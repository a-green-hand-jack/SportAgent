"""cook_node — LangGraph node for weekly cooking plan generation.

Orchestrates:
  KB recipe filtering → incremental day-by-day LLM generation
  → deterministic post-processing (scaling, protein boost, macro overwrite)
  → shopping list aggregation → write cooking_plan to state.
"""

from __future__ import annotations

import json

from fitness_agent.cooking.models import (
    DayMealPlan,
    WeeklyCookingPlan,
)
from fitness_agent.cooking.prompt import COOKING_SYSTEM, build_cooking_user_message
from fitness_agent.graph.knowledge.accessors import CookingKnowledge
from fitness_agent.graph.state import FitnessAgentState
from fitness_agent.graph.tools.cooking_tools import (
    CALORIE_TOLERANCE_PCT,
    MAX_UNKNOWN_FOOD_IDS_PER_BATCH,
    _compute_day_calorie_target,
    _overwrite_macros_deterministic,
    deterministic_scaler,
    grocery_gen,
)
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import Message, build_client
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 1

_WEEK_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def cook_node(state: FitnessAgentState) -> dict:
    """Generate a 7-day cooking plan and write it to the graph state.

    Reads
    -----
    state["user_profile"]  : dict
    state["weekly_plan"]   : dict (from plan_node)
    state["provider"]      : str
    state["model"]         : str

    Writes
    ------
    {"cooking_plan": dict, "errors": list[str]}
    """
    profile = UserProfile.model_validate(state["user_profile"])
    weekly_plan_raw = state.get("weekly_plan")
    if weekly_plan_raw is None:
        return {"errors": ["cook_node: weekly_plan is required but not present in state."]}

    weekly_plan = WeeklyPlan.model_validate(weekly_plan_raw)
    client = build_client(provider=state["provider"], model=state["model"])
    kb = KnowledgeBase()
    knowledge = CookingKnowledge(kb)

    if profile.daily_calorie_target is None:
        return {"errors": ["cook_node: Profile must be enriched (daily_calorie_target missing)."]}

    base_calorie_target = profile.daily_calorie_target

    # --- Tool: recipe filtering ---
    compatible_recipes = knowledge.get_recipes(profile.dietary_restrictions)
    banned_food_ids = knowledge.get_banned_food_ids(profile.dietary_restrictions)
    logger.info(
        f"cook_node: {len(compatible_recipes)} compatible recipes "
        f"(restrictions: {profile.dietary_restrictions})"
    )

    # --- Incremental day-by-day generation ---
    logger.info(f"cook_node: generating 7 days incrementally (provider: {client.provider})")
    all_days: list[DayMealPlan] = []

    for day_label in _WEEK_LABELS:
        already_json: str | None = None
        if all_days:
            already_json = json.dumps(
                [d.model_dump() for d in all_days],
                ensure_ascii=False,
                indent=2,
            )
        day = _generate_day(
            client,
            kb,
            profile,
            weekly_plan,
            compatible_recipes,
            day_label=day_label,
            already_generated_json=already_json,
            banned_food_ids=banned_food_ids,
        )
        all_days.append(day)

    # --- Assemble plan ---
    plan = WeeklyCookingPlan(
        user_name=profile.name,
        daily_plans=all_days,
        meal_prep_suggestions=[],
        shopping_list=[],
        cooking_tips_zh="",
    )

    # --- Tool: deterministic_scaler (full post-processing pipeline) ---
    deterministic_scaler(plan.daily_plans, base_calorie_target, profile, kb)

    # --- Compute calorie deviation percentages ---
    for day in plan.daily_plans:
        target = _compute_day_calorie_target(base_calorie_target, day.is_training_day)
        actual = day.day_total_macros.calories
        day.calorie_deviation_pct = (
            round((actual - target) / target * 100, 1) if target > 0 else 0.0
        )

    # --- Tool: grocery_gen ---
    plan.shopping_list = grocery_gen(plan.daily_plans, kb)

    # --- Final validation warnings ---
    all_warnings = _collect_validation_warnings(plan, base_calorie_target, kb, profile)
    if all_warnings:
        plan.cooking_tips_zh = (
            (plan.cooking_tips_zh + "\n\n" if plan.cooking_tips_zh else "")
            + "（以下为系统自动检测的改进建议）\n\n"
            + "\n\n".join(all_warnings)
        )

    logger.info(f"cook_node: {plan.summary()}")
    return {
        "cooking_plan": plan.model_dump(),
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Single-day generation helper
# ---------------------------------------------------------------------------


def _generate_day(
    client: object,
    kb: KnowledgeBase,
    profile: UserProfile,
    weekly_plan: WeeklyPlan,
    compatible_recipes: list,
    day_label: str,
    already_generated_json: str | None,
    banned_food_ids: set[str],
) -> DayMealPlan:
    """Call the LLM to generate a single day's meal plan with retry logic."""
    from fitness_agent.utils.llm_client import BaseLLMClient

    assert isinstance(client, BaseLLMClient)

    user_message = build_cooking_user_message(
        profile,
        weekly_plan,
        kb,
        compatible_recipes,
        day_label=day_label,
        already_generated_json=already_generated_json,
    )

    messages: list[Message] = [Message(role="user", content=user_message)]
    result: DayMealPlan | None = None

    for attempt in range(MAX_RETRIES + 1):
        logger.info(
            f"cook_node: calling {client.provider}/{client.model} "  # type: ignore[attr-defined]
            f"for day {day_label} (attempt {attempt + 1}/{MAX_RETRIES + 1})…"
        )
        response = client.chat(  # type: ignore[attr-defined]
            messages=messages,
            system=COOKING_SYSTEM,
            max_tokens=4096,
            temperature=0.7,
        )
        logger.info(
            f"cook_node: LLM responded {response.total_tokens} tokens "
            f"(in={response.input_tokens}, out={response.output_tokens})"
        )

        result = _parse_day_response(response.content, day_label)

        # Deterministic macro overwrite immediately after parsing
        _overwrite_macros_deterministic([result], kb)

        # Validate food IDs and dietary compliance
        food_id_warnings = _validate_food_ids([result], kb)
        dietary_warnings = _validate_dietary_compliance([result], banned_food_ids)

        needs_retry = (
            bool(dietary_warnings) or len(food_id_warnings) > MAX_UNKNOWN_FOOD_IDS_PER_BATCH
        )

        if not needs_retry:
            if food_id_warnings:
                logger.warning(
                    f"cook_node: day {day_label}: {len(food_id_warnings)} unknown food_id(s) "
                    f"(within tolerance of {MAX_UNKNOWN_FOOD_IDS_PER_BATCH})"
                )
            logger.info(f"cook_node: day {day_label}: validation passed.")
            break

        logger.info(
            f"cook_node: day {day_label}: {len(dietary_warnings)} dietary + "
            f"{len(food_id_warnings)} food_id warning(s) (attempt {attempt + 1})."
        )

        if attempt < MAX_RETRIES:
            messages.append(Message(role="assistant", content=response.content))
            correction_parts: list[str] = []
            if dietary_warnings:
                correction_parts.append(_build_dietary_correction_message(dietary_warnings))
            if len(food_id_warnings) > MAX_UNKNOWN_FOOD_IDS_PER_BATCH:
                correction_parts.append(
                    _build_food_id_correction_message(food_id_warnings, sorted(kb.all_food_ids))
                )
            messages.append(Message(role="user", content="\n\n".join(correction_parts)))

    assert result is not None
    return result


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_day_response(raw: str, expected_day_label: str) -> DayMealPlan:
    """Parse a single DayMealPlan from the LLM's raw text response."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"cook_node: LLM day response is not valid JSON: {exc}\n\n"
            f"Raw response:\n{raw[:500]}"
        ) from exc

    if isinstance(data, dict) and "daily_plans" in data:
        plans = data["daily_plans"]
        if plans:
            data = plans[0]
        else:
            raise RuntimeError(
                f"cook_node: LLM returned empty daily_plans for {expected_day_label}"
            )
    elif isinstance(data, list):
        if data:
            data = data[0]
        else:
            raise RuntimeError(f"cook_node: LLM returned empty list for {expected_day_label}")

    try:
        return DayMealPlan.model_validate(data)
    except Exception as exc:
        raise RuntimeError(
            f"cook_node: could not parse DayMealPlan for {expected_day_label}: {exc}\n\n"
            f"Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        ) from exc


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_food_ids(days: list[DayMealPlan], kb: KnowledgeBase) -> list[str]:
    """Check all ingredient food_ids against the KB."""
    valid_ids = kb.all_food_ids
    warnings: list[str] = []
    for day in days:
        for recipe in day.meals:
            for ing in recipe.ingredients:
                if ing.food_id not in valid_ids:
                    warnings.append(
                        f"- {day.day_label}/{recipe.name_zh}：food_id '{ing.food_id}'"
                        f"（{ing.food_name_zh}）不在食材数据库中"
                    )
    return warnings


def _validate_dietary_compliance(days: list[DayMealPlan], banned_food_ids: set[str]) -> list[str]:
    """Scan ingredient food_ids against the banned set."""
    if not banned_food_ids:
        return []
    warnings: list[str] = []
    for day in days:
        for recipe in day.meals:
            for ing in recipe.ingredients:
                if ing.food_id in banned_food_ids:
                    warnings.append(
                        f"- {day.day_label}/{recipe.name_zh}：食材 '{ing.food_id}'"
                        f"（{ing.food_name_zh}）违反饮食限制"
                    )
    return warnings


def _validate_calorie_compliance(days: list[DayMealPlan], base_calorie_target: float) -> list[str]:
    """Check each day's total calories against the day-specific target."""
    warnings: list[str] = []
    for day in days:
        target = _compute_day_calorie_target(base_calorie_target, day.is_training_day)
        actual = day.day_total_macros.calories
        if target <= 0:
            continue
        deviation = (actual - target) / target * 100
        if abs(deviation) > CALORIE_TOLERANCE_PCT:
            day_type = "训练日" if day.is_training_day else "休息日"
            warnings.append(
                f"- {day.day_label}（{day_type}）：{actual:.0f} kcal，"
                f"目标 {target:.0f} kcal，偏差 {deviation:+.1f}%"
            )
    return warnings


def _collect_validation_warnings(
    plan: WeeklyCookingPlan,
    base_calorie_target: float,
    kb: KnowledgeBase,
    profile: UserProfile,
) -> list[str]:
    """Run all post-generation validation checks and return formatted warning sections."""
    protein_target = profile.daily_protein_target_g or 0.0
    calorie_warnings = _validate_calorie_compliance(plan.daily_plans, base_calorie_target)

    protein_warnings = []
    if protein_target > 0:
        min_protein = protein_target * 90.0 / 100
        for day in plan.daily_plans:
            actual = day.day_total_macros.protein_g
            if actual < min_protein:
                pct = actual / protein_target * 100
                protein_warnings.append(
                    f"- {day.day_label}：蛋白质 {actual:.0f}g，"
                    f"目标 {protein_target:.0f}g 的 {pct:.0f}%（最低要求 90%）"
                )

    parts: list[str] = []
    if calorie_warnings:
        parts.append("📊 **热量偏差提醒**\n" + "\n".join(calorie_warnings))
    if protein_warnings:
        parts.append("🥩 **蛋白质不足提醒**\n" + "\n".join(protein_warnings))
    return parts


# ---------------------------------------------------------------------------
# Correction message builders
# ---------------------------------------------------------------------------


def _build_dietary_correction_message(dietary_warnings: list[str]) -> str:
    """Build a correction message for dietary violations."""
    return (
        "烹饪计划存在饮食限制违规，请调整：\n\n"
        "【饮食限制违规】\n" + "\n".join(dietary_warnings) + "\n\n"
        "调整要求：\n"
        "- 不要改变天数和整体餐食结构\n"
        "- 将禁用食材替换为同类别的合规食材\n"
        "- 保持每餐的营养比例和总热量基本不变\n"
        "- 返回完整修正后的 JSON（格式与之前相同，不要有任何额外文字）"
    )


def _build_food_id_correction_message(
    food_id_warnings: list[str],
    valid_food_ids: list[str],
) -> str:
    """Build a correction message for unknown food IDs."""
    valid_ids_text = ", ".join(sorted(valid_food_ids))
    return (
        "烹饪计划中以下食材的 food_id 不在数据库中，请替换：\n\n"
        "【无效食材 ID】\n" + "\n".join(food_id_warnings) + "\n\n"
        f"【有效 food_id 列表】\n{valid_ids_text}\n\n"
        "调整要求：\n"
        "- 将无效 food_id 替换为列表中语义最接近的有效 food_id\n"
        "- 保持 food_name_zh 与新 food_id 一致\n"
        "- 返回完整修正后的 JSON"
    )
