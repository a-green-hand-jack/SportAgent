"""Tests for cooking prompt builder."""
from __future__ import annotations

from pathlib import Path

import pytest

from fitness_agent.cooking.prompt import COOKING_SYSTEM, build_cooking_user_message
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.planner.models import DailyNutrition, ExerciseSet, TrainingDay, WeeklyPlan
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
        recipes_path=_DATA_DIR / "recipes.json",
    )


@pytest.fixture()
def profile() -> UserProfile:
    p = UserProfile(
        name="CookTest",
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
        dietary_restrictions=["vegetarian"],
    )
    return enrich_profile(p)


@pytest.fixture()
def weekly_plan(profile: UserProfile) -> WeeklyPlan:
    days = []
    for i in range(1, 4):
        days.append(
            TrainingDay(
                day_label=f"Day {i}",
                focus="Full body",
                exercises=[
                    ExerciseSet(
                        exercise_id="push_up",
                        exercise_name="Push Up",
                        exercise_name_zh="俯卧撑",
                        sets=3,
                        reps="10",
                        rest_seconds=60,
                    )
                ],
                estimated_duration_minutes=60,
                pre_workout_meal="燕麦+鸡蛋",
                post_workout_meal="鸡胸+米饭",
            )
        )
    return WeeklyPlan(
        user_name=profile.name,
        goal=profile.goal,
        experience_level=profile.experience_level.value,
        training_days=days,
        rest_days=["Day 4", "Day 5", "Day 6", "Day 7"],
        daily_nutrition=DailyNutrition(
            calorie_target=profile.daily_calorie_target or 2500,
            protein_g=profile.daily_protein_target_g or 150,
            carbs_g=250.0,
            fat_g=65.0,
            meal_suggestions=["早餐: 燕麦+鸡蛋", "午餐: 鸡胸肉+米饭"],
        ),
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    def test_system_prompt_non_empty(self) -> None:
        assert len(COOKING_SYSTEM) > 100

    def test_system_prompt_mentions_7_days(self) -> None:
        assert "7" in COOKING_SYSTEM

    def test_system_prompt_mentions_json(self) -> None:
        assert "JSON" in COOKING_SYSTEM

    def test_system_prompt_mentions_daily_plans(self) -> None:
        assert "daily_plans" in COOKING_SYSTEM


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------

class TestBuildCookingUserMessage:
    def test_includes_user_name(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        assert "CookTest" in msg

    def test_includes_dietary_restrictions(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        assert "vegetarian" in msg

    def test_includes_recipe_pool(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        # At least one compatible recipe name should appear
        assert any(
            r.name_zh in msg for r in compatible
        ), "No compatible recipe names found in prompt"

    def test_includes_training_schedule(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        assert "Day 1" in msg
        assert "训练日" in msg

    def test_includes_calorie_targets(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        cal = profile.daily_calorie_target or 2000
        # Calorie target or computed training/rest targets should appear
        assert str(int(cal)) in msg or "kcal" in msg

    def test_includes_food_database(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        # Food items from nutrition.json should appear
        assert "chicken_breast" in msg or "鸡胸肉" in msg

    def test_includes_meal_suggestions_reference(self, profile, weekly_plan, kb) -> None:
        compatible = kb.get_compatible_recipes(profile.dietary_restrictions)
        msg = build_cooking_user_message(profile, weekly_plan, kb, compatible)
        assert "PlanAgent" in msg
        assert "燕麦" in msg

    def test_no_restriction_uses_all_recipes(self, weekly_plan, kb) -> None:
        """Profile with no dietary restrictions → all recipes in pool."""
        p = UserProfile(
            name="NoRestriction",
            age=25,
            gender="male",
            height_cm=175,
            weight_kg=75,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            activity_level="sedentary",
        )
        p = enrich_profile(p)
        compatible = kb.get_compatible_recipes([])
        msg = build_cooking_user_message(p, weekly_plan, kb, compatible)
        # Should include recipes that are NOT vegetarian
        assert "鸡胸肉西兰花饭" in msg or "chicken_rice_broccoli" in msg
