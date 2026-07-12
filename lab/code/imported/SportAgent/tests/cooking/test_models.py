"""Tests for cooking output models (Pydantic validation)."""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from fitness_agent.cooking.models import (
    DayMealPlan,
    MacroBreakdown,
    MealPrepSuggestion,
    Recipe,
    RecipeIngredient,
    ShoppingItem,
    WeeklyCookingPlan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_macro(cal: float = 400, pro: float = 30, carbs: float = 50, fat: float = 10) -> dict:
    return {"calories": cal, "protein_g": pro, "carbs_g": carbs, "fat_g": fat}


def _make_ingredient(food_id: str = "chicken_breast", name: str = "鸡胸肉", amount: float = 150) -> dict:
    return {"food_id": food_id, "food_name_zh": name, "amount_g": amount}


def _make_recipe(
    recipe_id: str = "test_recipe",
    meal_type: str = "lunch",
    cal: float = 400,
) -> dict:
    return {
        "recipe_id": recipe_id,
        "name_zh": "测试菜品",
        "meal_type": meal_type,
        "prep_time_minutes": 5,
        "cook_time_minutes": 10,
        "ingredients": [_make_ingredient()],
        "steps_zh": ["步骤1", "步骤2"],
        "per_serving_macros": _make_macro(cal=cal),
    }


def _make_day(
    day_label: str = "周一",
    is_training: bool = True,
    n_meals: int = 3,
    cal_per_meal: float = 800,
) -> dict:
    meals = [_make_recipe(recipe_id=f"r{i}", cal=cal_per_meal) for i in range(n_meals)]
    total_cal = cal_per_meal * n_meals
    return {
        "day_label": day_label,
        "is_training_day": is_training,
        "meals": meals,
        "day_total_macros": _make_macro(cal=total_cal, pro=90, carbs=150, fat=30),
    }


WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _make_weekly_plan(n_days: int = 7) -> dict:
    days = [_make_day(day_label=WEEKDAYS[i], is_training=(i < 4)) for i in range(n_days)]
    return {
        "user_name": "TestUser",
        "daily_plans": days,
    }


# ---------------------------------------------------------------------------
# MacroBreakdown
# ---------------------------------------------------------------------------

class TestMacroBreakdown:
    def test_valid_macro(self) -> None:
        m = MacroBreakdown(**_make_macro())
        assert m.calories == 400

    def test_negative_calories_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MacroBreakdown(calories=-1, protein_g=0, carbs_g=0, fat_g=0)

    def test_zero_values_allowed(self) -> None:
        m = MacroBreakdown(calories=0, protein_g=0, carbs_g=0, fat_g=0)
        assert m.calories == 0


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------

class TestRecipe:
    def test_valid_recipe(self) -> None:
        r = Recipe(**_make_recipe())
        assert r.recipe_id == "test_recipe"

    def test_recipe_requires_ingredients(self) -> None:
        data = _make_recipe()
        data["ingredients"] = []
        with pytest.raises(ValidationError):
            Recipe(**data)

    def test_recipe_requires_steps(self) -> None:
        data = _make_recipe()
        data["steps_zh"] = []
        with pytest.raises(ValidationError):
            Recipe(**data)

    def test_substitution_notes_default_empty(self) -> None:
        r = Recipe(**_make_recipe())
        assert r.substitution_notes == []

    def test_scaling_notes_optional(self) -> None:
        r = Recipe(**_make_recipe())
        assert r.scaling_notes is None


# ---------------------------------------------------------------------------
# DayMealPlan
# ---------------------------------------------------------------------------

class TestDayMealPlan:
    def test_valid_day(self) -> None:
        d = DayMealPlan(**_make_day())
        assert d.day_label == "周一"

    def test_day_requires_at_least_3_meals(self) -> None:
        data = _make_day(n_meals=2)
        with pytest.raises(ValidationError):
            DayMealPlan(**data)

    def test_calorie_deviation_defaults_to_zero(self) -> None:
        d = DayMealPlan(**_make_day())
        assert d.calorie_deviation_pct == 0.0


# ---------------------------------------------------------------------------
# WeeklyCookingPlan
# ---------------------------------------------------------------------------

class TestWeeklyCookingPlan:
    def test_valid_plan(self) -> None:
        p = WeeklyCookingPlan(**_make_weekly_plan())
        assert p.user_name == "TestUser"
        assert len(p.daily_plans) == 7

    def test_plan_requires_7_days(self) -> None:
        with pytest.raises(ValidationError):
            WeeklyCookingPlan(**_make_weekly_plan(n_days=6))

    def test_plan_rejects_8_days(self) -> None:
        data = _make_weekly_plan()
        data["daily_plans"].append(_make_day(day_label="额外日"))
        with pytest.raises(ValidationError):
            WeeklyCookingPlan(**data)

    def test_shopping_list_default_empty(self) -> None:
        p = WeeklyCookingPlan(**_make_weekly_plan())
        assert p.shopping_list == []

    def test_summary_includes_user_name(self) -> None:
        p = WeeklyCookingPlan(**_make_weekly_plan())
        assert "TestUser" in p.summary()

    def test_created_at_auto_filled(self) -> None:
        p = WeeklyCookingPlan(**_make_weekly_plan())
        assert isinstance(p.created_at, datetime)


# ---------------------------------------------------------------------------
# ShoppingItem
# ---------------------------------------------------------------------------

class TestShoppingItem:
    def test_round_trip(self) -> None:
        item = ShoppingItem(
            food_id="chicken_breast",
            food_name_zh="鸡胸肉",
            total_amount_g=500.0,
            category="poultry",
        )
        data = json.loads(item.model_dump_json())
        restored = ShoppingItem.model_validate(data)
        assert restored.food_id == "chicken_breast"
        assert restored.total_amount_g == 500.0


# ---------------------------------------------------------------------------
# MealPrepSuggestion
# ---------------------------------------------------------------------------

class TestMealPrepSuggestion:
    def test_valid_suggestion(self) -> None:
        s = MealPrepSuggestion(
            recipe_name_zh="批量鸡胸",
            prep_day="周日",
            covers_days=["周一", "周二"],
            storage_zh="冷藏3天",
            reheat_zh="微波2分钟",
        )
        assert s.prep_day == "周日"
