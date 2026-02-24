"""User profile Pydantic model."""
from datetime import datetime
from pydantic import BaseModel, Field
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    ExperienceLevel,
    GoalType,
)


class Gender(str):
    """Gender strings."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(str):
    """Activity level outside of structured training."""
    SEDENTARY = "sedentary"               # 久坐办公
    LIGHTLY_ACTIVE = "lightly_active"     # 日常少量活动
    MODERATELY_ACTIVE = "moderately_active"  # 日常较多走动
    VERY_ACTIVE = "very_active"           # 体力劳动


class UserProfile(BaseModel):
    # --- 基本信息 ---
    name: str
    age: int = Field(ge=14, le=80)
    gender: str = Field(description="male / female / other")
    height_cm: float = Field(ge=120, le=220)
    weight_kg: float = Field(ge=30, le=200)

    # --- 目标 ---
    goal: GoalType
    target_weight_kg: float | None = Field(default=None, description="目标体重，减脂/增肌时填写")

    # --- 训练安排 ---
    experience_level: ExperienceLevel
    training_days_per_week: int = Field(ge=1, le=6)
    session_duration_minutes: int = Field(ge=20, le=180, description="每次训练时长（分钟）")
    available_equipment: list[Equipment] = Field(description="用户可用的器材")

    # --- 健康状况 ---
    injuries: list[ContraindicationTag] = Field(
        default_factory=list,
        description="当前伤病/身体限制"
    )
    activity_level: str = Field(
        default="lightly_active",
        description="日常活动水平（不含计划训练）"
    )

    # --- 饮食 ---
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="饮食限制，如 vegetarian, no_pork, lactose_intolerant"
    )

    # --- 计算字段（收集信息后填入）---
    bmr: float | None = Field(default=None, description="基础代谢率（kcal/day）")
    tdee: float | None = Field(default=None, description="每日总能量消耗（kcal/day）")
    daily_calorie_target: float | None = Field(default=None, description="每日热量目标（kcal）")
    daily_protein_target_g: float | None = Field(default=None, description="每日蛋白质目标（g）")

    # --- 元数据 ---
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
