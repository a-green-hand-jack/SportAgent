"""
Tests for CookingAgent.

Strategy: mock the LLM client so no real API calls are made.
All KB operations run against real fixture data in tests/data/.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fitness_agent.cooking.agent import CookingAgent
from fitness_agent.cooking.models import WeeklyCookingPlan
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.planner.models import DailyNutrition, ExerciseSet, TrainingDay, WeeklyPlan
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import LLMResponse


_DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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
        name="CookBob",
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
# Mock LLM helpers
# ---------------------------------------------------------------------------

def _make_llm_client(json_response: str) -> MagicMock:
    client = MagicMock()
    client.provider = "mock"
    client.model = "mock-model"
    client.chat.return_value = LLMResponse(
        content=json_response,
        provider="mock",
        model="mock-model",
        input_tokens=100,
        output_tokens=200,
    )
    return client


def _make_multi_response_client(responses: list[str]) -> MagicMock:
    client = MagicMock()
    client.provider = "mock"
    client.model = "mock-model"
    client.chat.side_effect = [
        LLMResponse(
            content=r,
            provider="mock",
            model="mock-model",
            input_tokens=100,
            output_tokens=200,
        )
        for r in responses
    ]
    return client


def _make_recipe_json(
    recipe_id: str = "test_recipe",
    meal_type: str = "lunch",
    calories: float = 800,
    protein: float = 50,
) -> dict:
    return {
        "recipe_id": recipe_id,
        "name_zh": f"测试{meal_type}",
        "meal_type": meal_type,
        "prep_time_minutes": 5,
        "cook_time_minutes": 10,
        "ingredients": [
            {
                "food_id": "chicken_breast",
                "food_name_zh": "鸡胸肉",
                "amount_g": 150,
            },
            {
                "food_id": "white_rice_cooked",
                "food_name_zh": "白米饭",
                "amount_g": 200,
            },
        ],
        "steps_zh": ["步骤1", "步骤2", "步骤3"],
        "per_serving_macros": {
            "calories": calories,
            "protein_g": protein,
            "carbs_g": 80,
            "fat_g": 15,
        },
    }


def _minimal_cooking_plan_json(
    profile: UserProfile,
    base_cal: float | None = None,
    training_days: int = 3,
) -> str:
    """Build a minimal valid cooking plan JSON that the mock LLM returns."""
    cal_target = base_cal or profile.daily_calorie_target or 2500
    training_cal = cal_target * 1.07
    rest_cal = cal_target * 0.96

    day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    days = []
    for i in range(7):
        is_training = i < training_days
        day_cal = training_cal if is_training else rest_cal
        # Split calories across 3 meals
        meal_cal = day_cal / 3

        meals = [
            _make_recipe_json(f"breakfast_{i}", "breakfast", meal_cal, 40),
            _make_recipe_json(f"lunch_{i}", "lunch", meal_cal, 50),
            _make_recipe_json(f"dinner_{i}", "dinner", meal_cal, 45),
        ]
        days.append({
            "day_label": day_labels[i],
            "is_training_day": is_training,
            "meals": meals,
            "day_total_macros": {
                "calories": day_cal,
                "protein_g": 135,
                "carbs_g": 240,
                "fat_g": 45,
            },
        })

    plan = {
        "daily_plans": days,
        "meal_prep_suggestions": [
            {
                "recipe_name_zh": "批量煮鸡胸",
                "prep_day": "周日",
                "covers_days": ["周一", "周二"],
                "storage_zh": "冷藏3天",
                "reheat_zh": "微波2分钟",
            }
        ],
        "cooking_tips_zh": "保持食材新鲜，注意蛋白摄入。",
    }
    return json.dumps(plan, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CookingAgent basic tests
# ---------------------------------------------------------------------------

class TestCookingAgent:
    def test_generate_returns_weekly_cooking_plan(
        self, kb, profile, weekly_plan
    ) -> None:
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert isinstance(plan, WeeklyCookingPlan)

    def test_plan_has_7_days(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert len(plan.daily_plans) == 7

    def test_plan_user_name_filled(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert plan.user_name == "CookBob"

    def test_unenriched_profile_raises(self, kb, weekly_plan) -> None:
        bare = UserProfile(
            name="Test",
            age=25,
            gender="male",
            height_cm=170,
            weight_kg=70,
            goal=GoalType.fat_loss,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            activity_level="sedentary",
        )
        client = _make_llm_client("{}")
        agent = CookingAgent(client=client, kb=kb)
        with pytest.raises(ValueError, match="enriched"):
            agent.generate_cooking_plan(weekly_plan, bare)

    def test_invalid_json_raises_runtime_error(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client("This is not JSON.")
        agent = CookingAgent(client=client, kb=kb)
        with pytest.raises(RuntimeError, match="not valid JSON"):
            agent.generate_cooking_plan(weekly_plan, profile)

    def test_strips_markdown_fences(self, kb, profile, weekly_plan) -> None:
        raw = "```json\n" + _minimal_cooking_plan_json(profile) + "\n```"
        client = _make_llm_client(raw)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert isinstance(plan, WeeklyCookingPlan)

    def test_llm_called_once_when_validation_passes(
        self, kb, profile, weekly_plan
    ) -> None:
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        # Stub validators to return no warnings
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._cross_validate_macros = lambda plan: []
        agent.generate_cooking_plan(weekly_plan, profile)
        client.chat.assert_called_once()


# ---------------------------------------------------------------------------
# Shopping list aggregation
# ---------------------------------------------------------------------------

class TestShoppingListAggregation:
    def test_shopping_list_populated(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert len(plan.shopping_list) > 0

    def test_shopping_list_deduplicates_food_ids(
        self, kb, profile, weekly_plan
    ) -> None:
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        food_ids = [item.food_id for item in plan.shopping_list]
        assert len(food_ids) == len(set(food_ids)), "Shopping list should have unique food_ids"

    def test_shopping_list_sums_amounts(self, kb, profile, weekly_plan) -> None:
        """chicken_breast appears in every meal (150g each × 3 meals × 7 days = 3150g)."""
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        chicken = next(
            (item for item in plan.shopping_list if item.food_id == "chicken_breast"),
            None,
        )
        assert chicken is not None
        # Each day has 3 meals, each with 150g chicken. 7 days.
        assert chicken.total_amount_g == 150 * 3 * 7


# ---------------------------------------------------------------------------
# Calorie validation
# ---------------------------------------------------------------------------

class TestCalorieValidation:
    def test_no_warning_when_within_tolerance(self, kb, profile, weekly_plan) -> None:
        """Plan with calories matching targets should have no calorie warnings."""
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # The minimal plan JSON is constructed to match targets
        base = profile.daily_calorie_target or 2500
        warnings = agent._validate_calorie_compliance(plan, base)
        assert warnings == []

    def test_calorie_deviation_computed(self, kb, profile, weekly_plan) -> None:
        """Each day should have calorie_deviation_pct computed."""
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        for day in plan.daily_plans:
            # Should be close to 0 for our well-constructed mock
            assert abs(day.calorie_deviation_pct) < 15.0


# ---------------------------------------------------------------------------
# Retry loop
# ---------------------------------------------------------------------------

class TestRetryLoop:
    def test_retries_on_calorie_violation(self, kb, profile, weekly_plan) -> None:
        """When calorie validation always fails, agent retries max_retries times."""
        max_retries = 1
        responses = [_minimal_cooking_plan_json(profile)] * (max_retries + 1)
        client = _make_multi_response_client(responses)
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        # Force calorie warnings every time
        agent._validate_calorie_compliance = lambda plan, target: [
            "- 周一（训练日）：3000 kcal，目标 2500 kcal，偏差 +20.0%"
        ]
        agent._cross_validate_macros = lambda plan: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == max_retries + 1

    def test_max_retries_respected(self, kb, profile, weekly_plan) -> None:
        """Agent never exceeds max_retries+1 LLM calls."""
        max_retries = 2
        total = max_retries + 1
        responses = [_minimal_cooking_plan_json(profile)] * total
        client = _make_multi_response_client(responses)
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        agent._validate_calorie_compliance = lambda plan, target: ["- 偏差过大"]
        agent._cross_validate_macros = lambda plan: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == total

    def test_no_retry_when_all_valid(self, kb, profile, weekly_plan) -> None:
        """No warnings → single LLM call."""
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb, max_retries=2)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._cross_validate_macros = lambda plan: []
        agent.generate_cooking_plan(weekly_plan, profile)
        client.chat.assert_called_once()

    def test_warnings_appended_to_tips(self, kb, profile, weekly_plan) -> None:
        """Unresolved warnings after retries are written into cooking_tips_zh."""
        max_retries = 1
        responses = [_minimal_cooking_plan_json(profile)] * (max_retries + 1)
        client = _make_multi_response_client(responses)
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        agent._validate_calorie_compliance = lambda plan, target: [
            "- 周一偏差 +20%"
        ]
        agent._cross_validate_macros = lambda plan: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert "热量偏差提醒" in plan.cooking_tips_zh

    def test_correction_message_appended(self, kb, profile, weekly_plan) -> None:
        """On retry, second LLM call has [user, assistant, user(correction)] messages."""
        responses = [_minimal_cooking_plan_json(profile)] * 2
        client = _make_multi_response_client(responses)
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_calorie_compliance = lambda plan, target: ["- 偏差"]
        agent._cross_validate_macros = lambda plan: []
        agent.generate_cooking_plan(weekly_plan, profile)
        second_kwargs = client.chat.call_args_list[1].kwargs
        msgs = second_kwargs["messages"]
        assert len(msgs) == 3
        assert msgs[1].role == "assistant"
        assert msgs[2].role == "user"
        assert "调整要求" in msgs[2].content


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------

class TestCrossValidation:
    def test_cross_validate_catches_large_discrepancy(
        self, kb, profile, weekly_plan
    ) -> None:
        """Manually craft plan where LLM claims 100 kcal but KB computes much more."""
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # Artificially set one recipe's reported macros to be very wrong
        plan.daily_plans[0].meals[0].per_serving_macros.calories = 50.0
        warnings = agent._cross_validate_macros(plan)
        # Should detect the discrepancy
        assert len(warnings) > 0

    def test_cross_validate_no_warning_for_unknown_foods(
        self, kb, profile, weekly_plan
    ) -> None:
        """Recipes with unknown food_ids are silently skipped."""
        client = _make_llm_client(_minimal_cooking_plan_json(profile))
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # Replace all food_ids with unknowns
        for day in plan.daily_plans:
            for meal in day.meals:
                for ing in meal.ingredients:
                    ing.food_id = "nonexistent_food_xyz"
        warnings = agent._cross_validate_macros(plan)
        assert warnings == []


# ---------------------------------------------------------------------------
# Training day calorie target computation
# ---------------------------------------------------------------------------

class TestCalorieTargetComputation:
    def test_training_day_higher(self) -> None:
        agent = CookingAgent.__new__(CookingAgent)
        target = agent._compute_day_calorie_target(2500, is_training_day=True)
        assert target == 2500 * 1.07

    def test_rest_day_lower(self) -> None:
        agent = CookingAgent.__new__(CookingAgent)
        target = agent._compute_day_calorie_target(2500, is_training_day=False)
        assert target == 2500 * 0.96
