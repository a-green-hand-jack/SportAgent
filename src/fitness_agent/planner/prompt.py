"""
Prompt builder for PlannerAgent.

Constructs the structured prompt that is injected into the LLM to generate
a personalised WeeklyPlan.  The LLM receives:
  1. A system prompt explaining its role and the JSON output format.
  2. A user message containing:
     - ⚠️ Hard constraint block (training days count — must come first)
     - Enriched user profile summary (deterministic numbers from calculator.py)
     - Applicable training rules (from knowledge base)
     - Anatomy knowledge (muscle recovery + volume guidelines)
     - Nutrition execution guide (meal timing + dietary substitutions)
     - Progressive overload protocol (starting weight + trigger rules)
     - Week schedule template (concrete day assignment)
     - Available exercise pool (already filtered for safety + equipment)
"""
from __future__ import annotations

import json

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import Exercise, ExperienceLevel
from fitness_agent.user.models import UserProfile

# ---------------------------------------------------------------------------
# System prompt (role + output schema)
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """\
你是一位资深力量与体能教练，专注于循证训练方法。你将根据用户信息生成一份完整、可直接执行的周训练计划。

## ⚠️ 最高优先级约束（不可违反）

1. **training_days 数组长度必须精确等于用户指定的每周训练天数** — 这是硬性约束，不得以任何理由减少或增加。
2. 同一主要肌群（胸/背/腿/肩）不得在连续两天内训练。
3. 每个 exercise_id 必须来自提供的动作库，exercise_name/exercise_name_zh 必须与动作库完全一致。
4. 热量、蛋白质数值直接使用用户资料中提供的计算值，不要重新计算。

## 输出格式

严格输出纯 JSON 对象，不含任何 markdown 代码块、注释或额外文字：

{
  "user_name": "用户姓名",
  "goal": "fat_loss|muscle_gain|body_recomposition|general_fitness",
  "experience_level": "beginner|intermediate|advanced",
  "training_days": [
    {
      "day_label": "周一 (Day 1)",
      "focus": "训练重点，如：上肢推（胸/肩/三头）",
      "exercises": [
        {
          "exercise_id": "snake_case_id",
          "exercise_name": "English Name",
          "exercise_name_zh": "中文名称",
          "sets": 3,
          "reps": "8-12",
          "rest_seconds": 90,
          "notes": "1-2条关键动作要领，帮助用户执行正确动作"
        }
      ],
      "estimated_duration_minutes": 60,
      "warmup_notes": "具体热身动作（5-10分钟），例如：开合跳30次、手臂绕环20次、深蹲热身10次",
      "cooldown_notes": "具体拉伸动作（5分钟），例如：胸肌拉伸30秒、股四头肌拉伸30秒"
    }
  ],
  "rest_days": ["周四", "周六", "周日"],
  "daily_nutrition": {
    "calorie_target": 2200,
    "protein_g": 160,
    "carbs_g": 250,
    "fat_g": 65,
    "meal_suggestions": [
      "训练前（训练前90分钟）：燕麦100g+鸡蛋清3个+香蕉1根",
      "训练后（训练后60分钟内）：鸡胸肉150g+白米饭200g",
      "早餐：...",
      "午餐：...",
      "晚餐：...",
      "睡前：牛奶200ml+少量坚果10g"
    ],
    "supplements": ["肌酸 3-5g/天（任意时间）", "维生素D3 2000IU（随餐）"]
  },
  "coach_notes": "包含：①本周训练结构说明 ②起始重量选择指引 ③渐进超负荷具体规则 ④恢复和睡眠提醒"
}

## 训练分化标准

- **新手（1-4天/周）**：全身训练，每次覆盖所有主要肌群
- **新手（5天/周）**：全身训练为主，可加入1-2天专项（如手臂/核心）
- **中级（3-4天/周）**：上下肢分化；5-6天可用推拉腿分化
- **高级（4-6天/周）**：推拉腿分化，每个肌群每周2次训练频率

## 计划质量要求

- 每个动作必须提供 notes（1-2条要领），帮助新手和中级者正确执行
- 热身和放松必须具体（说明动作，不能只说"热身10分钟"）
- meal_suggestions 必须包含训练前后的餐食时机建议
- coach_notes 必须包含起始重量指引和渐进超负荷的具体触发条件
- 考虑用户的饮食限制，meal_suggestions 中不要出现用户不能食用的食物
"""

# ---------------------------------------------------------------------------
# Week schedule helper
# ---------------------------------------------------------------------------

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _build_week_schedule(training_days: int) -> tuple[list[str], list[str]]:
    """
    Return (training_day_labels, rest_day_labels) for a given number of training days.

    Distributes training days to avoid 3+ consecutive training days where possible.
    """
    if training_days <= 0 or training_days > 7:
        training_days = min(max(training_days, 1), 7)

    # Distribute training days across the week
    if training_days == 1:
        train_indices = [0]
    elif training_days == 2:
        train_indices = [0, 3]           # Mon, Thu
    elif training_days == 3:
        train_indices = [0, 2, 4]        # Mon, Wed, Fri
    elif training_days == 4:
        train_indices = [0, 1, 3, 4]     # Mon, Tue, Thu, Fri
    elif training_days == 5:
        train_indices = [0, 1, 2, 3, 4]  # Mon-Fri
    elif training_days == 6:
        train_indices = [0, 1, 2, 3, 4, 5]  # Mon-Sat
    else:
        train_indices = list(range(7))   # all days

    training_labels = [_WEEKDAYS[i] for i in train_indices]
    rest_labels = [_WEEKDAYS[i] for i in range(7) if i not in train_indices]
    return training_labels, rest_labels


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------

def build_user_message(
    profile: UserProfile,
    kb: KnowledgeBase,
    exercise_pool: list[Exercise],
) -> str:
    """
    Build the user-turn message containing all context the LLM needs.

    Parameters
    ----------
    profile:
        Fully-enriched UserProfile (bmr/tdee/calorie_target already filled).
    kb:
        Knowledge base instance (used to pull rules, anatomy, nutrition principles).
    exercise_pool:
        Pre-filtered list of exercises (safe + equipment-compatible).
    """
    training_labels, rest_labels = _build_week_schedule(profile.training_days_per_week)

    sections: list[str] = []

    # 0. Hard constraint block — always first, impossible to miss
    sections.append(_format_hard_constraints(profile, training_labels, rest_labels))

    # 1. User profile summary
    sections.append(_format_profile(profile, training_labels, rest_labels))

    # 2. Applicable training rules
    rules_text = kb.format_rules_for_prompt(
        goal=profile.goal,
        level=profile.experience_level,
    )
    if rules_text:
        sections.append(f"## 训练规则\n\n{rules_text}")

    # 3. Anatomy knowledge (muscle recovery + volume)
    anatomy_text = kb.format_anatomy_for_prompt(level=profile.experience_level)
    if anatomy_text:
        sections.append(anatomy_text)

    # 4. Nutrition execution guide
    nutrition_text = kb.format_nutrition_principles_for_prompt(
        dietary_restrictions=profile.dietary_restrictions,
        goal=profile.goal,
    )
    if nutrition_text:
        sections.append(nutrition_text)

    # 5. Exercise pool (condensed JSON array)
    sections.append(_format_exercise_pool(exercise_pool))

    # 6. Final instruction with re-emphasis on training days
    sections.append(
        f"请根据以上信息，生成完整的 JSON 格式周训练计划。\n"
        f"**再次确认：training_days 数组必须包含且仅包含 {profile.training_days_per_week} 个训练日。**"
    )

    return "\n\n".join(sections)


def _format_hard_constraints(
    profile: UserProfile,
    training_labels: list[str],
    rest_labels: list[str],
) -> str:
    """The very first block — hard constraints in bold."""
    n = profile.training_days_per_week
    train_str = "、".join(training_labels)
    rest_str = "、".join(rest_labels) if rest_labels else "无"

    return (
        f"## ⚠️ 本次任务关键约束（必须严格遵守）\n\n"
        f"- **训练日数量：必须生成 {n} 个训练日（training_days 数组长度 = {n}）**\n"
        f"- 推荐周历：训练日 = {train_str}，休息日 = {rest_str}\n"
        f"- day_label 格式示例：「{training_labels[0]} (Day 1)」\n"
        f"- 同一肌群不得在连续两天训练（参考下方肌群恢复时间表）"
    )


def _format_profile(
    profile: UserProfile,
    training_labels: list[str],
    rest_labels: list[str],
) -> str:
    """Format the user profile as a readable Markdown section."""
    lines = [
        "## 用户信息",
        "",
        f"- 姓名: {profile.name}",
        f"- 年龄: {profile.age} 岁",
        f"- 性别: {profile.gender}",
        f"- 身高: {profile.height_cm} cm / 体重: {profile.weight_kg} kg",
        f"- 训练目标: {profile.goal.value}",
        f"- 经验水平: {profile.experience_level.value}",
        f"- **每周训练天数: {profile.training_days_per_week}（必须生成恰好 {profile.training_days_per_week} 个训练日）**",
        f"- 每次训练时长: {profile.session_duration_minutes} 分钟",
        f"- 可用器材: {', '.join(e.value for e in profile.available_equipment)}",
    ]

    if profile.injuries:
        lines.append(f"- ⚠️ 受伤/禁忌: {', '.join(profile.injuries)}（已在动作库中过滤，但热身和动作 notes 需特别注意）")

    if profile.dietary_restrictions:
        lines.append(f"- 饮食限制: {', '.join(profile.dietary_restrictions)}（meal_suggestions 中绝对不要出现禁忌食物）")

    if profile.target_weight_kg:
        lines.append(f"- 目标体重: {profile.target_weight_kg} kg")

    lines += [
        "",
        "### 计算所得营养目标（直接使用这些数值，不要重算）",
        f"- BMR: {profile.bmr:.0f} kcal/day" if profile.bmr else "- BMR: 未计算",
        f"- TDEE: {profile.tdee:.0f} kcal/day" if profile.tdee else "- TDEE: 未计算",
        (
            f"- **每日热量目标: {profile.daily_calorie_target:.0f} kcal**"
            if profile.daily_calorie_target
            else "- 每日热量目标: 未计算"
        ),
        (
            f"- **每日蛋白质目标: {profile.daily_protein_target_g:.0f} g**"
            if profile.daily_protein_target_g
            else "- 每日蛋白质目标: 未计算"
        ),
        "",
        "### 本周训练安排",
        f"- 训练日（{profile.training_days_per_week} 天）：{', '.join(training_labels)}",
        f"- 休息日（{7 - profile.training_days_per_week} 天）：{', '.join(rest_labels) if rest_labels else '无'}",
    ]

    return "\n".join(lines)


def _format_exercise_pool(exercises: list[Exercise]) -> str:
    """Format the exercise pool as a compact JSON array for LLM consumption."""
    pool = [
        {
            "id": ex.id,
            "name": ex.name,
            "name_zh": ex.name_zh,
            "category": ex.category.value,
            "equipment": [e.value for e in ex.equipment],
            "primary_muscles": [m.value for m in ex.primary_muscles],
            "secondary_muscles": [m.value for m in ex.secondary_muscles],
            "difficulty": ex.difficulty.value,
            "movement_pattern": ex.movement_pattern.value,
            "cues": ex.cues[:2] if ex.cues else [],  # send up to 2 cues for LLM reference
        }
        for ex in exercises
    ]

    return (
        "## 可用动作库\n\n"
        + json.dumps(pool, ensure_ascii=False, indent=2)
    )
