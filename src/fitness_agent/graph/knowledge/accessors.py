"""Knowledge Accessors — domain-scoped wrappers around KnowledgeBase.

Each accessor class exposes only the KB query methods that the corresponding
agent is authorised to use (as defined in graph/registry.py).

Classes
-------
PlannerKnowledge:  Authorised KB access for the planner agent
                   (rules, anatomy, exercises).
CookingKnowledge:  Authorised KB access for the cooking agent
                   (recipes, nutrition, nutrition_principles).
GYMKnowledge:      Authorised KB access for the gym agent
                   (exercises, warmup_templates, injury_profiles).
"""

from __future__ import annotations

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Exercise,
    ExperienceLevel,
    GoalType,
    InjuryProfile,
    RecipeTemplate,
    WarmupTemplate,
)

# ---------------------------------------------------------------------------
# PlannerKnowledge
# ---------------------------------------------------------------------------


class PlannerKnowledge:
    """Planner agent's authorised view of the KB: rules, anatomy, exercises.

    Wraps the three KB methods needed to build the LLM prompt for the
    weekly training plan.
    """

    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    def get_split_templates(self, goal: GoalType, level: ExperienceLevel) -> str:
        """Return formatted training rules (split templates + volume constraints).

        Used in the LLM prompt to guide exercise selection and day structure.
        """
        return self._kb.format_rules_for_prompt(goal, level)

    def get_anatomy_targets(self, level: ExperienceLevel) -> str:
        """Return formatted anatomy reference table for the given experience level.

        Includes muscle groups, recovery time, movement patterns, and weekly
        set ranges — used in the LLM prompt for muscle balance guidance.
        """
        return self._kb.format_anatomy_for_prompt(level)

    def get_volume_targets_dict(self, level: ExperienceLevel) -> dict[str, tuple[int, int]]:
        """Return ``{muscle_id: (min_sets, max_sets)}`` for volume validation.

        Used by the ``volume_checker`` tool (not directly in the LLM prompt).
        """
        return self._kb.get_volume_targets(level)

    def get_macro_standards(
        self,
        dietary_restrictions: list[str],
        goal: GoalType | None = None,
    ) -> str:
        """Return formatted nutrition principles for the LLM prompt.

        Covers meal timing, training vs. rest day carb adjustments,
        dietary substitutions, and supplement recommendations.
        """
        return self._kb.format_nutrition_principles_for_prompt(dietary_restrictions, goal)

    def get_injury_guidance(self, injuries: list[ContraindicationTag]) -> str:
        """Return formatted injury modification guidance for the LLM prompt."""
        return self._kb.format_injury_guidance_for_prompt(injuries)

    def get_warmup_templates_text(self) -> str:
        """Return formatted warmup/cooldown template reference for the LLM prompt."""
        return self._kb.format_warmup_templates_for_prompt()


# ---------------------------------------------------------------------------
# CookingKnowledge
# ---------------------------------------------------------------------------


class CookingKnowledge:
    """Cooking agent's authorised view of the KB: recipes, nutrition, nutrition_principles."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    def get_recipes(self, dietary_restrictions: list[str]) -> list[RecipeTemplate]:
        """Return recipe templates compatible with the user's dietary restrictions."""
        return self._kb.get_compatible_recipes(dietary_restrictions)

    def get_banned_food_ids(self, dietary_restrictions: list[str]) -> set[str]:
        """Return the set of food IDs banned by the given dietary restrictions."""
        return self._kb.get_banned_food_ids(dietary_restrictions)

    def get_ingredient_macros(self, food_id: str) -> dict[str, float]:
        """Return per-100g macro data for a food item.

        Returns an empty dict if the food_id is not in the KB.
        """
        food = self._kb.get_food_by_id(food_id)
        if food is None:
            return {}
        return {
            "calories": food.calories,
            "protein_g": food.protein_g,
            "carbs_g": food.carbs_g,
            "fat_g": food.fat_g,
            "serving_size_g": food.serving_size_g,
        }

    def get_nutrition_principles(
        self,
        dietary_restrictions: list[str],
        goal: GoalType | None = None,
    ) -> str:
        """Return formatted nutrition execution guidelines for the LLM prompt."""
        return self._kb.format_nutrition_principles_for_prompt(dietary_restrictions, goal)

    def get_foods_compact(self) -> str:
        """Return the compact food database table for the LLM prompt."""
        return self._kb.format_foods_compact_for_prompt()

    def get_all_food_ids(self) -> set[str]:
        """Return the set of all valid food IDs (for validation)."""
        return self._kb.all_food_ids

    def get_recipes_formatted(self, recipes: list[RecipeTemplate] | None = None) -> str:
        """Return formatted recipe reference block for the LLM prompt."""
        return self._kb.format_recipes_for_prompt(recipes)


# ---------------------------------------------------------------------------
# GYMKnowledge
# ---------------------------------------------------------------------------


class GYMKnowledge:
    """GYM agent's authorised view of the KB: exercises, warmup_templates, injury_profiles."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    def get_exercise_by_id(self, exercise_id: str) -> Exercise | None:
        """Look up a single exercise by its ID."""
        return self._kb.get_exercise_by_id(exercise_id)

    def get_warmup_template(self, movement_patterns: list[str]) -> WarmupTemplate | None:
        """Return the best-matching warmup template for the given movement patterns."""
        return self._kb.get_warmup_template(movement_patterns)

    def get_injury_profile(self, tag: ContraindicationTag) -> InjuryProfile | None:
        """Return the InjuryProfile for a given contraindication tag, or None."""
        return self._kb.get_injury_profile(tag)

    def get_all_exercise_ids(self) -> list[str]:
        """Return all valid exercise IDs (for validation error messages)."""
        return sorted(ex.id for ex in self._kb.exercises)
