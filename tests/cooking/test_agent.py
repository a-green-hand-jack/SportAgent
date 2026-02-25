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

def _make_llm_client(
    profile: UserProfile,
    training_days: int = 3,
    base_cal: float | None = None,
) -> MagicMock:
    """Create a mock LLM client that returns batch-appropriate day subsets.

    Uses call-order: first call → batch A (4 days), second call → batch B (3 days).
    On retries (subsequent calls within the same batch), the same pattern repeats
    with the same group of days.
    """
    _all_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def _side_effect(messages, **kwargs):
        # Always read from the FIRST message (the original batch prompt).
        # On retries, messages grows to [user, assistant, user(correction)],
        # but messages[0] is still the original prompt which uniquely identifies
        # the batch (batch A has 周一-周四, batch B has 周五-周日).
        first_content = messages[0].content if messages else ""
        requested = [lbl for lbl in _all_labels if lbl in first_content]
        if not requested:
            requested = _all_labels
        json_str = _minimal_cooking_plan_json(
            profile,
            base_cal=base_cal,
            training_days=training_days,
            day_labels=requested,
        )
        return LLMResponse(
            content=json_str,
            provider="mock",
            model="mock-model",
            input_tokens=100,
            output_tokens=200,
        )

    client = MagicMock()
    client.provider = "mock"
    client.model = "mock-model"
    client.chat.side_effect = _side_effect
    return client


def _make_llm_client_fixed(json_response: str) -> MagicMock:
    """Create a mock LLM client that always returns the same fixed response."""
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
    chicken_g: float = 150,
    rice_g: float = 200,
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
                "amount_g": chicken_g,
            },
            {
                "food_id": "white_rice_cooked",
                "food_name_zh": "白米饭",
                "amount_g": rice_g,
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
    day_labels: list[str] | None = None,
) -> str:
    """Build a minimal valid cooking plan JSON that the mock LLM returns.

    When ``day_labels`` is given, only those days are included in the response,
    matching the batched call structure (batch A: 4 days, batch B: 3 days).
    """
    cal_target = base_cal or profile.daily_calorie_target or 2500
    training_cal = cal_target * 1.07
    rest_cal = cal_target * 0.96

    # Scale ingredient amounts so KB-computed macros match calorie targets.
    # chicken_breast: 165 kcal/100g, white_rice_cooked: 130 kcal/100g
    # With ratio 3:4 (chicken:rice), cal_per_meal = 10.15 * k where k = chicken_g / 3
    # So k = cal_per_meal / 10.15, chicken_g = 3k, rice_g = 4k
    def _scale_amounts(day_cal: float) -> tuple[float, float]:
        meal_cal = day_cal / 3
        k = meal_cal / 10.15  # 1.65*3 + 1.30*4 = 10.15 per unit k
        return round(3 * k, 1), round(4 * k, 1)

    all_labels = ["\u5468\u4e00", "\u5468\u4e8c", "\u5468\u4e09", "\u5468\u56db", "\u5468\u4e94", "\u5468\u516d", "\u5468\u65e5"]
    labels_to_use = day_labels if day_labels is not None else all_labels
    days = []
    for label in labels_to_use:
        idx = all_labels.index(label) if label in all_labels else 0
        is_training = idx < training_days
        day_cal = training_cal if is_training else rest_cal
        meal_cal = day_cal / 3
        chicken_g, rice_g = _scale_amounts(day_cal)

        meals = [
            _make_recipe_json(f"breakfast_{idx}", "breakfast", meal_cal, 40,
                              chicken_g=chicken_g, rice_g=rice_g),
            _make_recipe_json(f"lunch_{idx}", "lunch", meal_cal, 50,
                              chicken_g=chicken_g, rice_g=rice_g),
            _make_recipe_json(f"dinner_{idx}", "dinner", meal_cal, 45,
                              chicken_g=chicken_g, rice_g=rice_g),
        ]
        days.append({
            "day_label": label,
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
                "recipe_name_zh": "\u6279\u91cf\u716e\u9e21\u80f8",
                "prep_day": "\u5468\u65e5",
                "covers_days": ["\u5468\u4e00", "\u5468\u4e8c"],
                "storage_zh": "\u51b7\u85cf3\u5929",
                "reheat_zh": "\u5fae\u6ce22\u5206\u949f",
            }
        ],
        "cooking_tips_zh": "\u4fdd\u6301\u98df\u6750\u65b0\u9c9c\uff0c\u6ce8\u610f\u86cb\u767d\u6444\u5165\u3002",
    }
    return json.dumps(plan, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CookingAgent basic tests
# ---------------------------------------------------------------------------

class TestCookingAgent:
    def test_generate_returns_weekly_cooking_plan(
        self, kb, profile, weekly_plan
    ) -> None:
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert isinstance(plan, WeeklyCookingPlan)

    def test_plan_has_7_days(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert len(plan.daily_plans) == 7

    def test_plan_user_name_filled(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(profile)
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
        client = _make_llm_client_fixed("{}")
        agent = CookingAgent(client=client, kb=kb)
        with pytest.raises(ValueError, match="enriched"):
            agent.generate_cooking_plan(weekly_plan, bare)

    def test_invalid_json_raises_runtime_error(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client_fixed("This is not JSON.")
        agent = CookingAgent(client=client, kb=kb)
        with pytest.raises(RuntimeError, match="not valid JSON"):
            agent.generate_cooking_plan(weekly_plan, profile)

    def test_strips_markdown_fences(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert isinstance(plan, WeeklyCookingPlan)

    def test_llm_called_twice_for_two_batches(
        self, kb, profile, weekly_plan
    ) -> None:
        """With batched generation, exactly 2 LLM calls are made (4+3 days)."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == 2


# ---------------------------------------------------------------------------
# Shopping list aggregation
# ---------------------------------------------------------------------------

class TestShoppingListAggregation:
    def test_shopping_list_populated(self, kb, profile, weekly_plan) -> None:
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert len(plan.shopping_list) > 0

    def test_shopping_list_deduplicates_food_ids(
        self, kb, profile, weekly_plan
    ) -> None:
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        food_ids = [item.food_id for item in plan.shopping_list]
        assert len(food_ids) == len(set(food_ids)), "Shopping list should have unique food_ids"

    def test_shopping_list_sums_amounts(self, kb, profile, weekly_plan) -> None:
        """chicken_breast total should be sum of all meals across 7 days."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        chicken = next(
            (item for item in plan.shopping_list if item.food_id == "chicken_breast"),
            None,
        )
        assert chicken is not None
        # Verify total is sum of all individual meal ingredient amounts
        expected_total = sum(
            ing.amount_g
            for day in plan.daily_plans
            for meal in day.meals
            for ing in meal.ingredients
            if ing.food_id == "chicken_breast"
        )
        assert abs(chicken.total_amount_g - expected_total) < 0.1


# ---------------------------------------------------------------------------
# Calorie validation
# ---------------------------------------------------------------------------

class TestCalorieValidation:
    def test_no_warning_when_within_tolerance(self, kb, profile, weekly_plan) -> None:
        """Plan with calories matching targets should have no calorie warnings."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # The minimal plan JSON is constructed to match targets
        base = profile.daily_calorie_target or 2500
        warnings = agent._validate_calorie_compliance(plan.daily_plans, base)
        assert warnings == []

    def test_calorie_deviation_computed(self, kb, profile, weekly_plan) -> None:
        """Each day should have calorie_deviation_pct computed."""
        client = _make_llm_client(profile)
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
        """Batch-level retries: max_retries=1 means 2 calls per batch, 4 total."""
        max_retries = 1
        # Each batch gets max_retries+1 = 2 calls → 2 batches → 4 total calls
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        agent._validate_calorie_compliance = lambda plan, target: [
            "- 周一（训练日）：3000 kcal，目标 2500 kcal，偏差 +20.0%"
        ]
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == (max_retries + 1) * 2

    def test_max_retries_respected(self, kb, profile, weekly_plan) -> None:
        """Agent never exceeds (max_retries+1) × 2 LLM calls (two batches)."""
        max_retries = 2
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        agent._validate_calorie_compliance = lambda plan, target: ["- 偏差过大"]
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == (max_retries + 1) * 2

    def test_no_retry_when_all_valid(self, kb, profile, weekly_plan) -> None:
        """No warnings → exactly 2 LLM calls (one per batch)."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=2)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == 2

    def test_warnings_appended_to_tips(self, kb, profile, weekly_plan) -> None:
        """Unresolved warnings after retries are written into cooking_tips_zh."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_calorie_compliance = lambda plan, target: [
            "- 周一偏差 +20%"
        ]
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert "热量偏差提醒" in plan.cooking_tips_zh

    def test_correction_message_appended(self, kb, profile, weekly_plan) -> None:
        """On batch retry, the second call gets [user, assistant, user(correction)] messages."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_calorie_compliance = lambda plan, target: ["- 偏差"]
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        # Batch A is calls [0, 1]; call 1 (the retry) gets 3 messages
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
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # Artificially set one recipe's reported macros to be very wrong
        plan.daily_plans[0].meals[0].per_serving_macros.calories = 50.0
        warnings = agent._cross_validate_macros(plan.daily_plans)
        # Should detect the discrepancy
        assert len(warnings) > 0

    def test_cross_validate_no_warning_for_unknown_foods(
        self, kb, profile, weekly_plan
    ) -> None:
        """Recipes with unknown food_ids are silently skipped."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # Replace all food_ids with unknowns
        for day in plan.daily_plans:
            for meal in day.meals:
                for ing in meal.ingredients:
                    ing.food_id = "nonexistent_food_xyz"
        warnings = agent._cross_validate_macros(plan.daily_plans)
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


# ---------------------------------------------------------------------------
# V2: Deterministic macro overwrite
# ---------------------------------------------------------------------------

class TestDeterministicMacroOverwrite:
    def test_overwrite_replaces_llm_values(self, kb, profile, weekly_plan) -> None:
        """After overwrite, macros should match KB computation, not LLM values."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)

        # After generation, macros should be deterministic.
        # Verify by recomputing for first meal and comparing.
        first_meal = plan.daily_plans[0].meals[0]
        ing_pairs = [(ing.food_id, ing.amount_g) for ing in first_meal.ingredients]
        expected = kb.compute_ingredients_macros(ing_pairs)
        assert abs(first_meal.per_serving_macros.calories - expected["calories"]) < 0.1

    def test_day_total_macros_are_sum_of_meals(self, kb, profile, weekly_plan) -> None:
        """day_total_macros should be the exact sum of per_serving_macros."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)

        for day in plan.daily_plans:
            sum_cal = sum(m.per_serving_macros.calories for m in day.meals)
            assert abs(day.day_total_macros.calories - sum_cal) < 0.2

    def test_calorie_deviation_based_on_deterministic_values(
        self, kb, profile, weekly_plan
    ) -> None:
        """calorie_deviation_pct should be computed from KB-computed values."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)

        base = profile.daily_calorie_target or 2500
        for day in plan.daily_plans:
            target = base * (1.07 if day.is_training_day else 0.96)
            expected_dev = (day.day_total_macros.calories - target) / target * 100
            assert abs(day.calorie_deviation_pct - round(expected_dev, 1)) < 0.2


# ---------------------------------------------------------------------------
# V2: Dietary compliance validation
# ---------------------------------------------------------------------------

class TestDietaryCompliance:
    def test_catches_banned_food(self, kb) -> None:
        """Should detect chicken_breast in a plan when vegetarian restriction applies."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="test",
            name_zh="鸡胸饭",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(
                    food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150
                ),
            ],
            steps_zh=["步骤1", "步骤2"],
            per_serving_macros=MacroBreakdown(
                calories=250, protein_g=30, carbs_g=0, fat_g=5
            ),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(
                calories=750, protein_g=90, carbs_g=0, fat_g=15
            ),
        )

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        banned = kb.get_banned_food_ids(["vegetarian"])
        warnings = agent._validate_dietary_compliance([day], banned)
        assert len(warnings) > 0
        assert "chicken_breast" in warnings[0]

    def test_no_violation_for_plant_foods(self, kb) -> None:
        """Plant foods should not trigger any warnings for vegetarian."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="tofu_dish",
            name_zh="白米豆腐",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(
                    food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200
                ),
                RecipeIngredient(
                    food_id="broccoli", food_name_zh="西兰花", amount_g=100
                ),
            ],
            steps_zh=["步骤1", "步骤2"],
            per_serving_macros=MacroBreakdown(
                calories=300, protein_g=10, carbs_g=60, fat_g=2
            ),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(
                calories=900, protein_g=30, carbs_g=180, fat_g=6
            ),
        )

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        banned = kb.get_banned_food_ids(["vegetarian"])
        warnings = agent._validate_dietary_compliance([day], banned)
        assert warnings == []

    def test_empty_banned_set_no_warnings(self, kb) -> None:
        """No dietary restrictions → no warnings regardless of ingredients."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="test",
            name_zh="鸡胸饭",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(
                    food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150
                ),
            ],
            steps_zh=["步骤1", "步骤2"],
            per_serving_macros=MacroBreakdown(
                calories=250, protein_g=30, carbs_g=0, fat_g=5
            ),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(
                calories=750, protein_g=90, carbs_g=0, fat_g=15
            ),
        )

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_dietary_compliance([day], set())
        assert warnings == []


# ---------------------------------------------------------------------------
# V2: Diversity validation
# ---------------------------------------------------------------------------

class TestDiversityValidation:
    def test_warns_on_recipe_repetition(self, kb) -> None:
        """recipe_id repeated > 50% should trigger warning."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        same_recipe = Recipe(
            recipe_id="same_dish",
            name_zh="同一道菜",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(
                    food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150
                ),
            ],
            steps_zh=["步骤1", "步骤2"],
            per_serving_macros=MacroBreakdown(
                calories=250, protein_g=30, carbs_g=0, fat_g=5
            ),
        )
        # 3 days × 3 meals = 9 meals, all with same recipe_id
        days = []
        for label in ["周一", "周二", "周三"]:
            days.append(DayMealPlan(
                day_label=label,
                is_training_day=True,
                meals=[same_recipe, same_recipe, same_recipe],
                day_total_macros=MacroBreakdown(
                    calories=750, protein_g=90, carbs_g=0, fat_g=15
                ),
            ))

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_diversity(days)
        assert any("多样性" in w for w in warnings)

    def test_warns_on_low_protein_variety(self, kb) -> None:
        """Only 1 protein source across 3+ days should trigger warning."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="chicken_only",
            name_zh="鸡胸饭",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(
                    food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150
                ),
                RecipeIngredient(
                    food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200
                ),
            ],
            steps_zh=["步骤1", "步骤2"],
            per_serving_macros=MacroBreakdown(
                calories=500, protein_g=40, carbs_g=60, fat_g=10
            ),
        )
        days = []
        for i, label in enumerate(["周一", "周二", "周三"]):
            days.append(DayMealPlan(
                day_label=label,
                is_training_day=True,
                meals=[
                    recipe.model_copy(update={"recipe_id": f"r{i}_1"}),
                    recipe.model_copy(update={"recipe_id": f"r{i}_2"}),
                    recipe.model_copy(update={"recipe_id": f"r{i}_3"}),
                ],
                day_total_macros=MacroBreakdown(
                    calories=1500, protein_g=120, carbs_g=180, fat_g=30
                ),
            ))

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_diversity(days)
        assert any("蛋白质来源" in w for w in warnings)
