"""Tests for KnowledgeBase loader and all query methods."""
import json
import pytest
from pathlib import Path

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    ExperienceLevel,
    GoalType,
    MovementPattern,
    MuscleGroup,
    RuleType,
)

TEST_DATA = Path(__file__).parent.parent / "data"


@pytest.fixture
def kb() -> KnowledgeBase:
    """KnowledgeBase backed by the small fixture data files in tests/data/."""
    return KnowledgeBase(
        exercises_path=TEST_DATA / "exercises.json",
        nutrition_path=TEST_DATA / "nutrition.json",
        rules_path=TEST_DATA / "rules.json",
    )


@pytest.fixture
def empty_kb(tmp_path: Path) -> KnowledgeBase:
    """KnowledgeBase pointing at non-existent files — should return empty lists."""
    return KnowledgeBase(
        exercises_path=tmp_path / "no_exercises.json",
        nutrition_path=tmp_path / "no_nutrition.json",
        rules_path=tmp_path / "no_rules.json",
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestLoading:
    def test_loads_exercises(self, kb: KnowledgeBase) -> None:
        assert len(kb.exercises) == 7

    def test_loads_foods(self, kb: KnowledgeBase) -> None:
        assert len(kb.foods) == 5

    def test_loads_rules(self, kb: KnowledgeBase) -> None:
        assert len(kb.rules) == 7

    def test_stats(self, kb: KnowledgeBase) -> None:
        stats = kb.stats()
        assert stats == {"exercises": 7, "foods": 5, "rules": 7}

    def test_missing_files_return_empty(self, empty_kb: KnowledgeBase) -> None:
        assert empty_kb.exercises == []
        assert empty_kb.foods == []
        assert empty_kb.rules == []

    def test_skips_invalid_entries(self, tmp_path: Path) -> None:
        """Malformed entries are skipped; valid ones are loaded."""
        data = [
            {
                "id": "valid_exercise",
                "name": "Valid",
                "name_zh": "有效",
                "category": "strength",
                "equipment": ["bodyweight"],
                "primary_muscles": ["chest"],
                "difficulty": "beginner",
                "movement_pattern": "push",
            },
            {"id": "bad_entry", "name": "Missing required fields"},
        ]
        path = tmp_path / "exercises.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        kb = KnowledgeBase(exercises_path=path, nutrition_path=tmp_path / "x.json",
                           rules_path=tmp_path / "y.json")
        assert len(kb.exercises) == 1
        assert kb.exercises[0].id == "valid_exercise"


# ---------------------------------------------------------------------------
# Exercise queries
# ---------------------------------------------------------------------------

class TestExerciseQueries:
    def test_get_safe_exercises_excludes_contraindicated(
        self, kb: KnowledgeBase
    ) -> None:
        # User has knee injury — barbell_squat and running must be excluded
        safe = kb.get_safe_exercises(
            contraindications=[ContraindicationTag.knee_injury],
            available_equipment=[Equipment.barbell, Equipment.bodyweight,
                                 Equipment.pull_up_bar, Equipment.dumbbell,
                                 Equipment.bench, Equipment.cable_machine],
        )
        ids = [ex.id for ex in safe]
        assert "barbell_squat" not in ids
        assert "running" not in ids
        # push_up is safe for knee injury
        assert "push_up" in ids

    def test_get_safe_exercises_requires_equipment(
        self, kb: KnowledgeBase
    ) -> None:
        # User only has bodyweight — barbell exercises must be excluded
        safe = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=[Equipment.bodyweight],
        )
        ids = [ex.id for ex in safe]
        assert "barbell_squat" not in ids
        assert "deadlift" not in ids
        assert "push_up" in ids
        assert "running" in ids

    def test_get_safe_exercises_no_injuries_all_equipment(
        self, kb: KnowledgeBase
    ) -> None:
        all_equipment = list(Equipment)
        safe = kb.get_safe_exercises(contraindications=[], available_equipment=all_equipment)
        # All 7 exercises should be available
        assert len(safe) == 7

    def test_filter_by_muscle_group(self, kb: KnowledgeBase) -> None:
        chest_exercises = kb.filter_exercises(
            kb.exercises, muscle_groups=[MuscleGroup.chest]
        )
        ids = [ex.id for ex in chest_exercises]
        assert "push_up" in ids
        assert "dumbbell_bench_press" in ids
        # Deadlift targets hamstrings/glutes/lower_back, not chest
        assert "deadlift" not in ids

    def test_filter_by_movement_pattern(self, kb: KnowledgeBase) -> None:
        push_exercises = kb.filter_exercises(
            kb.exercises, movement_patterns=[MovementPattern.push]
        )
        ids = [ex.id for ex in push_exercises]
        assert "push_up" in ids
        assert "dumbbell_bench_press" in ids
        assert "pull_up" not in ids
        assert "deadlift" not in ids

    def test_filter_by_difficulty(self, kb: KnowledgeBase) -> None:
        beginner = kb.filter_exercises(kb.exercises, difficulty=["beginner"])
        assert all(ex.difficulty.value == "beginner" for ex in beginner)

    def test_filter_by_equipment(self, kb: KnowledgeBase) -> None:
        barbell_only = kb.filter_exercises(
            kb.exercises, equipment=[Equipment.barbell]
        )
        ids = [ex.id for ex in barbell_only]
        assert "barbell_squat" in ids
        assert "deadlift" in ids
        assert "push_up" not in ids

    def test_filter_combined(self, kb: KnowledgeBase) -> None:
        result = kb.filter_exercises(
            kb.exercises,
            muscle_groups=[MuscleGroup.chest],
            difficulty=["beginner"],
        )
        assert all(ex.difficulty.value == "beginner" for ex in result)
        assert all(
            MuscleGroup.chest in ex.primary_muscles
            or MuscleGroup.chest in ex.secondary_muscles
            for ex in result
        )

    def test_get_exercise_by_id_found(self, kb: KnowledgeBase) -> None:
        ex = kb.get_exercise_by_id("pull_up")
        assert ex is not None
        assert ex.name_zh == "引体向上"

    def test_get_exercise_by_id_not_found(self, kb: KnowledgeBase) -> None:
        assert kb.get_exercise_by_id("nonexistent") is None


# ---------------------------------------------------------------------------
# Nutrition queries
# ---------------------------------------------------------------------------

class TestNutritionQueries:
    def test_get_food_by_english_name(self, kb: KnowledgeBase) -> None:
        food = kb.get_food_by_name("Chicken Breast")
        assert food is not None
        assert food.id == "chicken_breast"

    def test_get_food_by_name_case_insensitive(self, kb: KnowledgeBase) -> None:
        food = kb.get_food_by_name("chicken breast")
        assert food is not None

    def test_get_food_by_chinese_name(self, kb: KnowledgeBase) -> None:
        food = kb.get_food_by_name("鸡蛋")
        assert food is not None
        assert food.id == "egg_whole"

    def test_get_food_not_found(self, kb: KnowledgeBase) -> None:
        assert kb.get_food_by_name("nonexistent food") is None

    def test_search_foods_substring(self, kb: KnowledgeBase) -> None:
        results = kb.search_foods("chicken")
        assert len(results) == 1
        assert results[0].id == "chicken_breast"

    def test_search_foods_chinese_substring(self, kb: KnowledgeBase) -> None:
        results = kb.search_foods("蛋白")
        assert any(f.id == "whey_protein" for f in results)

    def test_search_foods_no_match(self, kb: KnowledgeBase) -> None:
        assert kb.search_foods("zzz_no_match") == []


# ---------------------------------------------------------------------------
# Rules queries
# ---------------------------------------------------------------------------

class TestRulesQueries:
    def test_get_rules_for_fat_loss_beginner(self, kb: KnowledgeBase) -> None:
        rules = kb.get_rules_for_context(GoalType.fat_loss, ExperienceLevel.beginner)
        ids = [r.id for r in rules]
        # fat_loss-specific rule
        assert "rule_calorie_deficit" in ids
        # applies_to_goals=[] means all goals
        assert "rule_protein_intake" in ids
        assert "rule_sleep" in ids
        # beginner-specific
        assert "rule_beginner_volume" in ids
        assert "rule_beginner_no_1rm" in ids
        # muscle_gain rule should NOT appear
        assert "rule_calorie_surplus" not in ids
        # intermediate rule should NOT appear
        assert "rule_intermediate_volume" not in ids

    def test_get_rules_for_muscle_gain_intermediate(self, kb: KnowledgeBase) -> None:
        rules = kb.get_rules_for_context(GoalType.muscle_gain, ExperienceLevel.intermediate)
        ids = [r.id for r in rules]
        assert "rule_calorie_surplus" in ids
        assert "rule_intermediate_volume" in ids
        assert "rule_calorie_deficit" not in ids
        assert "rule_beginner_volume" not in ids

    def test_universal_rules_appear_for_all_contexts(self, kb: KnowledgeBase) -> None:
        for goal in GoalType:
            for level in ExperienceLevel:
                rules = kb.get_rules_for_context(goal, level)
                ids = [r.id for r in rules]
                assert "rule_protein_intake" in ids, f"Missing universal rule for {goal}/{level}"
                assert "rule_sleep" in ids

    def test_get_constraint_rules_only_constraints(self, kb: KnowledgeBase) -> None:
        constraints = kb.get_constraint_rules(GoalType.fat_loss, ExperienceLevel.beginner)
        assert all(r.rule_type == RuleType.constraint for r in constraints)
        ids = [r.id for r in constraints]
        # rule_sleep is a recommendation, must not appear
        assert "rule_sleep" not in ids

    def test_format_rules_for_prompt_contains_descriptions(
        self, kb: KnowledgeBase
    ) -> None:
        text = kb.format_rules_for_prompt(GoalType.fat_loss, ExperienceLevel.beginner)
        assert "热量缺口" in text
        assert "[硬约束]" in text
        assert "[建议]" in text

    def test_format_rules_for_prompt_empty_kb(self, empty_kb: KnowledgeBase) -> None:
        text = empty_kb.format_rules_for_prompt(GoalType.general_fitness, ExperienceLevel.beginner)
        assert text == "（无特定规则约束）"
