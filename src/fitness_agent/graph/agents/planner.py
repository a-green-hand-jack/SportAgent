"""plan_node — LangGraph node for weekly training plan generation.

Orchestrates:
  KB filtering (split_engine) → LLM generation → volume/duration/injury validation
  → retry loop → write weekly_plan to state.
"""

from __future__ import annotations

import json

from fitness_agent.graph.state import FitnessAgentState
from fitness_agent.graph.tools.planner_tools import (
    _parse_contraindications,
    split_engine,
    volume_checker,
)
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.planner.prompt import PLANNER_SYSTEM, build_user_message
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import Message, build_client
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 2


def plan_node(state: FitnessAgentState) -> dict:
    """Generate a personalised WeeklyPlan and write it to the graph state.

    Reads
    -----
    state["user_profile"]  : dict (UserProfile.model_dump())
    state["provider"]      : str
    state["model"]         : str

    Writes
    ------
    {"weekly_plan": dict, "errors": list[str]}
    """
    profile = UserProfile.model_validate(state["user_profile"])
    client = build_client(provider=state["provider"], model=state["model"])
    kb = KnowledgeBase()

    # --- Validate enrichment ---
    if profile.bmr is None or profile.daily_calorie_target is None:
        return {
            "errors": [
                "plan_node: Profile must be enriched before planning. "
                "Call enrich_profile(profile) first."
            ]
        }

    # --- Tool: split_engine — build safe exercise pool ---
    exercise_pool = split_engine(profile, kb)
    contraindications = _parse_contraindications(profile.injuries)

    # --- Build initial prompt ---
    user_message = build_user_message(profile, kb, exercise_pool)
    logger.debug(f"plan_node: prompt length ~{len(user_message)} chars")

    messages: list[Message] = [Message(role="user", content=user_message)]
    plan: WeeklyPlan | None = None
    volume_warnings: list[str] = []
    duration_warnings: list[str] = []
    injury_warnings: list[str] = []

    for attempt in range(MAX_RETRIES + 1):
        logger.info(
            f"plan_node: calling {client.provider}/{client.model} "
            f"(attempt {attempt + 1}/{MAX_RETRIES + 1})…"
        )
        response = client.chat(
            messages=messages,
            system=PLANNER_SYSTEM,
            max_tokens=8192,
            temperature=0.7,
        )
        logger.info(
            f"plan_node: LLM responded {response.total_tokens} tokens "
            f"(in={response.input_tokens}, out={response.output_tokens})"
        )

        plan = _parse_response(response.content, profile)

        # Validate training-day count (informational warning)
        expected = profile.training_days_per_week
        actual = len(plan.training_days)
        if actual != expected:
            logger.warning(
                f"plan_node: training days mismatch: requested {expected}, got {actual}."
            )

        # Tool: volume_checker
        volume_warnings = volume_checker(plan, kb, profile.experience_level)
        # Duration validation (keep inline — simple logic)
        duration_warnings = _validate_duration(plan, profile.session_duration_minutes)
        # Injury re-validation
        injury_warnings = _validate_injuries(plan, contraindications, kb)

        all_warnings = volume_warnings + duration_warnings + injury_warnings
        if not all_warnings:
            logger.info("plan_node: all validations passed.")
            break

        logger.info(
            f"plan_node: {len(volume_warnings)} volume, {len(duration_warnings)} duration, "
            f"{len(injury_warnings)} injury warning(s) (attempt {attempt + 1})."
        )

        if attempt < MAX_RETRIES:
            messages.append(Message(role="assistant", content=response.content))
            correction = _build_correction_message(
                volume_warnings, duration_warnings, injury_warnings
            )
            messages.append(Message(role="user", content=correction))

    assert plan is not None

    # Append remaining warnings to coach_notes
    all_remaining = volume_warnings + duration_warnings + injury_warnings
    if all_remaining:
        parts = []
        if volume_warnings:
            parts.append(
                "📊 **周训练量提醒**\n"
                + "\n".join(volume_warnings)
                + "\n建议在不足的肌群对应训练日中额外补充1-2组复合动作。"
            )
        if duration_warnings:
            parts.append(
                "⏱ **训练时长超限提醒**\n"
                + "\n".join(duration_warnings)
                + "\n建议减少孤立动作或适当缩减组数。"
            )
        if injury_warnings:
            parts.append(
                "⚠️ **伤病安全提醒**\n"
                + "\n".join(injury_warnings)
                + "\n请将上述动作替换为对应伤病安全的替代动作。"
            )
        warning_text = "（以下为系统自动检测的计划改进建议）\n\n" + "\n\n".join(parts)
        plan.coach_notes = (
            (plan.coach_notes + "\n\n" + warning_text) if plan.coach_notes else warning_text
        )

    logger.info(f"plan_node: {plan.summary()}")
    return {
        "weekly_plan": plan.model_dump(),
        "errors": all_remaining,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_response(raw: str, profile: UserProfile) -> WeeklyPlan:
    """Strip markdown fences and parse the LLM output into a WeeklyPlan."""

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"plan_node: LLM response is not valid JSON: {exc}\n\nRaw response:\n{raw[:500]}"
        ) from exc

    data.setdefault("user_name", profile.name)
    data.setdefault("goal", profile.goal.value)
    data.setdefault("experience_level", profile.experience_level.value)
    _patch_exercises(data)

    try:
        return WeeklyPlan.model_validate(data)
    except Exception as exc:
        raise RuntimeError(
            f"plan_node: could not parse WeeklyPlan: {exc}\n\n" f"Data keys: {list(data.keys())}"
        ) from exc


def _patch_exercises(data: dict) -> dict:
    """Best-effort fill of missing exercise_name / exercise_name_zh fields."""
    for day in data.get("training_days", []):
        for ex in day.get("exercises", []):
            eid = ex.get("exercise_id", "")
            if "exercise_name" not in ex or not ex["exercise_name"]:
                ex["exercise_name"] = eid.replace("_", " ").title()
            if "exercise_name_zh" not in ex or not ex["exercise_name_zh"]:
                ex["exercise_name_zh"] = ex.get("exercise_name", eid.replace("_", " ").title())
    return data


def _validate_duration(plan: WeeklyPlan, session_duration_minutes: int) -> list[str]:
    """Check each training day's estimated duration against the user's session target."""
    tolerance = 15
    limit = session_duration_minutes + tolerance
    warnings = []
    for day in plan.training_days:
        if day.estimated_duration_minutes > limit:
            warnings.append(
                f"- {day.day_label}：估计时长 {day.estimated_duration_minutes} 分钟，"
                f"超过目标 {session_duration_minutes} 分钟（允许误差 {tolerance} 分钟）"
            )
    return warnings


def _validate_injuries(
    plan: WeeklyPlan,
    contraindications: list,
    kb: KnowledgeBase,
) -> list[str]:
    """Re-validate that no exercise in the plan violates the user's contraindications."""
    if not contraindications:
        return []
    contra_set = set(contraindications)
    warnings = []
    for day in plan.training_days:
        for ex_set in day.exercises:
            exercise = kb.get_exercise_by_id(ex_set.exercise_id)
            if exercise is None:
                continue
            violations = contra_set & set(exercise.contraindications)
            if violations:
                warnings.append(
                    f"- {ex_set.exercise_name}（{ex_set.exercise_id}）"
                    f"对 {', '.join(v.value for v in violations)} 有禁忌，请替换为安全动作"
                )
    return warnings


def _build_correction_message(
    volume_warnings: list[str],
    duration_warnings: list[str],
    injury_warnings: list[str],
) -> str:
    """Build a follow-up user message asking the LLM to fix all identified issues."""
    parts = []
    if volume_warnings:
        parts.append("【周训练量不足】\n" + "\n".join(volume_warnings))
    if duration_warnings:
        parts.append("【训练时长超限】\n" + "\n".join(duration_warnings))
    if injury_warnings:
        parts.append("【伤病安全问题】\n" + "\n".join(injury_warnings))
    joined = "\n\n".join(parts)
    return (
        f"计划存在以下问题，请调整：\n\n{joined}\n\n"
        "调整要求：\n"
        "- 不要改变训练日数量或整体训练结构\n"
        "- 训练量不足：在对应训练日增加 1-2 组针对该肌群的复合动作\n"
        "- 时长超限：减少动作数量或组数，优先删除孤立动作\n"
        "- 伤病问题：将违禁动作替换为安全替代动作\n"
        "- 返回完整修正后的 JSON 计划（格式与之前相同，不要有任何额外文字）"
    )
