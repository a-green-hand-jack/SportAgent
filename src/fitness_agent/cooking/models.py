"""
Output data models for the CookingAgent.

These are the structured results produced by CookingAgent.
All fields are Pydantic v2 BaseModel so the cooking plan can be
serialised to JSON, stored, and loaded back.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Macronutrient breakdown (reused across recipe / day / plan levels)
# ---------------------------------------------------------------------------

class MacroBreakdown(BaseModel):
    """Macronutrient breakdown."""

    calories: float = Field(ge=0, description="热量（kcal）")
    protein_g: float = Field(ge=0, description="蛋白质（g）")
    carbs_g: float = Field(ge=0, description="碳水化合物（g）")
    fat_g: float = Field(ge=0, description="脂肪（g）")


# ---------------------------------------------------------------------------
# Recipe-level models
# ---------------------------------------------------------------------------

class RecipeIngredient(BaseModel):
    """A single ingredient in a generated recipe."""

    food_id: str = Field(description="食材 ID，引用 nutrition.json")
    food_name_zh: str = Field(description="食材中文名")
    amount_g: float = Field(ge=0, description="用量（克）")
    note: Optional[str] = Field(default=None, description="备注，如'切丁'、'去皮'")


class Recipe(BaseModel):
    """A concrete recipe with cooking steps and macros."""

    recipe_id: str = Field(description="引用 recipes.json ID 或 LLM 自创的 ID")
    name_zh: str = Field(description="菜品中文名")
    meal_type: str = Field(
        description="餐食类型: breakfast|lunch|dinner|snack|pre_workout|post_workout",
    )
    prep_time_minutes: int = Field(ge=0, description="准备时间（分钟）")
    cook_time_minutes: int = Field(ge=0, description="烹饪时间（分钟）")
    ingredients: list[RecipeIngredient] = Field(min_length=1, description="食材列表")
    steps_zh: list[str] = Field(min_length=1, description="中文烹饪步骤")
    per_serving_macros: MacroBreakdown = Field(description="每份营养数据")
    substitution_notes: list[str] = Field(
        default_factory=list,
        description="替代方案说明，如'乳糖不耐受：用豆浆替代牛奶'",
    )
    scaling_notes: Optional[str] = Field(
        default=None,
        description="份量调整说明",
    )


# ---------------------------------------------------------------------------
# Day-level plan
# ---------------------------------------------------------------------------

class DayMealPlan(BaseModel):
    """All meals for one day."""

    day_label: str = Field(description="日期标签，如'周一'、'训练日1'、'休息日1'")
    is_training_day: bool = Field(description="是否为训练日")
    meals: list[Recipe] = Field(min_length=3, description="当天所有餐食（≥3 餐）")
    day_total_macros: MacroBreakdown = Field(description="当天总营养数据")
    calorie_deviation_pct: float = Field(
        default=0.0,
        description="(实际热量 - 目标热量) / 目标热量 × 100",
    )


# ---------------------------------------------------------------------------
# Shopping list
# ---------------------------------------------------------------------------

class ShoppingItem(BaseModel):
    """Aggregated ingredient for the weekly shopping list."""

    food_id: str = Field(description="食材 ID")
    food_name_zh: str = Field(description="食材中文名")
    total_amount_g: float = Field(ge=0, description="一周总用量（克）")
    category: str = Field(description="食材分类，对应 nutrition.json 的 category")


# ---------------------------------------------------------------------------
# Meal prep suggestions
# ---------------------------------------------------------------------------

class MealPrepSuggestion(BaseModel):
    """A batch cooking suggestion for meal prepping."""

    recipe_name_zh: str = Field(description="菜品中文名")
    prep_day: str = Field(description="建议备餐日，如'周日'")
    covers_days: list[str] = Field(description="可覆盖的天数，如['周一', '周二', '周三']")
    storage_zh: str = Field(description="储存方式说明")
    reheat_zh: str = Field(description="加热方式说明")


# ---------------------------------------------------------------------------
# Top-level weekly cooking plan
# ---------------------------------------------------------------------------

class WeeklyCookingPlan(BaseModel):
    """
    Full weekly cooking plan — the CookingAgent's primary output.

    Contains 7 daily meal plans, an aggregated shopping list,
    meal prep suggestions, and general cooking tips.
    """

    user_name: str = Field(description="用户姓名")
    daily_plans: list[DayMealPlan] = Field(
        min_length=7,
        max_length=7,
        description="7 天的每日餐食计划",
    )
    shopping_list: list[ShoppingItem] = Field(
        default_factory=list,
        description="一周采购清单（确定性聚合）",
    )
    meal_prep_suggestions: list[MealPrepSuggestion] = Field(
        default_factory=list,
        description="备餐建议",
    )
    cooking_tips_zh: str = Field(
        default="",
        description="通用烹饪提示和注意事项",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="生成时间戳",
    )

    def summary(self) -> str:
        """Return a short human-readable summary string."""
        compliant = sum(
            1 for d in self.daily_plans if abs(d.calorie_deviation_pct) <= 10.0
        )
        return (
            f"{self.user_name} | 7-day cooking plan | "
            f"{compliant}/7 days within ±10% calorie target | "
            f"{len(self.shopping_list)} shopping items"
        )
