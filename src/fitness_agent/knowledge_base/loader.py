"""Knowledge base loader: reads JSON data files and provides query methods."""
import json
from pathlib import Path
from functools import cached_property

from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    Exercise,
    ExperienceLevel,
    FoodItem,
    GoalType,
    MuscleGroup,
    MovementPattern,
    TrainingRule,
)
from fitness_agent.utils.config import DATA_DIR
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

# Default paths
_KB_DIR = DATA_DIR / "raw"
EXERCISES_PATH = _KB_DIR / "exercises.json"
NUTRITION_PATH = _KB_DIR / "nutrition.json"
RULES_PATH = _KB_DIR / "rules.json"


class KnowledgeBase:
    """
    Loads and indexes the fitness knowledge base from JSON files.

    This is the deterministic layer: filtering, constraint checking, and
    calculation happen here — not inside the LLM.
    """

    def __init__(
        self,
        exercises_path: Path = EXERCISES_PATH,
        nutrition_path: Path = NUTRITION_PATH,
        rules_path: Path = RULES_PATH,
    ) -> None:
        self._exercises_path = exercises_path
        self._nutrition_path = nutrition_path
        self._rules_path = rules_path

    # ------------------------------------------------------------------
    # Raw data (loaded lazily and cached)
    # ------------------------------------------------------------------

    @cached_property
    def exercises(self) -> list[Exercise]:
        return self._load_list(self._exercises_path, Exercise)

    @cached_property
    def foods(self) -> list[FoodItem]:
        return self._load_list(self._nutrition_path, FoodItem)

    @cached_property
    def rules(self) -> list[TrainingRule]:
        return self._load_list(self._rules_path, TrainingRule)

    # ------------------------------------------------------------------
    # Exercise queries
    # ------------------------------------------------------------------

    def get_safe_exercises(
        self,
        contraindications: list[ContraindicationTag],
        available_equipment: list[Equipment],
    ) -> list[Exercise]:
        """
        Return exercises that are safe and feasible for a given user.

        Safety rule: exclude exercises whose contraindications overlap
        with the user's injuries.
        Feasibility rule: at least one of the exercise's equipment options
        must be available to the user.
        """
        user_contra_set = set(contraindications)
        equipment_set = set(available_equipment)

        return [
            ex for ex in self.exercises
            if not set(ex.contraindications) & user_contra_set
            and set(ex.equipment) & equipment_set
        ]

    def filter_exercises(
        self,
        exercises: list[Exercise],
        *,
        muscle_groups: list[MuscleGroup] | None = None,
        movement_patterns: list[MovementPattern] | None = None,
        difficulty: list[str] | None = None,
        equipment: list[Equipment] | None = None,
    ) -> list[Exercise]:
        """Further filter an exercise list by optional criteria."""
        result = exercises

        if muscle_groups:
            muscle_set = set(muscle_groups)
            result = [
                ex for ex in result
                if set(ex.primary_muscles) & muscle_set
                or set(ex.secondary_muscles) & muscle_set
            ]

        if movement_patterns:
            pattern_set = set(movement_patterns)
            result = [ex for ex in result if ex.movement_pattern in pattern_set]

        if difficulty:
            diff_set = set(difficulty)
            result = [ex for ex in result if ex.difficulty in diff_set]

        if equipment:
            eq_set = set(equipment)
            result = [ex for ex in result if set(ex.equipment) & eq_set]

        return result

    def get_exercise_by_id(self, exercise_id: str) -> Exercise | None:
        for ex in self.exercises:
            if ex.id == exercise_id:
                return ex
        return None

    # ------------------------------------------------------------------
    # Nutrition queries
    # ------------------------------------------------------------------

    def get_food_by_name(self, name: str) -> FoodItem | None:
        """Case-insensitive lookup by English or Chinese name."""
        name_lower = name.lower()
        for food in self.foods:
            if food.name.lower() == name_lower or food.name_zh == name:
                return food
        return None

    def search_foods(self, query: str) -> list[FoodItem]:
        """Simple substring search across both name fields."""
        q = query.lower()
        return [
            f for f in self.foods
            if q in f.name.lower() or q in f.name_zh.lower()
        ]

    # ------------------------------------------------------------------
    # Rules queries
    # ------------------------------------------------------------------

    def get_rules_for_context(
        self,
        goal: GoalType,
        level: ExperienceLevel,
    ) -> list[TrainingRule]:
        """Return all rules that apply to the given goal and experience level."""
        return [
            rule for rule in self.rules
            if (not rule.applies_to_goals or goal in rule.applies_to_goals)
            and (not rule.applies_to_levels or level in rule.applies_to_levels)
        ]

    def get_constraint_rules(
        self,
        goal: GoalType,
        level: ExperienceLevel,
    ) -> list[TrainingRule]:
        """Return only hard-constraint rules (rule_type == constraint)."""
        from fitness_agent.knowledge_base.models import RuleType
        return [
            r for r in self.get_rules_for_context(goal, level)
            if r.rule_type == RuleType.constraint
        ]

    def format_rules_for_prompt(
        self,
        goal: GoalType,
        level: ExperienceLevel,
    ) -> str:
        """
        Return a formatted string of applicable rules for LLM prompt injection.
        """
        rules = self.get_rules_for_context(goal, level)
        if not rules:
            return "（无特定规则约束）"

        lines = []
        for rule in rules:
            tag = "[硬约束]" if rule.rule_type.value == "constraint" else "[建议]"
            lines.append(f"- {tag} {rule.description}")
            if rule.parameters:
                param_str = ", ".join(f"{k}={v}" for k, v in rule.parameters.items())
                lines.append(f"  参数: {param_str}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        return {
            "exercises": len(self.exercises),
            "foods": len(self.foods),
            "rules": len(self.rules),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_list(self, path: Path, model_cls: type) -> list:
        if not path.exists():
            logger.warning(f"KB data file not found: {path}. Returning empty list.")
            return []

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        items = []
        for entry in raw:
            try:
                items.append(model_cls.model_validate(entry))
            except Exception as e:
                logger.warning(f"Skipping invalid entry in {path.name}: {e}")

        logger.info(f"Loaded {len(items)} items from {path.name}")
        return items
