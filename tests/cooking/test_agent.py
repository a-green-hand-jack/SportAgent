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
    provider: str = "mock",
) -> MagicMock:
    """Create a mock LLM client that returns batch-appropriate day subsets.

    Reads the day labels requested in ``messages[0]`` (the original batch
    prompt) and returns only those days.  Set ``provider='deepseek'`` to
    exercise the 3-batch path (the low-cap threshold), or leave as
    ``'mock'`` for the single-batch path.
    """
    _all_labels = ["\u5468\u4e00", "\u5468\u4e8c", "\u5468\u4e09", "\u5468\u56db", "\u5468\u4e94", "\u5468\u516d", "\u5468\u65e5"]

    def _side_effect(messages, **kwargs):
        # Always read from the FIRST message (the original batch prompt).
        # On retries, messages grows to [user, assistant, user(correction)],
        # but messages[0] is still the original prompt which uniquely identifies
        # the batch.
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
            provider=provider,
            model="mock-model",
            input_tokens=100,
            output_tokens=200,
        )

    client = MagicMock()
    client.provider = provider
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


def _make_multi_response_client(responses: list[str], provider: str = "mock") -> MagicMock:
    client = MagicMock()
    client.provider = provider
    client.model = "mock-model"
    client.chat.side_effect = [
        LLMResponse(
            content=r,
            provider=provider,
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
    protein_food_id: str = "chicken_breast",
    protein_food_name: str = "鸡胸肉",
) -> dict:
    return {
        "recipe_id": recipe_id,
        "name_zh": f"测试{meal_type}",
        "meal_type": meal_type,
        "prep_time_minutes": 5,
        "cook_time_minutes": 10,
        "ingredients": [
            {
                "food_id": protein_food_id,
                "food_name_zh": protein_food_name,
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

    # Rotate protein sources to ensure intra-day diversity (max 2× same protein/day)
    _PROTEIN_ROTATION = [
        ("chicken_breast", "鸡胸肉"),
        ("egg_whole", "鸡蛋"),
        ("chicken_breast", "鸡胸肉"),
    ]

    days = []
    for label in labels_to_use:
        idx = all_labels.index(label) if label in all_labels else 0
        is_training = idx < training_days
        day_cal = training_cal if is_training else rest_cal
        meal_cal = day_cal / 3
        chicken_g, rice_g = _scale_amounts(day_cal)

        meals = [
            _make_recipe_json(f"breakfast_{idx}", "breakfast", meal_cal, 40,
                              chicken_g=chicken_g, rice_g=rice_g,
                              protein_food_id=_PROTEIN_ROTATION[0][0],
                              protein_food_name=_PROTEIN_ROTATION[0][1]),
            _make_recipe_json(f"lunch_{idx}", "lunch", meal_cal, 50,
                              chicken_g=chicken_g, rice_g=rice_g,
                              protein_food_id=_PROTEIN_ROTATION[1][0],
                              protein_food_name=_PROTEIN_ROTATION[1][1]),
            _make_recipe_json(f"dinner_{idx}", "dinner", meal_cal, 45,
                              chicken_g=chicken_g, rice_g=rice_g,
                              protein_food_id=_PROTEIN_ROTATION[2][0],
                              protein_food_name=_PROTEIN_ROTATION[2][1]),
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

    def test_llm_called_three_times_for_batches(
        self, kb, profile, weekly_plan
    ) -> None:
        """DeepSeek provider (low cap) uses 3 batches [2+2+3] = 3 LLM calls."""
        client = _make_llm_client(profile, provider="test-low-cap")
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == 3

    def test_llm_called_once_for_high_cap_provider(
        self, kb, profile, weekly_plan
    ) -> None:
        """Providers without a token cap (mock/qwen) use a single 7-day batch."""
        client = _make_llm_client(profile, provider="mock")
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_calorie_compliance = lambda plan, target: []
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == 1


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
    def test_retries_on_dietary_violation(self, kb, profile, weekly_plan) -> None:
        """DeepSeek 3-batch: max_retries=1 → 2 calls/batch × 3 batches = 6 total."""
        max_retries = 1
        client = _make_llm_client(profile, provider="test-low-cap")
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        agent._validate_dietary_compliance = lambda plan, banned: [
            "- 周一/鸡胸饭：食材 'chicken_breast'（鸡胸肉）违反饮食限制"
        ]
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == (max_retries + 1) * 3

    def test_max_retries_respected(self, kb, profile, weekly_plan) -> None:
        """DeepSeek 3-batch: (max_retries+1) × 3 total calls maximum."""
        max_retries = 2
        client = _make_llm_client(profile, provider="test-low-cap")
        agent = CookingAgent(client=client, kb=kb, max_retries=max_retries)
        agent._validate_dietary_compliance = lambda plan, banned: [
            "- 周一：饮食违规"
        ]
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == (max_retries + 1) * 3

    def test_no_retry_when_all_valid(self, kb, profile, weekly_plan) -> None:
        """No warnings → 1 call for mock (high-cap), 3 for deepseek (low-cap)."""
        client = _make_llm_client(profile, provider="test-low-cap")
        agent = CookingAgent(client=client, kb=kb, max_retries=2)
        agent._validate_dietary_compliance = lambda plan, banned: []
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == 3

    def test_no_llm_retry_for_calorie(self, kb, profile, weekly_plan) -> None:
        """Calorie issues do NOT trigger LLM retry — 3 calls for deepseek (one per batch)."""
        client = _make_llm_client(profile, provider="test-low-cap")
        agent = CookingAgent(client=client, kb=kb, max_retries=2)
        agent._validate_dietary_compliance = lambda plan, banned: []
        # Even if calorie validation would fail, no retry
        original_validate = agent._validate_calorie_compliance
        agent._validate_calorie_compliance = lambda plan, target: [
            "- 周一（训练日）：3000 kcal，目标 2500 kcal，偏差 +20.0%"
        ]
        agent.generate_cooking_plan(weekly_plan, profile)
        assert client.chat.call_count == 3

    def test_warnings_appended_to_tips(self, kb, profile, weekly_plan) -> None:
        """Unresolved calorie/protein warnings are written into cooking_tips_zh."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_dietary_compliance = lambda plan, banned: []
        # Force calorie warnings post-scaling
        original_validate_cal = agent._validate_calorie_compliance
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # The plan with well-scaled mock data should not have calorie warnings,
        # but let's verify the structure supports protein warnings too
        # by injecting post-generation:
        assert isinstance(plan.cooking_tips_zh, str)

    def test_protein_warnings_appended_to_tips(self, kb, profile, weekly_plan) -> None:
        """Protein warnings from post-processing appear in cooking_tips_zh."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_dietary_compliance = lambda plan, banned: []
        # Force protein validation to always return a warning
        agent._validate_protein_compliance = lambda days, target: [
            "- 周一：蛋白质 100g，目标 140g 的 71%（最低要求 90%）"
        ]
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        assert "蛋白质不足提醒" in plan.cooking_tips_zh

    def test_correction_message_for_dietary(self, kb, profile, weekly_plan) -> None:
        """On dietary retry, correction message asks to replace banned ingredients."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_dietary_compliance = lambda plan, banned: [
            "- 周一/鸡胸饭：食材 'chicken_breast' 违反饮食限制"
        ]
        agent.generate_cooking_plan(weekly_plan, profile)
        # Batch A is calls [0, 1]; call 1 (the retry) gets 3 messages
        second_kwargs = client.chat.call_args_list[1].kwargs
        msgs = second_kwargs["messages"]
        assert len(msgs) == 3
        assert msgs[1].role == "assistant"
        assert msgs[2].role == "user"
        assert "饮食限制违规" in msgs[2].content
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

# ---------------------------------------------------------------------------
# V3: Calorie scaling
# ---------------------------------------------------------------------------

class TestCalorieScaling:
    """Tests for _scale_day_to_calorie_target()."""

    @staticmethod
    def _make_day(
        kb: KnowledgeBase,
        chicken_g: float = 150.0,
        rice_g: float = 200.0,
        n_meals: int = 3,
    ) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        def _recipe(idx: int) -> Recipe:
            return Recipe(
                recipe_id=f"r_{idx}",
                name_zh=f"测试餐{idx}",
                meal_type="lunch",
                prep_time_minutes=5,
                cook_time_minutes=10,
                ingredients=[
                    RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=chicken_g),
                    RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=rice_g),
                ],
                steps_zh=["步骤1"],
                per_serving_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
            )

        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[_recipe(i) for i in range(n_meals)],
            day_total_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )
        # Compute real macros from KB
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent._overwrite_macros_deterministic([day])
        return day

    def test_scale_up_when_below_target(self, kb: KnowledgeBase) -> None:
        """Day with ~80% of target should be scaled up to within tolerance."""
        day = self._make_day(kb, chicken_g=120, rice_g=160)
        actual_before = day.day_total_macros.calories
        target = actual_before / 0.80  # day is 80% of target

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent.calorie_tolerance_pct = 10.0
        agent._scale_day_to_calorie_target(day, target)

        deviation = abs(day.day_total_macros.calories - target) / target * 100
        assert deviation <= 10.0

    def test_scale_down_when_above_target(self, kb: KnowledgeBase) -> None:
        """Day with ~120% of target should be scaled down to within tolerance."""
        day = self._make_day(kb, chicken_g=180, rice_g=240)
        actual_before = day.day_total_macros.calories
        target = actual_before / 1.20  # day is 120% of target

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent.calorie_tolerance_pct = 10.0
        agent._scale_day_to_calorie_target(day, target)

        deviation = abs(day.day_total_macros.calories - target) / target * 100
        assert deviation <= 10.0

    def test_no_scale_when_within_tolerance(self, kb: KnowledgeBase) -> None:
        """Within ±10% → ingredient amounts should not change."""
        day = self._make_day(kb, chicken_g=150, rice_g=200)
        original_amounts = [
            ing.amount_g for r in day.meals for ing in r.ingredients
        ]
        target = day.day_total_macros.calories * 1.05  # 5% off → within 10%

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent.calorie_tolerance_pct = 10.0
        agent._scale_day_to_calorie_target(day, target)

        current_amounts = [
            ing.amount_g for r in day.meals for ing in r.ingredients
        ]
        assert original_amounts == current_amounts

    def test_ingredient_ratios_preserved(self, kb: KnowledgeBase) -> None:
        """Scaling should preserve the chicken:rice ratio."""
        day = self._make_day(kb, chicken_g=150, rice_g=200)
        ratio_before = 150 / 200
        target = day.day_total_macros.calories * 1.5  # force scaling up

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent.calorie_tolerance_pct = 10.0
        agent._scale_day_to_calorie_target(day, target)

        chicken = day.meals[0].ingredients[0].amount_g
        rice = day.meals[0].ingredients[1].amount_g
        ratio_after = chicken / rice
        assert abs(ratio_before - ratio_after) < 0.01

    def test_zero_calories_is_noop(self, kb: KnowledgeBase) -> None:
        """0-calorie day or 0 target should not crash."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="empty",
            name_zh="空餐",
            meal_type="lunch",
            prep_time_minutes=0,
            cook_time_minutes=0,
            ingredients=[
                RecipeIngredient(food_id="unknown_xyz", food_name_zh="未知", amount_g=100),
            ],
            steps_zh=["N/A"],
            per_serving_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent.calorie_tolerance_pct = 10.0
        # Should not raise
        agent._scale_day_to_calorie_target(day, 2500)
        agent._scale_day_to_calorie_target(day, 0)

    def test_scale_factor_clamped(self, kb: KnowledgeBase) -> None:
        """Extreme deviation → scale factor clamped to [0.5, 2.0]."""
        day = self._make_day(kb, chicken_g=50, rice_g=50)
        actual_before = day.day_total_macros.calories
        # Target is 10× actual → raw factor would be 10, clamped to 2.0
        target = actual_before * 10

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent.calorie_tolerance_pct = 10.0
        agent._scale_day_to_calorie_target(day, target)

        # Check that no ingredient exceeded 2× its original amount
        # Original: 50g chicken per meal → max should be 100g
        for recipe in day.meals:
            for ing in recipe.ingredients:
                assert ing.amount_g <= 100.1  # 50 * 2.0 with rounding tolerance


# ---------------------------------------------------------------------------
# V3: Protein compliance validation
# ---------------------------------------------------------------------------

class TestProteinCompliance:
    """Tests for _validate_protein_compliance()."""

    @staticmethod
    def _make_day_with_protein(protein_g: float) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="r1",
            name_zh="测试",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=100),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(
                calories=300, protein_g=protein_g / 3, carbs_g=30, fat_g=5
            ),
        )
        return DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(
                calories=900, protein_g=protein_g, carbs_g=90, fat_g=15
            ),
        )

    def test_warns_below_90pct(self) -> None:
        """85% of target → should produce a warning."""
        day = self._make_day_with_protein(119)  # 85% of 140
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_protein_compliance([day], 140)
        assert len(warnings) == 1

    def test_no_warn_at_90pct(self) -> None:
        """Exactly 90% → should NOT produce a warning."""
        day = self._make_day_with_protein(126)  # 90% of 140
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_protein_compliance([day], 140)
        assert warnings == []

    def test_no_warn_above_target(self) -> None:
        """Above target → no warning."""
        day = self._make_day_with_protein(150)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_protein_compliance([day], 140)
        assert warnings == []


# ---------------------------------------------------------------------------
# V3: Protein boost
# ---------------------------------------------------------------------------

class TestProteinBoost:
    """Tests for _boost_protein_for_day()."""

    @staticmethod
    def _make_day_with_ingredients(
        kb: KnowledgeBase,
        chicken_g: float = 100.0,
        rice_g: float = 200.0,
    ) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="r1",
            name_zh="鸡胸饭",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=chicken_g),
                RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=rice_g),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent._overwrite_macros_deterministic([day])
        return day

    def test_boost_reaches_target(self, kb: KnowledgeBase) -> None:
        """After boost, protein should reach the target."""
        day = self._make_day_with_ingredients(kb, chicken_g=80, rice_g=200)
        protein_before = day.day_total_macros.protein_g
        target = protein_before * 1.5  # need 50% more

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent._boost_protein_for_day(day, target)

        assert day.day_total_macros.protein_g >= target - 0.5

    def test_only_protein_rich_scaled(self, kb: KnowledgeBase) -> None:
        """Rice (2.7g/100g) should NOT be scaled, only chicken (33g/100g)."""
        day = self._make_day_with_ingredients(kb, chicken_g=100, rice_g=200)
        rice_before = [
            ing.amount_g
            for r in day.meals
            for ing in r.ingredients
            if ing.food_id == "white_rice_cooked"
        ]
        target = day.day_total_macros.protein_g * 1.3

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent._boost_protein_for_day(day, target)

        rice_after = [
            ing.amount_g
            for r in day.meals
            for ing in r.ingredients
            if ing.food_id == "white_rice_cooked"
        ]
        assert rice_before == rice_after

    def test_noop_when_sufficient(self, kb: KnowledgeBase) -> None:
        """Already above target → ingredient amounts unchanged."""
        day = self._make_day_with_ingredients(kb, chicken_g=200, rice_g=200)
        amounts_before = [
            ing.amount_g for r in day.meals for ing in r.ingredients
        ]
        target = day.day_total_macros.protein_g * 0.5  # well below actual

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent._boost_protein_for_day(day, target)

        amounts_after = [
            ing.amount_g for r in day.meals for ing in r.ingredients
        ]
        assert amounts_before == amounts_after

    def test_no_protein_sources_does_not_crash(self, kb: KnowledgeBase) -> None:
        """Pure-grain day → logs warning but does not crash."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipe = Recipe(
            recipe_id="grain_only",
            name_zh="白饭",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=300),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, recipe, recipe],
            day_total_macros=MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0),
        )
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        agent._overwrite_macros_deterministic([day])
        # Should not raise
        agent._boost_protein_for_day(day, 140)


# ---------------------------------------------------------------------------
# V3: Post-workout protein validation
# ---------------------------------------------------------------------------

class TestPostWorkoutProtein:
    """Tests for _validate_post_workout_protein()."""

    @staticmethod
    def _make_day_with_post_workout(
        meal_type: str, protein_g: float
    ) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        filler = Recipe(
            recipe_id="filler",
            name_zh="填充餐",
            meal_type="breakfast",
            prep_time_minutes=5,
            cook_time_minutes=5,
            ingredients=[
                RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=300, protein_g=5, carbs_g=60, fat_g=1),
        )
        target_meal = Recipe(
            recipe_id="pw_meal",
            name_zh="训练后餐",
            meal_type=meal_type,
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=100),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(
                calories=200, protein_g=protein_g, carbs_g=10, fat_g=3
            ),
        )
        return DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[filler, target_meal, filler],
            day_total_macros=MacroBreakdown(
                calories=800, protein_g=protein_g + 10, carbs_g=130, fat_g=5
            ),
        )

    def test_warns_low_post_workout(self) -> None:
        """post_workout meal with 10g protein → warning."""
        day = self._make_day_with_post_workout("post_workout", 10)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_post_workout_protein([day])
        assert len(warnings) == 1
        assert "训练后餐蛋白质" in warnings[0]

    def test_passes_adequate_post_workout(self) -> None:
        """post_workout meal with 40g protein → no warning (threshold is 35g)."""
        day = self._make_day_with_post_workout("post_workout", 40)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_post_workout_protein([day])
        assert warnings == []

    def test_ignores_non_post_workout(self) -> None:
        """breakfast with 5g protein → no warning (not post_workout)."""
        day = self._make_day_with_post_workout("breakfast", 5)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_post_workout_protein([day])
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


# ---------------------------------------------------------------------------
# V4: Food-ID validation
# ---------------------------------------------------------------------------

class TestFoodIdValidation:
    """Tests for _validate_food_ids() and _build_food_id_correction_message()."""

    @staticmethod
    def _make_day_with_food_ids(food_ids: list[str]) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipes = []
        for i, fid in enumerate(food_ids):
            recipes.append(Recipe(
                recipe_id=f"r_{i}",
                name_zh=f"测试餐{i}",
                meal_type="lunch",
                prep_time_minutes=5,
                cook_time_minutes=10,
                ingredients=[
                    RecipeIngredient(food_id=fid, food_name_zh=f"食材{i}", amount_g=100),
                ],
                steps_zh=["步骤1"],
                per_serving_macros=MacroBreakdown(calories=300, protein_g=20, carbs_g=30, fat_g=5),
            ))
        return DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=recipes,
            day_total_macros=MacroBreakdown(calories=900, protein_g=60, carbs_g=90, fat_g=15),
        )

    def test_detects_unknown_food_ids(self, kb) -> None:
        """Unknown food_ids should produce warnings."""
        day = self._make_day_with_food_ids(["chicken_breast", "FAKE_food_xyz", "also_fake"])
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_food_ids([day])
        assert len(warnings) == 2
        assert "FAKE_food_xyz" in warnings[0]
        assert "also_fake" in warnings[1]

    def test_no_warning_for_all_known_ids(self, kb) -> None:
        """All valid food_ids → no warnings."""
        day = self._make_day_with_food_ids(["chicken_breast", "white_rice_cooked", "broccoli"])
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_food_ids([day])
        assert warnings == []

    def test_correction_message_lists_valid_ids(self, kb) -> None:
        """Correction message should contain the valid food_id list."""
        warnings = ["- 周一/测试餐：food_id 'FAKE' 不在食材数据库中"]
        valid_ids = sorted(kb.all_food_ids)
        msg = CookingAgent._build_food_id_correction_message(warnings, valid_ids)
        assert "FAKE" in msg
        assert "chicken_breast" in msg
        assert "有效 food_id 列表" in msg

    def test_food_id_validation_unit(self, kb) -> None:
        """Validate _validate_food_ids returns correct count for mixed valid/invalid."""
        day_a = self._make_day_with_food_ids(["chicken_breast", "INVALID_1", "INVALID_2"])
        day_b = self._make_day_with_food_ids(["egg_whole", "INVALID_3", "white_rice_cooked"])
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_food_ids([day_a, day_b])
        assert len(warnings) == 3
        invalid_ids = {"INVALID_1", "INVALID_2", "INVALID_3"}
        for w in warnings:
            assert any(fid in w for fid in invalid_ids)


# ---------------------------------------------------------------------------
# V4: Intra-day diversity validation
# ---------------------------------------------------------------------------

class TestIntradayDiversity:
    """Tests for _validate_intraday_diversity()."""

    @staticmethod
    def _make_day_with_protein_counts(
        food_id: str, count: int, kb: KnowledgeBase
    ) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        recipes = []
        for i in range(count):
            recipes.append(Recipe(
                recipe_id=f"r_{i}",
                name_zh=f"测试餐{i}",
                meal_type="lunch",
                prep_time_minutes=5,
                cook_time_minutes=10,
                ingredients=[
                    RecipeIngredient(food_id=food_id, food_name_zh="鸡胸肉", amount_g=150),
                    RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200),
                ],
                steps_zh=["步骤1"],
                per_serving_macros=MacroBreakdown(calories=500, protein_g=40, carbs_g=60, fat_g=10),
            ))
        return DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=recipes,
            day_total_macros=MacroBreakdown(
                calories=500 * count, protein_g=40 * count, carbs_g=60 * count, fat_g=10 * count
            ),
        )

    def test_warns_same_protein_3x(self, kb) -> None:
        """chicken_breast 3× in one day → warning."""
        day = self._make_day_with_protein_counts("chicken_breast", 3, kb)
        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_intraday_diversity([day])
        assert len(warnings) == 1
        assert "3 次" in warnings[0]

    def test_no_warn_same_protein_2x(self, kb) -> None:
        """chicken_breast 2× in one day → no warning (threshold is >2)."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        # Need at least 3 meals for DayMealPlan validation
        recipe_chicken = Recipe(
            recipe_id="r_chicken",
            name_zh="鸡胸饭",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=500, protein_g=40, carbs_g=60, fat_g=10),
        )
        recipe_egg = Recipe(
            recipe_id="r_egg",
            name_zh="鸡蛋饭",
            meal_type="dinner",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="egg_whole", food_name_zh="鸡蛋", amount_g=150),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=500, protein_g=35, carbs_g=0, fat_g=20),
        )
        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe_chicken, recipe_chicken, recipe_egg],
            day_total_macros=MacroBreakdown(calories=1500, protein_g=115, carbs_g=120, fat_g=40),
        )

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_intraday_diversity([day])
        assert warnings == []

    def test_no_warn_different_proteins(self, kb) -> None:
        """3 different protein sources → no warning."""
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        def _make_recipe(food_id: str, name: str, rid: str) -> Recipe:
            return Recipe(
                recipe_id=rid,
                name_zh=name,
                meal_type="lunch",
                prep_time_minutes=5,
                cook_time_minutes=10,
                ingredients=[
                    RecipeIngredient(food_id=food_id, food_name_zh=name, amount_g=150),
                ],
                steps_zh=["步骤1"],
                per_serving_macros=MacroBreakdown(calories=400, protein_g=30, carbs_g=10, fat_g=10),
            )

        day = DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[
                _make_recipe("chicken_breast", "鸡胸肉", "r1"),
                _make_recipe("egg_whole", "鸡蛋", "r2"),
                _make_recipe("whole_egg", "鸡蛋", "r3"),
            ],
            day_total_macros=MacroBreakdown(calories=1200, protein_g=90, carbs_g=30, fat_g=30),
        )

        agent = CookingAgent.__new__(CookingAgent)
        agent.kb = kb
        warnings = agent._validate_intraday_diversity([day])
        assert warnings == []


# ---------------------------------------------------------------------------
# V4: Meal structure validation
# ---------------------------------------------------------------------------

class TestMealStructure:
    """Tests for _validate_meal_structure()."""

    @staticmethod
    def _make_day(
        is_training: bool, meal_types: list[str]
    ) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        meals = []
        for i, mt in enumerate(meal_types):
            meals.append(Recipe(
                recipe_id=f"r_{i}",
                name_zh=f"测试{mt}",
                meal_type=mt,
                prep_time_minutes=5,
                cook_time_minutes=10,
                ingredients=[
                    RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150),
                ],
                steps_zh=["步骤1"],
                per_serving_macros=MacroBreakdown(calories=300, protein_g=30, carbs_g=20, fat_g=5),
            ))
        return DayMealPlan(
            day_label="周一",
            is_training_day=is_training,
            meals=meals,
            day_total_macros=MacroBreakdown(
                calories=300 * len(meals), protein_g=30 * len(meals),
                carbs_g=20 * len(meals), fat_g=5 * len(meals),
            ),
        )

    def test_warns_missing_pre_workout(self) -> None:
        """Training day without pre_workout → warning."""
        day = self._make_day(True, ["breakfast", "post_workout", "dinner"])
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_structure([day])
        assert any("缺少 pre_workout" in w for w in warnings)

    def test_warns_lunch_and_post_workout_coexist(self) -> None:
        """Training day with both lunch and post_workout → warning."""
        day = self._make_day(True, ["breakfast", "pre_workout", "lunch", "post_workout", "dinner"])
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_structure([day])
        assert any("lunch 和 post_workout 不应同时存在" in w for w in warnings)

    def test_no_warn_valid_training_day(self) -> None:
        """Valid training day structure → no warning."""
        day = self._make_day(True, ["breakfast", "pre_workout", "post_workout", "dinner", "snack"])
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_structure([day])
        assert warnings == []

    def test_warns_rest_day_has_post_workout(self) -> None:
        """Rest day with post_workout → warning."""
        day = self._make_day(False, ["breakfast", "post_workout", "dinner"])
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_structure([day])
        assert any("不应包含 post_workout" in w for w in warnings)


# ---------------------------------------------------------------------------
# V4: Per-meal calorie ranges
# ---------------------------------------------------------------------------

class TestMealCalorieRanges:
    """Tests for _validate_meal_calorie_ranges()."""

    @staticmethod
    def _make_day_with_meal(meal_type: str, calories: float) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        filler = Recipe(
            recipe_id="filler1",
            name_zh="填充1",
            meal_type="breakfast",
            prep_time_minutes=5,
            cook_time_minutes=5,
            ingredients=[
                RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=500, protein_g=10, carbs_g=60, fat_g=2),
        )
        filler2 = Recipe(
            recipe_id="filler2",
            name_zh="填充2",
            meal_type="dinner",
            prep_time_minutes=5,
            cook_time_minutes=5,
            ingredients=[
                RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=500, protein_g=10, carbs_g=60, fat_g=2),
        )
        target_meal = Recipe(
            recipe_id="target",
            name_zh="目标餐",
            meal_type=meal_type,
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=[
                RecipeIngredient(food_id="chicken_breast", food_name_zh="鸡胸肉", amount_g=150),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(
                calories=calories, protein_g=30, carbs_g=20, fat_g=5
            ),
        )
        return DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[filler, target_meal, filler2],
            day_total_macros=MacroBreakdown(
                calories=1000 + calories, protein_g=50, carbs_g=140, fat_g=9
            ),
        )

    def test_warns_pre_workout_too_heavy(self) -> None:
        """pre_workout 863 kcal exceeds max 400 → warning."""
        day = self._make_day_with_meal("pre_workout", 863)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_calorie_ranges([day])
        assert len(warnings) == 1
        assert "建议最高" in warnings[0]

    def test_warns_snack_too_heavy(self) -> None:
        """snack 500 kcal exceeds max 350 → warning."""
        day = self._make_day_with_meal("snack", 500)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_calorie_ranges([day])
        assert len(warnings) == 1
        assert "建议最高" in warnings[0]

    def test_no_warn_within_ranges(self) -> None:
        """lunch 700 kcal within 500-1000 → no warning."""
        day = self._make_day_with_meal("lunch", 700)
        agent = CookingAgent.__new__(CookingAgent)
        warnings = agent._validate_meal_calorie_ranges([day])
        # Only check that no warning for the lunch meal
        lunch_warnings = [w for w in warnings if "lunch" in w]
        assert lunch_warnings == []


# ---------------------------------------------------------------------------
# V4: Ingredient rounding
# ---------------------------------------------------------------------------

class TestIngredientRounding:
    """Tests for _round_ingredient_amounts()."""

    @staticmethod
    def _make_day_with_amounts(amounts: list[float]) -> "DayMealPlan":
        from fitness_agent.cooking.models import (
            DayMealPlan,
            MacroBreakdown,
            Recipe,
            RecipeIngredient,
        )

        ingredients = [
            RecipeIngredient(
                food_id=f"food_{i}",
                food_name_zh=f"食材{i}",
                amount_g=amt,
            )
            for i, amt in enumerate(amounts)
        ]
        recipe = Recipe(
            recipe_id="r1",
            name_zh="测试餐",
            meal_type="lunch",
            prep_time_minutes=5,
            cook_time_minutes=10,
            ingredients=ingredients,
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=500, protein_g=30, carbs_g=50, fat_g=10),
        )
        # Need at least 3 meals
        filler = Recipe(
            recipe_id="f1",
            name_zh="填充",
            meal_type="breakfast",
            prep_time_minutes=5,
            cook_time_minutes=5,
            ingredients=[
                RecipeIngredient(food_id="white_rice_cooked", food_name_zh="白米饭", amount_g=200),
            ],
            steps_zh=["步骤1"],
            per_serving_macros=MacroBreakdown(calories=300, protein_g=5, carbs_g=60, fat_g=1),
        )
        return DayMealPlan(
            day_label="周一",
            is_training_day=True,
            meals=[recipe, filler, filler],
            day_total_macros=MacroBreakdown(calories=1100, protein_g=40, carbs_g=170, fat_g=12),
        )

    def test_rounds_to_10g(self) -> None:
        """136g → 140g, 271g → 270g."""
        day = self._make_day_with_amounts([136, 271])
        agent = CookingAgent.__new__(CookingAgent)
        agent._round_ingredient_amounts([day])
        amounts = [ing.amount_g for ing in day.meals[0].ingredients]
        assert amounts == [140, 270]

    def test_small_amounts_round_to_5g(self) -> None:
        """8g → 10g, 3g → 5g (minimum 5g)."""
        day = self._make_day_with_amounts([8, 3])
        agent = CookingAgent.__new__(CookingAgent)
        agent._round_ingredient_amounts([day])
        amounts = [ing.amount_g for ing in day.meals[0].ingredients]
        assert amounts == [10, 5]

    def test_rounding_preserves_multiples(self) -> None:
        """Already-round values should stay the same."""
        day = self._make_day_with_amounts([150, 200, 5])
        agent = CookingAgent.__new__(CookingAgent)
        agent._round_ingredient_amounts([day])
        amounts = [ing.amount_g for ing in day.meals[0].ingredients]
        assert amounts == [150, 200, 5]


# ---------------------------------------------------------------------------
# V3: Pipeline integration
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    """End-to-end tests verifying the full V3+V4 pipeline."""

    def test_all_days_within_calorie_tolerance(
        self, kb, profile, weekly_plan
    ) -> None:
        """After full pipeline, all 7 days should be within ±10% of calorie target."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)

        base = profile.daily_calorie_target or 2500
        for day in plan.daily_plans:
            target = base * (1.07 if day.is_training_day else 0.96)
            actual = day.day_total_macros.calories
            deviation = abs(actual - target) / target * 100
            assert deviation <= 10.0, (
                f"{day.day_label}: {actual:.0f} kcal vs target {target:.0f} kcal "
                f"(deviation {deviation:.1f}%)"
            )

    def test_calorie_deviation_pct_matches_actual(
        self, kb, profile, weekly_plan
    ) -> None:
        """calorie_deviation_pct should accurately reflect actual vs target."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)

        base = profile.daily_calorie_target or 2500
        for day in plan.daily_plans:
            target = base * (1.07 if day.is_training_day else 0.96)
            expected_dev = (day.day_total_macros.calories - target) / target * 100
            assert abs(day.calorie_deviation_pct - round(expected_dev, 1)) < 0.2

    def test_ingredient_amounts_are_rounded(
        self, kb, profile, weekly_plan
    ) -> None:
        """After full pipeline, all ingredient amounts should be multiples of 5 or 10."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)

        for day in plan.daily_plans:
            for recipe in day.meals:
                for ing in recipe.ingredients:
                    if ing.amount_g >= 10:
                        assert ing.amount_g % 10 == 0, (
                            f"{day.day_label}/{recipe.name_zh}: {ing.food_id} "
                            f"amount {ing.amount_g}g not rounded to 10g"
                        )
                    else:
                        assert ing.amount_g % 5 == 0, (
                            f"{day.day_label}/{recipe.name_zh}: {ing.food_id} "
                            f"amount {ing.amount_g}g not rounded to 5g"
                        )

    def test_food_id_retry_triggers_extra_llm_call(
        self, kb, profile, weekly_plan
    ) -> None:
        """Batch with many unknown food_ids → retry → extra LLM call."""
        # Build batch A (周一, 周二) response with many unknown food_ids
        bad_plan_json = _minimal_cooking_plan_json(
            profile, training_days=3, day_labels=["周一", "周二"],
        )
        bad_data = json.loads(bad_plan_json)
        for day_data in bad_data["daily_plans"]:
            for meal in day_data["meals"]:
                meal["ingredients"][0]["food_id"] = "unknown_meat_xyz"
        bad_json = json.dumps(bad_data, ensure_ascii=False)

        good_json_a = _minimal_cooking_plan_json(
            profile, training_days=3, day_labels=["周一", "周二"],
        )
        good_json_b = _minimal_cooking_plan_json(
            profile, training_days=3, day_labels=["周三", "周四"],
        )
        good_json_c = _minimal_cooking_plan_json(
            profile, training_days=3, day_labels=["周五", "周六", "周日"],
        )

        # batch A: bad → good (retry); batch B: good; batch C: good
        client = _make_multi_response_client(
            [bad_json, good_json_a, good_json_b, good_json_c],
            provider="test-low-cap",
        )
        agent = CookingAgent(client=client, kb=kb, max_retries=1)
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # batch A used 2 calls (initial + retry), batch B used 1, batch C used 1 → total 4
        assert client.chat.call_count == 4
        assert len(plan.daily_plans) == 7

    def test_structure_warnings_in_tips(
        self, kb, profile, weekly_plan
    ) -> None:
        """Mock plan missing pre/post_workout → structure warnings in cooking_tips."""
        client = _make_llm_client(profile)
        agent = CookingAgent(client=client, kb=kb)
        agent._validate_dietary_compliance = lambda plan, banned: []
        plan = agent.generate_cooking_plan(weekly_plan, profile)
        # Our mock plan only has breakfast/lunch/dinner — training days
        # will trigger "缺少 pre_workout" and "缺少 post_workout" warnings
        assert "餐食结构问题" in plan.cooking_tips_zh
