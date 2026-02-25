"""
CookingAgent — orchestrates the cooking plan generation pipeline:

  1. Filter compatible recipe pool from KB (dietary restrictions)
  2. Build structured LLM prompt (user context + recipes + food DB)
  3. Call LLM and parse the JSON response into a WeeklyCookingPlan
  4. Validate daily calorie compliance (training-day vs rest-day targets)
  5. Cross-validate recipe macros deterministically (ingredients × nutrition.json)
  6. Retry with correction message if validation fails
  7. Aggregate shopping list deterministically (post-processing)

The agent is deliberately stateless — each call is a fresh generation.
"""
from __future__ import annotations

import json

from fitness_agent.cooking.models import (
    DayMealPlan,
    MacroBreakdown,
    MealPrepSuggestion,
    Recipe,
    RecipeIngredient,
    ShoppingItem,
    WeeklyCookingPlan,
)
from fitness_agent.cooking.prompt import COOKING_SYSTEM, build_cooking_user_message
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import BaseLLMClient, Message
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)


class CookingAgent:
    """
    AI cooking planner that combines deterministic KB logic with LLM creativity.

    Parameters
    ----------
    client:
        Any ``BaseLLMClient`` instance.
    kb:
        Knowledge base providing foods, recipes, and nutrition principles.
    max_retries:
        Maximum number of additional LLM calls after the first attempt when
        calorie validation fails.  Total calls = max_retries + 1.
    calorie_tolerance_pct:
        Allowed deviation (%) between actual and target daily calories.
    """

    def __init__(
        self,
        client: BaseLLMClient,
        kb: KnowledgeBase,
        max_retries: int = 1,
        calorie_tolerance_pct: float = 10.0,
    ) -> None:
        self.client = client
        self.kb = kb
        self.max_retries = max_retries
        self.calorie_tolerance_pct = calorie_tolerance_pct

    # Training-day / rest-day calorie multipliers
    TRAINING_DAY_MULTIPLIER = 1.07   # +7%
    REST_DAY_MULTIPLIER = 0.96       # -4%

    # Deterministic scaling constants
    MAX_SCALE_FACTOR = 2.0           # Max ingredient scaling (prevent huge portions)
    MIN_SCALE_FACTOR = 0.5           # Min ingredient scaling (prevent tiny portions)

    # Protein compliance constants
    PROTEIN_COMPLIANCE_PCT = 90.0    # Min protein % of target (per day)
    PROTEIN_RICH_THRESHOLD = 15.0    # g/100g — foods above this are "protein-rich"
    POST_WORKOUT_MIN_PROTEIN_G = 20.0  # Min protein for post_workout meals

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # Week days used for batching
    _WEEK_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def generate_cooking_plan(
        self,
        weekly_plan: WeeklyPlan,
        profile: UserProfile,
    ) -> WeeklyCookingPlan:
        """
        Generate a 7-day cooking plan for the given training plan + profile.

        The plan is built via two LLM calls (days 1-4 then days 5-7) so that
        the response fits within providers that cap output tokens at 8192
        (e.g. DeepSeek).  Results are merged into a single WeeklyCookingPlan.

        The profile **must** be fully enriched (daily_calorie_target set).

        Raises
        ------
        ValueError
            If the profile is missing computed nutrition fields.
        RuntimeError
            If the LLM returns a response that cannot be parsed.
        """
        if profile.daily_calorie_target is None:
            raise ValueError(
                "Profile must be enriched before cooking plan generation. "
                "Call enrich_profile(profile) first."
            )

        base_calorie_target = profile.daily_calorie_target

        # --- Step 1: filter compatible recipes ---
        compatible_recipes = self.kb.get_compatible_recipes(
            profile.dietary_restrictions
        )
        logger.info(
            f"Recipe pool: {len(compatible_recipes)} compatible recipes "
            f"(restrictions: {profile.dietary_restrictions})"
        )

        # --- Step 1b: compute banned food IDs for dietary enforcement ---
        banned_food_ids = self.kb.get_banned_food_ids(
            profile.dietary_restrictions
        )
        if banned_food_ids:
            logger.info(
                f"Dietary enforcement: {len(banned_food_ids)} banned food IDs "
                f"for restrictions {profile.dietary_restrictions}"
            )

        # --- Step 2: generate in two batches (days 1-4, days 5-7) ---
        batch_a = self._WEEK_LABELS[:4]  # 周一~周四
        batch_b = self._WEEK_LABELS[4:]  # 周五~周日

        days_a = self._generate_batch(
            profile, weekly_plan, compatible_recipes, batch_a,
            banned_food_ids=banned_food_ids,
        )
        days_b = self._generate_batch(
            profile, weekly_plan, compatible_recipes, batch_b,
            banned_food_ids=banned_food_ids,
        )

        all_days = days_a + days_b

        # --- Step 3: assemble a combined WeeklyCookingPlan ---
        plan = WeeklyCookingPlan(
            user_name=profile.name,
            daily_plans=all_days,
            meal_prep_suggestions=[],
            shopping_list=[],
            cooking_tips_zh="",
        )

        # --- Step 4: deterministic macro overwrite on merged plan ---
        self._overwrite_macros_deterministic(plan.daily_plans)

        # --- Step 5: protein boost (before calorie scaling!) ---
        protein_target = profile.daily_protein_target_g or 0.0
        if protein_target > 0:
            min_protein = protein_target * self.PROTEIN_COMPLIANCE_PCT / 100
            for day in plan.daily_plans:
                if day.day_total_macros.protein_g < min_protein:
                    self._boost_protein_for_day(day, protein_target)

        # --- Step 6: deterministic calorie scaling ---
        for day in plan.daily_plans:
            day_target = self._compute_day_calorie_target(
                base_calorie_target, day.is_training_day
            )
            self._scale_day_to_calorie_target(day, day_target)

        # --- Step 7: final deterministic overwrite (ensure consistency) ---
        self._overwrite_macros_deterministic(plan.daily_plans)

        # --- Step 8: final validation (warnings only, no more correction) ---
        calorie_warnings = self._validate_calorie_compliance(
            plan.daily_plans, base_calorie_target
        )
        protein_warnings = self._validate_protein_compliance(
            plan.daily_plans, protein_target
        )
        post_workout_warnings = self._validate_post_workout_protein(
            plan.daily_plans
        )
        diversity_warnings = self._validate_diversity(plan.daily_plans)

        # Append remaining warnings to cooking_tips_zh
        all_remaining = (
            calorie_warnings + protein_warnings
            + post_workout_warnings + diversity_warnings
        )
        if all_remaining:
            parts = []
            if calorie_warnings:
                parts.append(
                    "📊 **热量偏差提醒**\n"
                    + "\n".join(calorie_warnings)
                    + "\n建议调整对应天数的食材份量。"
                )
            if protein_warnings:
                parts.append(
                    "🥩 **蛋白质不足提醒**\n"
                    + "\n".join(protein_warnings)
                )
            if post_workout_warnings:
                parts.append(
                    "💪 **训练后餐蛋白质不足**\n"
                    + "\n".join(post_workout_warnings)
                )
            if diversity_warnings:
                parts.append(
                    "🔄 **多样性提醒**\n"
                    + "\n".join(diversity_warnings)
                )
            warning_text = "（以下为系统自动检测的改进建议）\n\n" + "\n\n".join(parts)
            plan.cooking_tips_zh = (
                (plan.cooking_tips_zh + "\n\n" + warning_text)
                if plan.cooking_tips_zh
                else warning_text
            )

        # Compute calorie deviation percentages for each day
        for day in plan.daily_plans:
            target = self._compute_day_calorie_target(
                base_calorie_target, day.is_training_day
            )
            actual = day.day_total_macros.calories
            day.calorie_deviation_pct = round(
                (actual - target) / target * 100, 1
            ) if target > 0 else 0.0

        # Deterministic shopping list aggregation
        plan.shopping_list = self._aggregate_shopping_list(plan)

        logger.info(f"Cooking plan generated: {plan.summary()}")
        return plan

    # ------------------------------------------------------------------
    # Batch generation helper
    # ------------------------------------------------------------------

    def _generate_batch(
        self,
        profile: UserProfile,
        weekly_plan: WeeklyPlan,
        compatible_recipes: list,  # list[RecipeTemplate]
        days_subset: list[str],
        banned_food_ids: set[str] | None = None,
    ) -> list:  # list[DayMealPlan]
        """Run the LLM generate→validate→retry loop for a subset of days.

        Pipeline per attempt:
        1. Call LLM and parse response.
        2. Overwrite all macro values deterministically from KB.
        3. Validate dietary compliance (banned food_ids).
        4. If dietary violations exist and retries remain, send correction and loop.

        **Calorie / protein corrections are NOT retried here** — they are handled
        deterministically in ``generate_cooking_plan()`` via ingredient scaling.

        Returns the list of ``DayMealPlan`` objects for the requested days.
        """
        user_message = build_cooking_user_message(
            profile, weekly_plan, self.kb, compatible_recipes,
            days_subset=days_subset,
        )
        logger.debug(
            f"Batch {days_subset}: prompt ~{len(user_message)} chars"
        )

        banned = banned_food_ids or set()
        messages: list[Message] = [Message(role="user", content=user_message)]
        batch_days: list = []
        dietary_warnings: list[str] = []

        for attempt in range(self.max_retries + 1):
            logger.info(
                f"Calling {self.client.provider}/{self.client.model} "
                f"for days {days_subset} "
                f"(attempt {attempt + 1}/{self.max_retries + 1})…"
            )
            response = self.client.chat(
                messages=messages,
                system=COOKING_SYSTEM,
                max_tokens=8192,
                temperature=0.7,
            )
            logger.info(
                f"LLM responded: {response.total_tokens} tokens "
                f"(in={response.input_tokens}, out={response.output_tokens})"
            )

            # Step 1: Parse
            partial = self._parse_batch_response(response.content, profile)
            batch_days = partial

            # Step 2: Deterministic macro overwrite (replaces LLM self-reported values)
            self._overwrite_macros_deterministic(batch_days)

            # Step 3: Validate dietary compliance (only retry trigger)
            dietary_warnings = self._validate_dietary_compliance(batch_days, banned)

            if not dietary_warnings:
                logger.info(f"Batch {days_subset}: dietary validation passed.")
                break

            logger.info(
                f"Batch {days_subset}: {len(dietary_warnings)} dietary warning(s) "
                f"(attempt {attempt + 1}/{self.max_retries + 1})."
            )

            if attempt < self.max_retries:
                messages.append(Message(role="assistant", content=response.content))
                correction = self._build_dietary_correction_message(
                    dietary_warnings
                )
                messages.append(Message(role="user", content=correction))

        return batch_days

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _overwrite_macros_deterministic(self, days: list[DayMealPlan]) -> None:
        """Replace all LLM-reported macro values with KB-computed deterministic values.

        For each recipe in each day:
        1. Compute per_serving_macros from ingredient food_ids × amounts.
        2. Overwrite the recipe's per_serving_macros.
        3. Recompute and overwrite day_total_macros as the sum of all meals.

        Unknown food_ids contribute 0 to the totals (logged as warnings).
        """
        for day in days:
            day_cal = 0.0
            day_pro = 0.0
            day_carb = 0.0
            day_fat = 0.0

            for recipe in day.meals:
                ing_pairs = [
                    (ing.food_id, ing.amount_g) for ing in recipe.ingredients
                ]
                computed = self.kb.compute_ingredients_macros(ing_pairs)

                recipe.per_serving_macros = MacroBreakdown(
                    calories=computed["calories"],
                    protein_g=computed["protein_g"],
                    carbs_g=computed["carbs_g"],
                    fat_g=computed["fat_g"],
                )

                day_cal += computed["calories"]
                day_pro += computed["protein_g"]
                day_carb += computed["carbs_g"]
                day_fat += computed["fat_g"]

            day.day_total_macros = MacroBreakdown(
                calories=round(day_cal, 1),
                protein_g=round(day_pro, 1),
                carbs_g=round(day_carb, 1),
                fat_g=round(day_fat, 1),
            )

    def _validate_dietary_compliance(
        self, days: list[DayMealPlan], banned_food_ids: set[str]
    ) -> list[str]:
        """Scan all ingredient food_ids against the banned set.

        Returns a list of warning strings for each violation found.
        """
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

    def _validate_diversity(self, days: list[DayMealPlan]) -> list[str]:
        """Check recipe diversity across days (warning only, no retry).

        Checks:
        1. recipe_id repetition > 50% of total meals → warning
        2. protein source variety < 3 unique protein food_ids → warning
        """
        warnings: list[str] = []

        # Check recipe repetition
        all_recipe_ids: list[str] = []
        for day in days:
            for recipe in day.meals:
                all_recipe_ids.append(recipe.recipe_id)

        if all_recipe_ids:
            from collections import Counter
            counts = Counter(all_recipe_ids)
            most_common_count = counts.most_common(1)[0][1]
            total = len(all_recipe_ids)
            if most_common_count > total * 0.5:
                top_id = counts.most_common(1)[0][0]
                warnings.append(
                    f"食谱多样性不足：'{top_id}' 出现 {most_common_count}/{total} 次"
                )

        # Check protein source variety
        protein_categories = {"meat", "poultry", "seafood", "egg_dairy", "legume"}
        protein_food_ids: set[str] = set()
        for day in days:
            for recipe in day.meals:
                for ing in recipe.ingredients:
                    food = self.kb.get_food_by_id(ing.food_id)
                    if food and food.category.value in protein_categories:
                        protein_food_ids.add(ing.food_id)

        if len(protein_food_ids) < 3 and len(days) >= 3:
            warnings.append(
                f"蛋白质来源不足：仅 {len(protein_food_ids)} 种"
                f"（建议至少 3 种不同蛋白质食材）"
            )

        return warnings

    # ------------------------------------------------------------------
    # Deterministic calorie scaling & protein boost (V3)
    # ------------------------------------------------------------------

    def _scale_day_to_calorie_target(
        self,
        day: DayMealPlan,
        target_cal: float,
        tolerance_pct: float | None = None,
    ) -> None:
        """Deterministically scale all ingredient amounts so daily calories hit the target.

        Uniform scaling preserves the LLM-chosen ingredient ratios.
        The scale factor is clamped to [MIN_SCALE_FACTOR, MAX_SCALE_FACTOR]
        to prevent unreasonable portions.  After scaling, macros are recomputed
        via ``_overwrite_macros_deterministic``.
        """
        actual_cal = day.day_total_macros.calories
        if actual_cal <= 0 or target_cal <= 0:
            return  # nothing to scale

        tol = tolerance_pct if tolerance_pct is not None else self.calorie_tolerance_pct
        deviation_pct = abs(actual_cal - target_cal) / target_cal * 100
        if deviation_pct <= tol:
            return  # already within tolerance

        raw_factor = target_cal / actual_cal
        factor = max(self.MIN_SCALE_FACTOR, min(self.MAX_SCALE_FACTOR, raw_factor))

        for recipe in day.meals:
            for ing in recipe.ingredients:
                ing.amount_g = round(ing.amount_g * factor, 1)

        # Recompute all macros from scaled ingredient amounts
        self._overwrite_macros_deterministic([day])

    def _validate_protein_compliance(
        self,
        days: list[DayMealPlan],
        daily_protein_target: float,
    ) -> list[str]:
        """Check that each day's protein >= PROTEIN_COMPLIANCE_PCT % of target.

        Returns a list of warning strings for non-compliant days.
        """
        if daily_protein_target <= 0:
            return []

        min_protein = daily_protein_target * self.PROTEIN_COMPLIANCE_PCT / 100
        warnings: list[str] = []
        for day in days:
            actual = day.day_total_macros.protein_g
            if actual < min_protein:
                pct = actual / daily_protein_target * 100
                warnings.append(
                    f"- {day.day_label}：蛋白质 {actual:.0f}g，"
                    f"目标 {daily_protein_target:.0f}g 的 {pct:.0f}%"
                    f"（最低要求 {self.PROTEIN_COMPLIANCE_PCT:.0f}%）"
                )
        return warnings

    def _boost_protein_for_day(
        self, day: DayMealPlan, target_protein: float
    ) -> None:
        """Increase protein-rich ingredient amounts to close the protein gap.

        Only scales ingredients whose food has protein_g/100g >= PROTEIN_RICH_THRESHOLD.
        The extra grams are distributed proportionally to each high-protein
        ingredient's current protein contribution.  After boosting, macros are
        recomputed via ``_overwrite_macros_deterministic``.
        """
        actual_protein = day.day_total_macros.protein_g
        if actual_protein >= target_protein:
            return  # already sufficient

        gap = target_protein - actual_protein

        # Collect high-protein ingredients and their current protein contributions
        protein_sources: list[tuple[RecipeIngredient, float]] = []
        for recipe in day.meals:
            for ing in recipe.ingredients:
                food = self.kb.get_food_by_id(ing.food_id)
                if food is None:
                    continue
                protein_per_100g = food.protein_g / food.serving_size_g * 100
                if protein_per_100g >= self.PROTEIN_RICH_THRESHOLD:
                    current_protein = food.protein_g / food.serving_size_g * ing.amount_g
                    protein_sources.append((ing, current_protein))

        if not protein_sources:
            logger.warning(
                f"{day.day_label}: no protein-rich ingredients found, "
                f"cannot boost protein (gap={gap:.1f}g)"
            )
            return

        total_existing_protein = sum(p for _, p in protein_sources)
        if total_existing_protein <= 0:
            return

        # Distribute gap proportionally
        for ing, contribution in protein_sources:
            food = self.kb.get_food_by_id(ing.food_id)
            if food is None:
                continue
            share = contribution / total_existing_protein
            extra_protein_needed = gap * share
            protein_per_g = food.protein_g / food.serving_size_g
            if protein_per_g > 0:
                extra_amount_g = extra_protein_needed / protein_per_g
                ing.amount_g = round(ing.amount_g + extra_amount_g, 1)

        # Recompute all macros
        self._overwrite_macros_deterministic([day])

    def _validate_post_workout_protein(
        self, days: list[DayMealPlan]
    ) -> list[str]:
        """Check that post_workout meals have >= POST_WORKOUT_MIN_PROTEIN_G protein.

        Returns a list of warning strings for non-compliant post-workout meals.
        """
        warnings: list[str] = []
        for day in days:
            for recipe in day.meals:
                if recipe.meal_type != "post_workout":
                    continue
                protein = recipe.per_serving_macros.protein_g
                if protein < self.POST_WORKOUT_MIN_PROTEIN_G:
                    warnings.append(
                        f"- {day.day_label}/{recipe.name_zh}：训练后餐蛋白质"
                        f" {protein:.0f}g < {self.POST_WORKOUT_MIN_PROTEIN_G:.0f}g"
                    )
        return warnings

    def _compute_day_calorie_target(
        self, base_target: float, is_training_day: bool
    ) -> float:
        """Compute day-specific calorie target based on training status."""
        if is_training_day:
            return base_target * self.TRAINING_DAY_MULTIPLIER
        return base_target * self.REST_DAY_MULTIPLIER

    def _validate_calorie_compliance(
        self, days: list[DayMealPlan], base_calorie_target: float
    ) -> list[str]:
        """Check each day's total calories against the day-specific target."""
        warnings: list[str] = []
        for day in days:
            target = self._compute_day_calorie_target(
                base_calorie_target, day.is_training_day
            )
            actual = day.day_total_macros.calories
            if target <= 0:
                continue
            deviation = (actual - target) / target * 100
            if abs(deviation) > self.calorie_tolerance_pct:
                day_type = "训练日" if day.is_training_day else "休息日"
                warnings.append(
                    f"- {day.day_label}（{day_type}）：{actual:.0f} kcal，"
                    f"目标 {target:.0f} kcal，偏差 {deviation:+.1f}%"
                )
        return warnings

    def _cross_validate_macros(self, days: list[DayMealPlan]) -> list[str]:
        """Cross-validate recipe macros using nutrition.json data.

        Recomputes calories from ingredient food_ids × amounts and compares
        against the LLM's self-reported per_serving_macros.calories.
        Only flags recipes with > 20% discrepancy.
        """
        warnings: list[str] = []
        tolerance_pct = 20.0

        for day in days:
            for recipe in day.meals:
                computed_cal = 0.0
                has_known_food = False
                for ing in recipe.ingredients:
                    food = self.kb.get_food_by_id(ing.food_id)
                    if food is None:
                        continue
                    has_known_food = True
                    scale = ing.amount_g / food.serving_size_g
                    computed_cal += food.calories * scale

                if not has_known_food:
                    continue  # skip if no ingredients found in KB

                reported_cal = recipe.per_serving_macros.calories
                if reported_cal <= 0:
                    continue

                discrepancy = abs(computed_cal - reported_cal) / reported_cal * 100
                if discrepancy > tolerance_pct:
                    warnings.append(
                        f"- {recipe.name_zh}（{day.day_label}）：标注 {reported_cal:.0f} kcal，"
                        f"实际计算 {computed_cal:.0f} kcal（差异 {discrepancy:.0f}%）"
                    )
        return warnings

    @staticmethod
    def _build_dietary_correction_message(
        dietary_warnings: list[str],
    ) -> str:
        """Build a follow-up user message for dietary violations only."""
        warning_text = "\n".join(dietary_warnings)
        return (
            f"烹饪计划存在饮食限制违规，请调整：\n\n"
            f"【饮食限制违规】\n{warning_text}\n\n"
            "调整要求：\n"
            "- 不要改变天数和整体餐食结构\n"
            "- 将禁用食材替换为同类别的合规食材\n"
            "- 保持每餐的营养比例和总热量基本不变\n"
            "- 返回完整修正后的 JSON（格式与之前相同，不要有任何额外文字）"
        )

    @staticmethod
    def _build_correction_message(
        calorie_warnings: list[str],
        dietary_warnings: list[str],
    ) -> str:
        """Build a follow-up user message asking the LLM to fix issues.

        .. deprecated:: V3
            Use ``_build_dietary_correction_message`` instead.
            Kept for backward compatibility.
        """
        parts = []
        if dietary_warnings:
            parts.append(
                "【饮食限制违规】\n" + "\n".join(dietary_warnings)
                + "\n请将上述禁用食材替换为符合饮食限制的替代品。"
            )
        if calorie_warnings:
            parts.append("【每日热量偏差超限】\n" + "\n".join(calorie_warnings))
        joined = "\n\n".join(parts)
        return (
            f"烹饪计划存在以下问题，请调整：\n\n{joined}\n\n"
            "调整要求：\n"
            "- 不要改变天数和整体餐食结构\n"
            "- 饮食违规：将禁用食材替换为同类别的合规食材\n"
            "- 热量偏高：减少碳水或脂肪较高的食材用量，或替换为低热量食材\n"
            "- 热量偏低：增加食材份量或添加一份加餐\n"
            "- 返回完整修正后的 JSON（格式与之前相同，不要有任何额外文字）"
        )

    # ------------------------------------------------------------------
    # Post-processing: deterministic shopping list
    # ------------------------------------------------------------------

    def _aggregate_shopping_list(
        self, plan: WeeklyCookingPlan
    ) -> list[ShoppingItem]:
        """Aggregate all ingredients across 7 days into a deduplicated shopping list."""
        totals: dict[str, float] = {}
        names: dict[str, str] = {}

        for day in plan.daily_plans:
            for recipe in day.meals:
                for ing in recipe.ingredients:
                    fid = ing.food_id
                    totals[fid] = totals.get(fid, 0.0) + ing.amount_g
                    if fid not in names:
                        names[fid] = ing.food_name_zh

        items: list[ShoppingItem] = []
        for fid, total_g in sorted(totals.items()):
            food = self.kb.get_food_by_id(fid)
            category = food.category.value if food else "other"
            name_zh = names.get(fid, fid)
            items.append(
                ShoppingItem(
                    food_id=fid,
                    food_name_zh=name_zh,
                    total_amount_g=round(total_g, 1),
                    category=category,
                )
            )
        return items

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw: str, profile: UserProfile) -> WeeklyCookingPlan:
        """Strip markdown fences and parse the LLM output into a WeeklyCookingPlan."""
        text = raw.strip()

        # Strip ```json ... ``` or ``` ... ``` fences
        if text.startswith("```"):
            lines = text.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[1:end])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"LLM response is not valid JSON: {exc}\n\nRaw response:\n{raw[:500]}"
            ) from exc

        # Fill in user_name if not present
        data.setdefault("user_name", profile.name)

        # Ensure shopping_list is empty (will be computed deterministically)
        data["shopping_list"] = []

        try:
            return WeeklyCookingPlan.model_validate(data)
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse LLM output into WeeklyCookingPlan: {exc}\n\n"
                f"Data keys: {list(data.keys())}"
            ) from exc

    @staticmethod
    def _parse_batch_response(raw: str, profile: UserProfile) -> list:
        """Parse a batch LLM response that contains only a ``daily_plans`` array.

        The LLM is asked to return a JSON object with a ``daily_plans`` key
        (same schema as the full plan, but only covering the requested subset of
        days).  Returns a plain list of ``DayMealPlan`` objects.
        """
        text = raw.strip()

        # Strip ```json ... ``` / ``` fences
        if text.startswith("```"):
            lines = text.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[1:end])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"LLM batch response is not valid JSON: {exc}\n\n"
                f"Raw response:\n{raw[:500]}"
            ) from exc

        # Support both {"daily_plans": [...]} and a bare [...] array
        if isinstance(data, list):
            days_raw = data
        else:
            days_raw = data.get("daily_plans", [])

        try:
            return [DayMealPlan.model_validate(d) for d in days_raw]
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse batch DayMealPlan list: {exc}\n\n"
                f"First item keys: {list(days_raw[0].keys()) if days_raw else '(empty)'}"
            ) from exc
