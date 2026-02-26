"""Knowledge base Pydantic models: Exercise, FoodItem, TrainingRule."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Equipment(str, Enum):
    bodyweight = "bodyweight"           # 徒手/自重
    dumbbell = "dumbbell"               # 哑铃
    barbell = "barbell"                 # 杠铃
    kettlebell = "kettlebell"           # 壶铃
    resistance_band = "resistance_band" # 弹力带
    cable_machine = "cable_machine"     # 绳索/缆绳机
    machine = "machine"                 # 固定器械
    pull_up_bar = "pull_up_bar"         # 单杠/引体向上架
    bench = "bench"                     # 训练凳（通常配合杠铃/哑铃）
    ez_bar = "ez_bar"                   # EZ 弯举杆


class MuscleGroup(str, Enum):
    chest = "chest"               # 胸
    back = "back"                 # 背（泛指）
    lats = "lats"                 # 背阔肌
    traps = "traps"               # 斜方肌
    lower_back = "lower_back"     # 下背/竖脊肌
    shoulders = "shoulders"       # 肩（泛指）
    front_delt = "front_delt"     # 前三角
    side_delt = "side_delt"       # 中三角
    rear_delt = "rear_delt"       # 后三角
    biceps = "biceps"             # 二头肌
    triceps = "triceps"           # 三头肌
    forearms = "forearms"         # 前臂
    core = "core"                 # 核心（泛指）
    abs = "abs"                   # 腹直肌
    obliques = "obliques"         # 腹斜肌
    quads = "quads"               # 股四头肌
    hamstrings = "hamstrings"     # 腘绳肌
    glutes = "glutes"             # 臀肌
    calves = "calves"             # 小腿
    hip_flexors = "hip_flexors"   # 髋屈肌
    adductors = "adductors"       # 内收肌
    full_body = "full_body"       # 全身


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ExerciseCategory(str, Enum):
    strength = "strength"         # 力量训练
    cardio = "cardio"             # 有氧
    flexibility = "flexibility"   # 柔韧/拉伸
    plyometric = "plyometric"     # 爆发力


class MovementPattern(str, Enum):
    push = "push"           # 推（水平/垂直）
    pull = "pull"           # 拉（水平/垂直）
    squat = "squat"         # 蹲
    hinge = "hinge"         # 髋铰（硬拉系列）
    carry = "carry"         # 负重行走
    core = "core"           # 核心稳定/抗旋
    cardio = "cardio"       # 有氧
    isolation = "isolation" # 孤立动作


class ContraindicationTag(str, Enum):
    knee_injury = "knee_injury"           # 膝关节损伤
    lower_back_pain = "lower_back_pain"   # 腰痛/下背痛
    shoulder_injury = "shoulder_injury"   # 肩关节损伤
    wrist_injury = "wrist_injury"         # 手腕损伤
    neck_pain = "neck_pain"               # 颈部疼痛
    hip_injury = "hip_injury"             # 髋关节损伤
    ankle_injury = "ankle_injury"         # 踝关节损伤
    herniated_disc = "herniated_disc"     # 椎间盘突出
    hypertension = "hypertension"         # 高血压（屏气动作）
    elbow_injury = "elbow_injury"         # 肘关节损伤


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------

class Exercise(BaseModel):
    id: str = Field(description="唯一 ID，snake_case，如 barbell_squat")
    name: str = Field(description="英文名称")
    name_zh: str = Field(description="中文名称")
    category: ExerciseCategory
    equipment: list[Equipment] = Field(description="所需器材（可多选，表示该动作的常见器材变体）")
    primary_muscles: list[MuscleGroup] = Field(description="主要目标肌群")
    secondary_muscles: list[MuscleGroup] = Field(default_factory=list, description="协同肌群")
    difficulty: Difficulty
    movement_pattern: MovementPattern
    contraindications: list[ContraindicationTag] = Field(
        default_factory=list, description="禁忌标签，带有这些标签的用户应排除此动作"
    )
    cues: list[str] = Field(default_factory=list, description="动作要领（中文）")
    met_value: float | None = Field(default=None, description="代谢当量，有氧动作用于热量估算")

    # --- Extended fields for GYMAgent (optional, populated for core exercises) ---
    detailed_technique_zh: str | None = Field(
        default=None,
        description="3-5 句详细技术说明，GYMAgent 优先使用此字段而非 LLM 生成",
    )
    common_mistakes_zh: list[str] = Field(
        default_factory=list,
        description="常见动作错误（中文），GYMAgent 优先使用此字段",
    )
    breathing_pattern_zh: str | None = Field(
        default=None,
        description="呼吸模式描述，如 '下降时吸气，推起时呼气'",
    )
    video_url: str | None = Field(
        default=None,
        description="教学视频链接（Bilibili / YouTube）",
    )


# ---------------------------------------------------------------------------
# FoodItem
# ---------------------------------------------------------------------------

class FoodCategory(str, Enum):
    grain = "grain"           # 主食/谷物
    meat = "meat"             # 畜肉
    poultry = "poultry"       # 禽肉
    seafood = "seafood"       # 海鲜
    egg_dairy = "egg_dairy"   # 蛋奶
    vegetable = "vegetable"   # 蔬菜
    fruit = "fruit"           # 水果
    nut_seed = "nut_seed"     # 坚果种子
    legume = "legume"         # 豆类
    oil_fat = "oil_fat"       # 油脂
    condiment = "condiment"   # 调味品
    supplement = "supplement" # 营养补剂/运动食品


class FoodItem(BaseModel):
    id: str
    name: str = Field(description="英文名称")
    name_zh: str = Field(description="中文名称")
    category: FoodCategory
    serving_size_g: float = Field(description="每份克数（100g 为标准）")
    calories: float = Field(description="热量（kcal）")
    protein_g: float = Field(description="蛋白质（g）")
    carbs_g: float = Field(description="碳水化合物（g）")
    fat_g: float = Field(description="脂肪（g）")
    fiber_g: float = Field(default=0.0, description="膳食纤维（g）")
    dietary_tags: list[str] = Field(
        default_factory=list,
        description="饮食属性标签，如 ['meat', 'poultry'] 或 ['plant', 'vegan']",
    )


# ---------------------------------------------------------------------------
# MuscleGroupInfo  (anatomy knowledge)
# ---------------------------------------------------------------------------

class MuscleGroupInfo(BaseModel):
    id: str = Field(description="肌群 ID，与 MuscleGroup 枚举值对应")
    name: str = Field(description="英文名称")
    name_zh: str = Field(description="中文名称")
    is_large_muscle: bool = Field(description="是否大肌群（大肌群恢复更慢，容量更高）")
    recovery_hours_min: int = Field(description="最少恢复小时数")
    recovery_hours_max: int = Field(description="最多恢复小时数")
    primary_movement_patterns: list[str] = Field(description="主要动作模式")
    antagonist_groups: list[str] = Field(default_factory=list, description="拮抗肌群")
    weekly_volume_beginner_min: int = Field(description="新手每周最少训练组数")
    weekly_volume_beginner_max: int = Field(description="新手每周最多训练组数")
    weekly_volume_intermediate_min: int = Field(description="中级每周最少训练组数")
    weekly_volume_intermediate_max: int = Field(description="中级每周最多训练组数")
    weekly_volume_advanced_min: int = Field(description="高级每周最少训练组数")
    weekly_volume_advanced_max: int = Field(description="高级每周最多训练组数")
    scheduling_notes: str = Field(default="", description="排课注意事项")


# ---------------------------------------------------------------------------
# NutritionPrinciples  (meal timing + dietary substitutions)
# ---------------------------------------------------------------------------

class MealTimingEntry(BaseModel):
    window_minutes: int
    focus: str
    rationale: str = ""
    examples: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class TrainingRestDayNutrition(BaseModel):
    carb_adjustment: str
    protein_adjustment: str
    fat_adjustment: str
    note: str


class DietarySubstitution(BaseModel):
    restriction: str = Field(description="饮食限制 ID（英文小写）")
    restriction_zh: str = Field(description="中文标签")
    avoid: list[str] = Field(default_factory=list)
    protein_alternatives: list[str] = Field(default_factory=list)
    calcium_alternatives: list[str] = Field(default_factory=list)
    dairy_alternatives: list[str] = Field(default_factory=list)
    carb_alternatives: list[str] = Field(default_factory=list)
    must_supplement: list[str] = Field(default_factory=list)
    notes: str = ""
    banned_food_tags: list[str] = Field(
        default_factory=list,
        description="该饮食限制禁止使用的食材标签列表",
    )


class SupplementInfo(BaseModel):
    id: str
    name: str
    name_zh: str
    evidence_level: str
    benefit: str
    dosage: str
    timing: str
    suitable_for: list[str] = Field(default_factory=list)
    notes: str = ""


class NutritionPrinciples(BaseModel):
    meal_timing: dict[str, MealTimingEntry] = Field(default_factory=dict)
    training_vs_rest_day: dict[str, TrainingRestDayNutrition] = Field(default_factory=dict)
    hydration: dict[str, Any] = Field(default_factory=dict)
    dietary_substitutions: list[DietarySubstitution] = Field(default_factory=list)
    supplements: list[SupplementInfo] = Field(default_factory=list)

    def get_substitution(self, restriction: str) -> "DietarySubstitution | None":
        """Find substitution rules for a given dietary restriction (case-insensitive)."""
        r = restriction.lower()
        for sub in self.dietary_substitutions:
            if r in sub.restriction.lower() or r in sub.restriction_zh:
                return sub
        return None


# ---------------------------------------------------------------------------
# TrainingRule
# ---------------------------------------------------------------------------

class RuleCategory(str, Enum):
    volume = "volume"           # 训练容量
    frequency = "frequency"     # 训练频率
    intensity = "intensity"     # 训练强度
    nutrition = "nutrition"     # 营养规则
    progression = "progression" # 渐进超负荷
    safety = "safety"           # 安全限制
    recovery = "recovery"       # 恢复规则
    structure = "structure"     # 计划结构（分化方式等）


class GoalType(str, Enum):
    muscle_gain = "muscle_gain"                   # 增肌
    fat_loss = "fat_loss"                         # 减脂
    body_recomposition = "body_recomposition"     # 体态改善
    general_fitness = "general_fitness"           # 通用健身


class ExperienceLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class RuleType(str, Enum):
    constraint = "constraint"           # 硬约束（必须遵守）
    recommendation = "recommendation"   # 软建议（尽量遵守）


class TrainingRule(BaseModel):
    id: str
    category: RuleCategory
    applies_to_goals: list[GoalType] = Field(
        default_factory=list,
        description="适用的目标类型，空列表表示适用所有目标"
    )
    applies_to_levels: list[ExperienceLevel] = Field(
        default_factory=list,
        description="适用的训练水平，空列表表示适用所有水平"
    )
    rule_type: RuleType
    description: str = Field(description="规则的自然语言描述（中文），直接注入 LLM prompt")
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="数值参数，用于确定性计算"
    )


# ---------------------------------------------------------------------------
# WarmupTemplate  (热身/拉伸模板库)
# ---------------------------------------------------------------------------

class WarmupTemplate(BaseModel):
    """Warmup and cooldown template for a specific training day type."""
    id: str = Field(description="模板唯一 ID，如 lower_body / upper_push")
    name_zh: str = Field(description="模板中文名称")
    applicable_movement_patterns: list[str] = Field(
        description="适用的动作模式列表（与 MovementPattern 枚举值对应）"
    )
    warmup_sequence: list[str] = Field(
        description="热身步骤，使用 ①②③ 格式的中文字符串列表"
    )
    cooldown_sequence: list[str] = Field(
        description="放松拉伸步骤，使用 ①②③ 格式的中文字符串列表"
    )
    injury_modifications: dict[str, str] = Field(
        default_factory=dict,
        description="伤病调整说明，键为 ContraindicationTag 值，值为对应的热身调整说明"
    )


# ---------------------------------------------------------------------------
# InjuryProfile  (伤病修改指导)
# ---------------------------------------------------------------------------

class InjuryProfile(BaseModel):
    """Deterministic training guidance for a specific injury/contraindication."""
    tag: ContraindicationTag = Field(description="对应的伤病标签")
    name_zh: str = Field(description="伤病中文名称")
    avoid_movement_patterns: list[str] = Field(
        description="应完全避免的动作模式列表"
    )
    modify_movement_patterns: dict[str, str] = Field(
        description="需要修改的动作模式，键为动作模式，值为修改说明"
    )
    warmup_focus_zh: str = Field(description="热身阶段的重点说明")
    general_guidance_zh: str = Field(description="整体训练注意事项（1-2 句）")
    warmup_routine: list[str] = Field(
        default_factory=list,
        description="伤病专项热身动作列表（具体动作+次数/时长），注入到每天热身最前面",
    )


# ---------------------------------------------------------------------------
# RecipeTemplate  (食谱模板库)
# ---------------------------------------------------------------------------

class RecipeIngredientTemplate(BaseModel):
    """A single ingredient entry in a recipe template."""
    food_id: str = Field(description="引用 nutrition.json 中的 FoodItem.id")
    amount_g: float = Field(ge=0, description="食材用量（克）")
    note: str = Field(default="", description="备注，如'切丁'、'2个全蛋'")


class SubstitutionEntry(BaseModel):
    """How to replace a specific ingredient for a dietary restriction."""
    replacement_id: str = Field(description="替换食材的 food_id")
    amount_g: float = Field(ge=0, description="替换食材用量（克）")
    note: str = Field(default="", description="替换说明")


class RecipeTemplate(BaseModel):
    """A recipe template in the knowledge base."""
    id: str = Field(description="唯一 ID，snake_case")
    name: str = Field(description="英文名称")
    name_zh: str = Field(description="中文名称")
    meal_type: str = Field(description="餐食类型: breakfast|lunch|dinner|snack|pre_workout|post_workout")
    tags: list[str] = Field(default_factory=list, description="筛选标签，如 high_protein, quick, batch_friendly")
    dietary_flags: list[str] = Field(
        default_factory=list,
        description="该食谱原生满足的饮食限制，如 vegetarian, vegan, gluten_free"
    )
    prep_time_minutes: int = Field(default=0, ge=0, description="准备时间（分钟）")
    cook_time_minutes: int = Field(default=0, ge=0, description="烹饪时间（分钟）")
    servings: int = Field(default=1, ge=1, description="份数")
    batch_friendly: bool = Field(default=False, description="是否适合批量备餐")
    ingredients: list[RecipeIngredientTemplate] = Field(min_length=1, description="食材列表")
    steps_zh: list[str] = Field(min_length=1, description="中文烹饪步骤")
    per_serving_macros: dict[str, float] = Field(
        default_factory=dict,
        description="每份预计算营养数据: calories, protein_g, carbs_g, fat_g"
    )
    substitution_groups: dict[str, dict[str, SubstitutionEntry | None]] = Field(
        default_factory=dict,
        description="按饮食限制的食材替换方案，键为限制ID，值为{food_id: SubstitutionEntry}"
    )
    scaling_notes: str = Field(default="", description="份量调整说明")
