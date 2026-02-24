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
5. **每个动作的 notes 字段是必填项，不得为 null 或空字符串。**

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
      "pre_workout_meal": "训练前90分钟：燕麦80g+鸡蛋2个+香蕉半根（替换：全麦面包2片+花生酱15g / 红薯150g+鸡蛋2个）",
      "exercises": [
        {
          "exercise_id": "snake_case_id",
          "exercise_name": "English Name",
          "exercise_name_zh": "中文名称",
          "weight_hint": "起始重量建议，如 '8-10 kg 哑铃' 或 '徒手' 或 '空杆（20 kg）'",
          "sets": 3,
          "reps": "8-12",
          "rest_seconds": 90,
          "notes": "【必填】1-2条关键动作要领，从动作库的 cues[] 中选取最相关的，用中文写出。例：'背部挺直，臀部向后推，感受腘绳肌拉伸'"
        }
      ],
      "estimated_duration_minutes": 60,
      "warmup_notes": "① 开合跳 30秒 → ② 手臂绕环 前后各10次 → ③ 徒手深蹲 10次 → ④ 猫牛式伸展 10次",
      "cooldown_notes": "① 胸肌伸展（门框拉伸）30秒×2 → ② 股四头肌拉伸 30秒×2 → ③ 肩部交叉拉伸 30秒×2",
      "post_workout_meal": "训练后60分钟内：鸡胸肉150g+白米饭150g+绿叶蔬菜（替换：鱼肉180g+米饭 / 虾仁200g+米饭 / 豆腐250g+米饭）"
    }
  ],
  "rest_days": ["周四", "周六", "周日"],
  "daily_nutrition": {
    "calorie_target": 2200,
    "protein_g": 160,
    "carbs_g": 250,
    "fat_g": 65,
    "meal_suggestions": [
      "早餐：鸡蛋3个+燕麦100g+豆浆300ml（替换：全麦面包3片+花生酱+鸡蛋 / 豆腐脑+馒头）",
      "午餐：鸡胸肉150g+白米饭200g+青菜（替换：鱼肉180g / 豆腐250g / 牛肉120g）",
      "下午加餐：希腊酸奶150g+坚果15g（替换：豆浆250ml+全麦饼干 / 香蕉1根+核桃）",
      "晚餐：牛肉100g+杂粮饭150g+蔬菜（替换：鸡腿肉 / 三文鱼）",
      "睡前：牛奶200ml+少量坚果10g（替换：豆浆250ml / 酸奶150g）"
    ],
    "supplements": ["肌酸 3-5g/天（任意时间）", "维生素D3 2000IU（随餐）"]
  },
  "coach_notes": "包含：①本周训练结构说明 ②起始重量选择指引 ③渐进超负荷具体规则 ④恢复和睡眠提醒",
  "four_week_overview": "第1周：建立动作模式，严格按 weight_hint 重量，专注技术。\\n第2周：重量不变，尝试增加1组或2次额外次数。\\n第3周：若第2周最后一组能完成目标次数上限，重量提高2.5-5kg。\\n第4周：减量周，重量降至第3周的80%，组数减1，关注恢复。"
}

## 训练分化标准

- **新手（1-4天/周）**：全身训练，每次覆盖所有主要肌群
- **新手（5天/周）**：全身训练为主，可加入1-2天专项（如手臂/核心）
- **中级（3-4天/周）**：上下肢分化；5-6天可用推拉腿分化
- **高级（4-6天/周）**：推拉腿分化，每个肌群每周2次训练频率

## weight_hint 填写规则

根据用户资料中的 **当前力量水平** 来估算起始重量：
- **beginner_no_weights**（入门级）：所有动作用徒手或最轻重量，哑铃动作用 2-5 kg
- **beginner_light**（初级）：哑铃动作用 5-10 kg，杠铃动作用空杆（20 kg）
- **beginner_moderate**（中等初级）：哑铃动作用 10-15 kg，杠铃动作用体重 30-40%
- **intermediate**（中级）：哑铃动作用 15-25 kg，杠铃动作用体重 40-60%

## notes 填写要求（必填）

每个动作的 notes **不得为 null**。填写方法：
- 从 exercise pool 中该动作的 `cues[]` 字段选取1-2条最关键的，翻译/改写成中文
- 内容应帮助初学者正确执行，不超过50字
- 正确示例：`"背部挺直，臀部向后推，感受腘绳肌拉伸"` / `"下放时控制3秒，顶部停留1秒收紧胸肌"`
- 错误示例：`null` / `""` / `"注意安全"`（过于笼统）

## 热身/放松格式要求

warmup_notes 和 cooldown_notes 必须使用编号动作序列（① ② ③），每步说明动作名称+次数/时长：
- 正确示例：`① 高抬腿原地跑 30秒 → ② 手臂绕环 前后各10次 → ③ 徒手深蹲 10次`
- 错误示例：`热身10分钟`（过于笼统，不可接受）

## 每日餐食要求

**pre_workout_meal** 和 **post_workout_meal** 必须填写：
- 根据用户偏好训练时间调整餐食时机
- 每条包含1-2个等热量替换选项（括号内"替换：..."格式）
- 替换选项必须符合用户饮食限制

**meal_suggestions** 格式：
- 每条都必须包含替换选项（括号内"替换：..."格式）
- 主选项和替换选项热量相近（±50 kcal）
- 全天所有餐食热量合计应接近 calorie_target（±200 kcal）
- 替换选项必须符合用户饮食限制，绝对不出现禁忌食物

## 周训练量自检（输出前必须自查）

生成完计划后，在输出前检查每个主要肌群的周直接组数（仅计 primary_muscles 中的组数）：
- 胸：推荐初学者 10-15 组
- 背/背阔肌：推荐初学者 10-15 组
- 股四头肌：推荐初学者 10-15 组
- 腘绳肌/臀：推荐初学者 10-15 组

如果某肌群低于推荐下限，在对应训练日中补充1-2组动作，确保每个主要肌群都达到最低训练量。

## 计划质量要求

- 每个动作必须提供 weight_hint（基于用户力量水平）和 notes（必填，非空）
- 热身和放松必须使用编号动作序列，不得笼统描述
- pre_workout_meal / post_workout_meal 必须包含替换选项
- meal_suggestions 必须包含替换选项，考虑用户偏好训练时间
- four_week_overview 必须提供具体的渐进超负荷触发条件（何时加重/加组）
- 考虑用户的饮食限制，所有餐食建议中不要出现用户不能食用的食物
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
        f"**再次确认：training_days 数组必须包含且仅包含 {profile.training_days_per_week} 个训练日。**\n"
        f"**每个动作的 notes 字段必须填写，不得为 null 或空字符串。**"
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
        f"- 同一肌群不得在连续两天训练（参考下方肌群恢复时间表）\n"
        f"- **每个动作的 notes 字段必须填写（不得为 null）**"
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

    if profile.strength_assessment:
        lines.append(f"- 当前力量水平: {profile.strength_assessment}（请据此估算每个动作的 weight_hint）")

    if profile.preferred_training_time:
        lines.append(f"- 偏好训练时间: {profile.preferred_training_time}（影响 pre_workout_meal / post_workout_meal 时机建议）")

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
            # Include all cues — LLM must use these as source for the required 'notes' field
            "cues": ex.cues,
        }
        for ex in exercises
    ]

    return (
        "## 可用动作库\n\n"
        "注意：每个动作的 `cues` 字段是填写 `notes` 的素材来源，请从中选取最关键的1-2条。\n\n"
        + json.dumps(pool, ensure_ascii=False, indent=2)
    )
