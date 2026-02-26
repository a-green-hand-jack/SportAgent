"""cooking_tools — deterministic tools for the CookingAgent node.

Tools
-----
deterministic_scaler:  Full post-processing pipeline (macro overwrite, protein boost,
                       calorie scaling, clamping, rounding).
grocery_gen:           Aggregate ingredients across 7 days into a shopping list.
"""

from __future__ import annotations

from fitness_agent.cooking.models import DayMealPlan, MacroBreakdown, ShoppingItem
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants (mirrors CookingAgent class-level constants)
# ---------------------------------------------------------------------------

TRAINING_DAY_MULTIPLIER: float = 1.07
REST_DAY_MULTIPLIER: float = 0.96
MAX_SCALE_FACTOR: float = 2.0
MIN_SCALE_FACTOR: float = 0.5
CALORIE_TOLERANCE_PCT: float = 10.0
PROTEIN_COMPLIANCE_PCT: float = 90.0
PROTEIN_RICH_THRESHOLD: float = 15.0  # g/100g
PROTEIN_BOOST_BUFFER_G: float = 5.0
MAX_UNKNOWN_FOOD_IDS_PER_BATCH: int = 0
MEAL_CALORIE_HARD_CAPS: dict[str, float] = {
    "snack": 400,
    "pre_workout": 400,
    "post_workout": 700,
}


# ---------------------------------------------------------------------------
# deterministic_scaler
# ---------------------------------------------------------------------------


def deterministic_scaler(
    daily_plans: list[DayMealPlan],
    base_calorie_target: float,
    profile: UserProfile,
    kb: KnowledgeBase,
) -> None:
    """Apply the full deterministic post-processing pipeline to a 7-day meal plan.

    Modifies ``daily_plans`` in-place.

    Pipeline
    --------
    1. Macro overwrite — replace LLM-reported values with KB-computed ones.
    2. Protein boost   — scale protein-rich ingredients to hit daily target.
    3. Calorie scaling — scale each day's ingredients to hit day-specific target.
    4. Meal clamping   — cap per-meal calories for small-meal types.
    5. Rounding        — round ingredient amounts to practical precision.
    6. Second-pass scaling — compensate for calorie loss from clamping + rounding.
    7. Final macro overwrite.
    """
    protein_target = profile.daily_protein_target_g or 0.0

    # Step 1: initial macro overwrite
    _overwrite_macros_deterministic(daily_plans, kb)

    # Step 2: protein boost (before calorie scaling)
    if protein_target > 0:
        boost_aim = protein_target + PROTEIN_BOOST_BUFFER_G
        for day in daily_plans:
            if day.day_total_macros.protein_g < protein_target:
                _boost_protein_for_day(day, boost_aim, kb)

    # Step 3: calorie scaling
    for day in daily_plans:
        day_target = _compute_day_calorie_target(base_calorie_target, day.is_training_day)
        _scale_day_to_calorie_target(day, day_target, kb)

    # Step 4: clamp per-meal calories
    _clamp_meal_calories(daily_plans, kb)

    # Step 5: round ingredient amounts
    _round_ingredient_amounts(daily_plans)

    # Step 6: second-pass scaling (compensate rounding/clamping losses)
    _overwrite_macros_deterministic(daily_plans, kb)
    for day in daily_plans:
        day_target = _compute_day_calorie_target(base_calorie_target, day.is_training_day)
        _scale_day_to_calorie_target(day, day_target, kb)

    # Step 7: final macro overwrite
    _overwrite_macros_deterministic(daily_plans, kb)


# ---------------------------------------------------------------------------
# grocery_gen
# ---------------------------------------------------------------------------


def grocery_gen(
    daily_plans: list[DayMealPlan],
    kb: KnowledgeBase,
) -> list[ShoppingItem]:
    """Aggregate all ingredients across all days into a deduplicated shopping list.

    Parameters
    ----------
    daily_plans:
        The 7-day meal plan (after scaling and finalisation).
    kb:
        Initialised knowledge base (for food category lookup).

    Returns
    -------
    list[ShoppingItem]
        Sorted by food_id, with total gram amounts summed across all days.
    """
    totals: dict[str, float] = {}
    names: dict[str, str] = {}

    for day in daily_plans:
        for recipe in day.meals:
            for ing in recipe.ingredients:
                fid = ing.food_id
                totals[fid] = totals.get(fid, 0.0) + ing.amount_g
                if fid not in names:
                    names[fid] = ing.food_name_zh

    items: list[ShoppingItem] = []
    for fid, total_g in sorted(totals.items()):
        food = kb.get_food_by_id(fid)
        category = food.category.value if food else "other"
        items.append(
            ShoppingItem(
                food_id=fid,
                food_name_zh=names.get(fid, fid),
                total_amount_g=round(total_g, 1),
                category=category,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Internal helpers (extracted from CookingAgent private methods)
# ---------------------------------------------------------------------------


def _overwrite_macros_deterministic(days: list[DayMealPlan], kb: KnowledgeBase) -> None:
    """Replace all LLM-reported macro values with KB-computed deterministic values."""
    for day in days:
        day_cal = 0.0
        day_pro = 0.0
        day_carb = 0.0
        day_fat = 0.0

        for recipe in day.meals:
            ing_pairs = [(ing.food_id, ing.amount_g) for ing in recipe.ingredients]
            computed = kb.compute_ingredients_macros(ing_pairs)

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


def _compute_day_calorie_target(base_target: float, is_training_day: bool) -> float:
    """Compute day-specific calorie target based on training status."""
    if is_training_day:
        return base_target * TRAINING_DAY_MULTIPLIER
    return base_target * REST_DAY_MULTIPLIER


def _scale_day_to_calorie_target(
    day: DayMealPlan,
    target_cal: float,
    kb: KnowledgeBase,
    tolerance_pct: float = CALORIE_TOLERANCE_PCT,
) -> None:
    """Scale all ingredient amounts so daily calories hit the target.

    Uniform scaling preserves the LLM-chosen ingredient ratios.
    The scale factor is clamped to [MIN_SCALE_FACTOR, MAX_SCALE_FACTOR].
    """
    actual_cal = day.day_total_macros.calories
    if actual_cal <= 0 or target_cal <= 0:
        return

    deviation_pct = abs(actual_cal - target_cal) / target_cal * 100
    if deviation_pct <= tolerance_pct:
        return

    raw_factor = target_cal / actual_cal
    factor = max(MIN_SCALE_FACTOR, min(MAX_SCALE_FACTOR, raw_factor))

    for recipe in day.meals:
        for ing in recipe.ingredients:
            ing.amount_g = round(ing.amount_g * factor, 1)

    _overwrite_macros_deterministic([day], kb)


def _clamp_meal_calories(days: list[DayMealPlan], kb: KnowledgeBase) -> None:
    """Scale down meals that exceed their type's hard calorie ceiling."""
    for day in days:
        for recipe in day.meals:
            cap = MEAL_CALORIE_HARD_CAPS.get(recipe.meal_type)
            if cap is None:
                continue
            ing_pairs = [(ing.food_id, ing.amount_g) for ing in recipe.ingredients]
            computed = kb.compute_ingredients_macros(ing_pairs)
            actual_cal = computed["calories"]
            if actual_cal <= cap:
                continue
            factor = cap / actual_cal
            logger.info(
                f"{day.day_label}/{recipe.name_zh} ({recipe.meal_type}): "
                f"{actual_cal:.0f} kcal > {cap:.0f} cap, scaling by {factor:.2f}"
            )
            for ing in recipe.ingredients:
                ing.amount_g = round(ing.amount_g * factor, 1)


def _boost_protein_for_day(
    day: DayMealPlan,
    target_protein: float,
    kb: KnowledgeBase,
) -> None:
    """Increase protein-rich ingredient amounts to close the protein gap."""
    from fitness_agent.cooking.models import RecipeIngredient

    actual_protein = day.day_total_macros.protein_g
    if actual_protein >= target_protein:
        return

    gap = target_protein - actual_protein

    protein_sources: list[tuple[RecipeIngredient, float]] = []
    for recipe in day.meals:
        for ing in recipe.ingredients:
            food = kb.get_food_by_id(ing.food_id)
            if food is None:
                continue
            protein_per_100g = food.protein_g / food.serving_size_g * 100
            if protein_per_100g >= PROTEIN_RICH_THRESHOLD:
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

    for ing, contribution in protein_sources:
        food = kb.get_food_by_id(ing.food_id)
        if food is None:
            continue
        share = contribution / total_existing_protein
        extra_protein_needed = gap * share
        protein_per_g = food.protein_g / food.serving_size_g
        if protein_per_g > 0:
            extra_amount_g = extra_protein_needed / protein_per_g
            ing.amount_g = round(ing.amount_g + extra_amount_g, 1)

    _overwrite_macros_deterministic([day], kb)


def _round_ingredient_amounts(days: list[DayMealPlan]) -> None:
    """Round all ingredient amounts to practical precision.

    >= 10g: round to nearest 10g
    < 10g:  round to nearest 5g (minimum 5g)
    """
    for day in days:
        for recipe in day.meals:
            for ing in recipe.ingredients:
                if ing.amount_g < 10:
                    ing.amount_g = max(5.0, round(ing.amount_g / 5) * 5)
                else:
                    ing.amount_g = round(ing.amount_g / 10) * 10
