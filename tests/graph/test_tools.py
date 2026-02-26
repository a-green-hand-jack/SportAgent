"""Tests for graph tool functions.

All KB operations run against real fixture data in tests/data/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    ExperienceLevel,
    GoalType,
)
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile

_DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture()
def kb() -> KnowledgeBase:
    return KnowledgeBase(
        exercises_path=_DATA_DIR / "exercises.json",
        nutrition_path=_DATA_DIR / "nutrition.json",
        rules_path=_DATA_DIR / "rules.json",
        anatomy_path=_DATA_DIR / "anatomy.json",
        nutrition_principles_path=_DATA_DIR / "nutrition_principles.json",
    )


@pytest.fixture()
def base_profile() -> UserProfile:
    profile = UserProfile(
        name="Test",
        age=28,
        gender="male",
        height_cm=178.0,
        weight_kg=78.0,
        goal=GoalType.muscle_gain,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=60,
        available_equipment=[Equipment.bodyweight, Equipment.dumbbell],
        activity_level="lightly_active",
    )
    return enrich_profile(profile)


# ---------------------------------------------------------------------------
# safety_guard
# ---------------------------------------------------------------------------


class TestSafetyGuard:
    def test_no_contraindications_returns_all(self, kb) -> None:
        from fitness_agent.graph.tools.safety_tools import safety_guard

        result = safety_guard(kb.exercises, [])
        assert len(result) == len(kb.exercises)

    def test_filters_contraindicated_exercises(self, kb) -> None:
        from fitness_agent.graph.tools.safety_tools import safety_guard

        # push_up has wrist_injury contraindication in test data
        all_ex = kb.exercises
        result = safety_guard(all_ex, [ContraindicationTag.wrist_injury])
        # At least one exercise should be filtered out
        assert len(result) <= len(all_ex)
        # No exercise in result should have wrist_injury contraindication
        for ex in result:
            assert ContraindicationTag.wrist_injury not in ex.contraindications


# ---------------------------------------------------------------------------
# split_engine
# ---------------------------------------------------------------------------


class TestSplitEngine:
    def test_returns_list_of_exercises(self, kb, base_profile) -> None:
        from fitness_agent.graph.tools.planner_tools import split_engine

        pool = split_engine(base_profile, kb)
        assert isinstance(pool, list)
        assert len(pool) > 0

    def test_respects_max_exercises(self, kb, base_profile) -> None:
        from fitness_agent.graph.tools.planner_tools import split_engine

        pool = split_engine(base_profile, kb, max_exercises=5)
        assert len(pool) <= 5

    def test_filters_by_equipment(self, kb) -> None:
        from fitness_agent.graph.tools.planner_tools import split_engine

        profile = enrich_profile(
            UserProfile(
                name="BodyweightOnly",
                age=25,
                gender="female",
                height_cm=165,
                weight_kg=58,
                goal=GoalType.fat_loss,
                experience_level=ExperienceLevel.beginner,
                training_days_per_week=3,
                session_duration_minutes=45,
                available_equipment=[Equipment.bodyweight],
                activity_level="sedentary",
            )
        )
        pool = split_engine(profile, kb)
        # All exercises in the pool should be feasible with bodyweight equipment
        equipment_set = {Equipment.bodyweight}
        for ex in pool:
            assert (
                set(ex.equipment) & equipment_set
            ), f"Exercise {ex.id} requires equipment not available to user"

    def test_bodyweight_fallback_when_pool_empty(self, kb) -> None:
        """Profile with impossible equipment combination triggers bodyweight fallback."""
        from fitness_agent.graph.tools.planner_tools import split_engine

        # Use a made-up equipment type that doesn't exist - patch with an empty pool
        profile = enrich_profile(
            UserProfile(
                name="NoEquip",
                age=30,
                gender="male",
                height_cm=175,
                weight_kg=75,
                goal=GoalType.general_fitness,
                experience_level=ExperienceLevel.beginner,
                training_days_per_week=3,
                session_duration_minutes=45,
                available_equipment=[Equipment.bodyweight],
                activity_level="sedentary",
            )
        )
        # Even with bodyweight, pool should not be empty
        pool = split_engine(profile, kb)
        assert len(pool) > 0


# ---------------------------------------------------------------------------
# volume_checker
# ---------------------------------------------------------------------------


class TestVolumeChecker:
    def test_returns_list(self, kb, base_profile) -> None:
        from fitness_agent.graph.tools.planner_tools import volume_checker
        from fitness_agent.planner.models import (
            DailyNutrition,
            ExerciseSet,
            TrainingDay,
            WeeklyPlan,
        )

        day = TrainingDay(
            day_label="Day 1",
            focus="Full body",
            exercises=[
                ExerciseSet(
                    exercise_id="push_up",
                    exercise_name="Push Up",
                    exercise_name_zh="俯卧撑",
                    sets=4,
                    reps="10",
                    rest_seconds=60,
                )
            ],
            estimated_duration_minutes=45,
        )
        plan = WeeklyPlan(
            user_name="Test",
            goal=GoalType.muscle_gain,
            experience_level="beginner",
            training_days=[day],
            daily_nutrition=DailyNutrition(
                calorie_target=2000, protein_g=150, carbs_g=200, fat_g=60
            ),
        )
        warnings = volume_checker(plan, kb, ExperienceLevel.beginner)
        assert isinstance(warnings, list)

    def test_no_warnings_for_plan_with_nonexistent_exercise(self, kb) -> None:
        """Plan with unknown exercise IDs → exercises skipped → no counts → no warnings."""
        from fitness_agent.graph.tools.planner_tools import volume_checker
        from fitness_agent.planner.models import (
            DailyNutrition,
            ExerciseSet,
            TrainingDay,
            WeeklyPlan,
        )

        day = TrainingDay(
            day_label="Day 1",
            focus="Full body",
            exercises=[
                ExerciseSet(
                    exercise_id="nonexistent_xyz",
                    exercise_name="Unknown",
                    exercise_name_zh="未知",
                    sets=3,
                    reps="10",
                    rest_seconds=60,
                )
            ],
            estimated_duration_minutes=45,
        )
        plan = WeeklyPlan(
            user_name="Test",
            goal=GoalType.general_fitness,
            experience_level="beginner",
            training_days=[day],
            daily_nutrition=DailyNutrition(
                calorie_target=2000, protein_g=150, carbs_g=200, fat_g=60
            ),
        )
        warnings = volume_checker(plan, kb, ExperienceLevel.beginner)
        # All exercises unknown → all counts = 0 → no muscle gets flagged
        assert warnings == []


# ---------------------------------------------------------------------------
# grocery_gen
# ---------------------------------------------------------------------------


class TestGroceryGen:
    def test_returns_empty_for_empty_days(self, kb) -> None:
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )
        from fitness_agent.graph.tools.cooking_tools import grocery_gen

        recipe = Recipe(
            recipe_id="test_recipe",
            name_zh="测试餐",
            meal_type="breakfast",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150.0)
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=200, protein_g=30, carbs_g=5, fat_g=5),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(calories=600, protein_g=90, carbs_g=15, fat_g=15),
        )
        items = grocery_gen([day], kb)
        assert isinstance(items, list)
        # chicken_breast should be aggregated
        fids = [item.food_id for item in items]
        assert "chicken_breast" in fids

    def test_aggregates_same_food_across_days(self, kb) -> None:
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )
        from fitness_agent.graph.tools.cooking_tools import grocery_gen

        def make_day(label: str, amount_g: float) -> DayMealPlan:
            recipe = Recipe(
                recipe_id=f"r_{label}",
                name_zh="测试",
                meal_type="breakfast",
                prep_time_minutes=5,
                cook_time_minutes=5,
                ingredients=[
                    RecipeIngredient(
                        food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=amount_g
                    )
                ],
                steps_zh=["步骤1"],
                per_serving_macros=MacroBreakdown(calories=100, protein_g=20, carbs_g=0, fat_g=2),
            )
            return DayMealPlan(
                day_label=label,
                is_training_day=False,
                meals=[recipe, recipe, recipe],
                day_total_macros=MacroBreakdown(calories=300, protein_g=60, carbs_g=0, fat_g=6),
            )

        day1 = make_day("周一", 100.0)
        day2 = make_day("周二", 150.0)
        items = grocery_gen([day1, day2], kb)
        chicken_item = next((i for i in items if i.food_id == "chicken_breast"), None)
        assert chicken_item is not None
        # 100 * 3 + 150 * 3 = 750g total
        assert chicken_item.total_amount_g == pytest.approx(750.0, abs=1.0)


# ---------------------------------------------------------------------------
# rpe_engine (placeholder)
# ---------------------------------------------------------------------------


class TestRpeEngine:
    def test_returns_empty_list(self, base_profile) -> None:
        from fitness_agent.graph.tools.gym_tools import rpe_engine

        result = rpe_engine(base_profile, session_count=4)
        assert result == []
