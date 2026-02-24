"""
Prompt builder for PlannerAgent.

Constructs the structured prompt that is injected into the LLM to generate
a personalised WeeklyPlan.  The LLM receives:
  1. A system prompt explaining its role and the JSON output format.
  2. A user message containing:
     - Enriched user profile summary (deterministic numbers from calculator.py)
     - Applicable training rules (from knowledge base)
     - Available exercise pool (already filtered for safety + equipment)
"""
from __future__ import annotations

import json

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import Exercise
from fitness_agent.user.models import UserProfile

# ---------------------------------------------------------------------------
# System prompt (role + output schema)
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """\
你是一位经验丰富的力量与体能教练，擅长根据用户的个人情况制定个性化的训练计划。

你的任务是根据用户信息、训练规则和可用动作库，生成一份完整的周训练计划。

## 输出格式

你必须严格输出一个 JSON 对象，符合以下结构（不要输出任何额外文字、markdown 代码块、注释）：

{
  "user_name": "用户姓名",
  "goal": "fat_loss|muscle_gain|body_recomposition|general_fitness",
  "experience_level": "beginner|intermediate|advanced",
  "training_days": [
    {
      "day_label": "Day 1",
      "focus": "训练重点描述",
      "exercises": [
        {
          "exercise_id": "snake_case_id",
          "exercise_name": "English Name",
          "exercise_name_zh": "中文名称",
          "sets": 3,
          "reps": "8-12",
          "rest_seconds": 90,
          "notes": "可选的动作提示"
        }
      ],
      "estimated_duration_minutes": 60,
      "warmup_notes": "热身建议",
      "cooldown_notes": "拉伸放松建议"
    }
  ],
  "rest_days": ["Day 4", "Day 6", "Day 7"],
  "daily_nutrition": {
    "calorie_target": 2200,
    "protein_g": 160,
    "carbs_g": 250,
    "fat_g": 65,
    "meal_suggestions": ["早餐: ...", "午餐: ...", "晚餐: ..."],
    "supplements": ["乳清蛋白粉（可选）"]
  },
  "coach_notes": "总体建议和鼓励"
}

## 要求

1. training_days 的数量必须严格等于用户指定的每周训练天数
2. 每个 exercise_id 必须来自提供的动作库列表
3. exercise_name 和 exercise_name_zh 必须与动作库一致
4. 热量、蛋白质目标必须使用用户资料中计算好的数值（不要自己重算）
5. 新手应优先全身训练，中级可使用上下分化，高级可使用推拉腿分化
6. 严格遵守提供的训练规则（尤其是 constraint 类型）
7. 只输出纯 JSON，不包含任何其他文字
"""


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
        Knowledge base instance (used to pull applicable rules).
    exercise_pool:
        Pre-filtered list of exercises (safe + equipment-compatible).
    """
    sections: list[str] = []

    # 1. User profile summary
    sections.append(_format_profile(profile))

    # 2. Applicable training rules
    rules_text = kb.format_rules_for_prompt(
        goal=profile.goal,
        level=profile.experience_level,
    )
    if rules_text:
        sections.append(f"## 训练规则\n\n{rules_text}")

    # 3. Exercise pool (condensed JSON array)
    sections.append(_format_exercise_pool(exercise_pool))

    # 4. Final instruction
    sections.append(
        "请根据以上信息，生成完整的 JSON 格式周训练计划。"
    )

    return "\n\n".join(sections)


def _format_profile(profile: UserProfile) -> str:
    """Format the user profile as a readable Markdown section."""
    lines = [
        "## 用户信息",
        "",
        f"- 姓名: {profile.name}",
        f"- 年龄: {profile.age} 岁",
        f"- 性别: {profile.gender}",
        f"- 身高: {profile.height_cm} cm",
        f"- 体重: {profile.weight_kg} kg",
        f"- 训练目标: {profile.goal.value}",
        f"- 经验水平: {profile.experience_level.value}",
        f"- 每周训练天数: {profile.training_days_per_week}",
        f"- 每次训练时长: {profile.session_duration_minutes} 分钟",
        f"- 可用器材: {', '.join(e.value for e in profile.available_equipment)}",
    ]

    if profile.injuries:
        lines.append(f"- 受伤/禁忌: {', '.join(profile.injuries)}")

    if profile.dietary_restrictions:
        lines.append(f"- 饮食限制: {', '.join(profile.dietary_restrictions)}")

    if profile.target_weight_kg:
        lines.append(f"- 目标体重: {profile.target_weight_kg} kg")

    lines += [
        "",
        "### 计算所得营养目标",
        f"- BMR: {profile.bmr:.0f} kcal/day" if profile.bmr else "- BMR: 未计算",
        f"- TDEE: {profile.tdee:.0f} kcal/day" if profile.tdee else "- TDEE: 未计算",
        (
            f"- 每日热量目标: {profile.daily_calorie_target:.0f} kcal"
            if profile.daily_calorie_target
            else "- 每日热量目标: 未计算"
        ),
        (
            f"- 每日蛋白质目标: {profile.daily_protein_target_g:.0f} g"
            if profile.daily_protein_target_g
            else "- 每日蛋白质目标: 未计算"
        ),
    ]

    return "\n".join(lines)


def _format_exercise_pool(exercises: list[Exercise]) -> str:
    """Format the exercise pool as a compact JSON array for LLM consumption."""
    # Only send the fields the LLM actually needs (keep prompt lean)
    pool = [
        {
            "id": ex.id,
            "name": ex.name,
            "name_zh": ex.name_zh,
            "category": ex.category.value,
            "equipment": [e.value for e in ex.equipment],
            "primary_muscles": [m.value for m in ex.primary_muscles],
            "difficulty": ex.difficulty.value,
            "movement_pattern": ex.movement_pattern.value,
        }
        for ex in exercises
    ]

    return (
        "## 可用动作库\n\n"
        + json.dumps(pool, ensure_ascii=False, indent=2)
    )
