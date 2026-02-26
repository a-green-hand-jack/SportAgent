"""
Prompt builder for CookingAgent.

Constructs the structured prompt that is injected into the LLM to generate
a single day of a WeeklyCookingPlan.  The LLM receives:
  1. A system prompt explaining its role and the JSON output format.
  2. A user message containing:
     - User profile summary (dietary restrictions, calorie targets)
     - Training schedule (which days are training vs rest)
     - Macro targets with training-day vs rest-day differentiation
     - Recipe reference pool (from KB, filtered by dietary compatibility)
     - Food item database (compact reference from nutrition.json)
     - Dietary substitution rules (from nutrition_principles.json)
     - PlanAgent's existing meal suggestions (as reference, not binding)
     - Already-generated days (as JSON, for diversity/context awareness)
     - Final instruction for the specific day to generate
"""

from __future__ import annotations

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import RecipeTemplate
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.user.models import UserProfile

# ---------------------------------------------------------------------------
# System prompt (role + output schema)
# ---------------------------------------------------------------------------

COOKING_SYSTEM = """\
你是一位专业营养师和家庭烹饪顾问，擅长为健身人群设计实用、美味、营养均衡的每日餐食方案。

## ⚠️ 最高优先级约束（不可违反）

1. **每次只生成当天指定的一天计划**，输出单个 DayMealPlan JSON 对象（不是数组）。
2. 每天至少 3 餐（训练日需包含 pre_workout 和 post_workout 类型的餐食）。
3. 食材的 food_id **必须严格使用**食材数据库（下方表格）中的有效 ID，不可自创。
4. 每天的总热量必须接近对应目标（训练日和休息日目标不同），偏差不超过 ±10%。
5. 蛋白质每天不低于目标值的 90%。
6. 训练后餐（post_workout）蛋白质必须 >= 35g（快速吸收蛋白质来源：鸡胸肉、鱼肉、蛋白粉等）。
7. 输出纯 JSON，不含任何 markdown 代码块、注释或额外文字。
8. 每天的蛋白质主要来源（肉/鱼/蛋/豆）至少 2 种，同一蛋白质食材每天最多出现 2 次。
9. 单餐热量范围：pre_workout ≤ 400 kcal，snack 150-350 kcal，breakfast 400-700 kcal，lunch/dinner 500-1000 kcal。
10. 训练日不应同时包含 lunch 和 post_workout（post_workout 替代午餐时段）。
11. **菜品多样性（关键）**：已生成天中每道菜（recipe_id）全周最多出现 **2 次**。\
在生成当天时，请检查"已生成历史"部分，避免使用已出现 2 次的菜品。
12. **食材重量统一用熟重/即食重量**：大米、面条、意大利面、藜麦等主食的 amount_g \
必须是"煮熟后重量"（即用户端称量的重量）。食材数据库中的热量值均基于熟重。\
不要使用干重/生重标注。

注意：食材用量的精确热量/蛋白质将由系统自动微调。你只需选择合理的食材搭配和大致用量，
系统会自动调整份量以匹配热量目标。请专注于食材多样性和烹饪实用性。

## 训练日 vs 休息日营养差异

- **训练日**：碳水 +15-20%（为训练提供能量），总热量约 +5-8%
- **休息日**：碳水 -10-15%，脂肪可略增 +5-10%（促进恢复），总热量约 -3-5%

## 烹饪实用性原则

1. 每道菜的准备+烹饪时间控制在 30 分钟内（除特殊标注的慢炖菜）
2. 食材用量给出具体克数，方便称量
3. 烹饪步骤要具体可操作（温度、时间、手法）
4. 优先复用食材，减少一周内需要购买的食材种类
5. 标注适合批量备餐的菜品，给出储存和加热建议

## 输出格式

严格输出单个 DayMealPlan JSON 对象（注意：**不是数组，不是 daily_plans 键包裹**）：

{
  "day_label": "周一",
  "is_training_day": true,
  "meals": [
    {
      "recipe_id": "来自食谱库的ID或自创ID（snake_case）",
      "name_zh": "菜品中文名",
      "meal_type": "breakfast|lunch|dinner|snack|pre_workout|post_workout",
      "prep_time_minutes": 5,
      "cook_time_minutes": 10,
      "ingredients": [
        {
          "food_id": "chicken_breast",
          "food_name_zh": "鸡胸肉",
          "amount_g": 150,
          "note": "切丁"
        }
      ],
      "steps_zh": ["步骤1", "步骤2", "步骤3"],
      "per_serving_macros": {
        "calories": 450,
        "protein_g": 35,
        "carbs_g": 50,
        "fat_g": 12
      },
      "substitution_notes": ["乳糖不耐受：用豆浆替代牛奶"],
      "scaling_notes": "蛋白质不足时加1个蛋清"
    }
  ],
  "day_total_macros": {
    "calories": 2400,
    "protein_g": 170,
    "carbs_g": 280,
    "fat_g": 70
  }
}

注意：**不需要输出 shopping_list、meal_prep_suggestions、cooking_tips_zh、user_name**，系统会自动生成。
"""


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------

# Full 7-day week labels in Chinese
_WEEK_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def build_cooking_user_message(
    profile: UserProfile,
    weekly_plan: WeeklyPlan,
    kb: KnowledgeBase,
    compatible_recipes: list[RecipeTemplate],
    day_label: str,
    already_generated_json: str | None = None,
) -> str:
    """
    Assemble the user message for a single-day CookingAgent LLM call.

    Parameters
    ----------
    day_label:
        The day to generate (e.g. "周三").
    already_generated_json:
        JSON string of all previously generated DayMealPlan objects, injected
        as context so the model can avoid repeating dishes.  Pass None for the
        first day (周一).

    Sections (in order):
    1. User profile summary
    2. Training schedule
    3. Macro targets (training-day vs rest-day differentiation)
    4. Recipe reference pool
    5. Food item database (compact)
    6. Dietary substitution rules
    7. PlanAgent's existing meal suggestions (as reference)
    8. Already-generated days history (for diversity awareness)
    9. Final instruction for this specific day
    """
    sections: list[str] = []

    # --- Section 1: User profile summary ---
    cal = profile.daily_calorie_target or 2000
    pro = profile.daily_protein_target_g or 150
    sections.append(
        f"## 用户概况\n\n"
        f"- 姓名：{profile.name}\n"
        f"- 体重：{profile.weight_kg} kg\n"
        f"- 目标：{profile.goal.value}\n"
        f"- 饮食限制：{', '.join(profile.dietary_restrictions) if profile.dietary_restrictions else '无'}\n"
        f"- 基础热量目标：{cal:.0f} kcal/天\n"
        f"- 蛋白质目标：{pro:.0f} g/天\n"
        f"- 碳水目标：{weekly_plan.daily_nutrition.carbs_g:.0f} g/天\n"
        f"- 脂肪目标：{weekly_plan.daily_nutrition.fat_g:.0f} g/天"
    )

    # --- Section 1.5: Onboarding conversation summary ---
    if profile.profile_summary:
        sections.append(
            f"## 用户背景摘要（来自入门对话，请仔细阅读并优先参考）\n\n{profile.profile_summary}"
        )

    # --- Section 2: Training schedule ---
    # Normalize training day labels to Chinese weekday prefix for robust matching.
    # PlanAgent outputs day_label like "周一 (Day 1)" but CookingAgent iterates
    # over _WEEK_LABELS ["周一", "周二", ...], so we extract the prefix.
    training_day_labels: list[str] = []
    for d in weekly_plan.training_days:
        matched = False
        for wl in _WEEK_LABELS:
            if d.day_label.startswith(wl):
                training_day_labels.append(wl)
                matched = True
                break
        if not matched:
            training_day_labels.append(d.day_label)
    rest_day_labels = weekly_plan.rest_days
    schedule_lines = ["## 训练日程\n"]
    schedule_lines.append(f"训练日（{len(training_day_labels)} 天）：")
    for day in weekly_plan.training_days:
        schedule_lines.append(f"  - {day.day_label}：{day.focus}")
    schedule_lines.append(f"\n休息日：{', '.join(rest_day_labels) if rest_day_labels else '无'}")
    sections.append("\n".join(schedule_lines))

    # --- Section 3: Macro targets with training/rest day differentiation ---
    training_cal = cal * 1.07
    rest_cal = cal * 0.96
    training_carbs = weekly_plan.daily_nutrition.carbs_g * 1.17
    rest_carbs = weekly_plan.daily_nutrition.carbs_g * 0.88
    sections.append(
        f"## 训练日 vs 休息日营养目标\n\n"
        f"**训练日**（{len(training_day_labels)} 天）：\n"
        f"  - 热量：~{training_cal:.0f} kcal\n"
        f"  - 蛋白质：≥{pro:.0f} g\n"
        f"  - 碳水：~{training_carbs:.0f} g（+17%）\n"
        f"  - 脂肪：~{weekly_plan.daily_nutrition.fat_g:.0f} g\n\n"
        f"**休息日**（{len(rest_day_labels)} 天）：\n"
        f"  - 热量：~{rest_cal:.0f} kcal\n"
        f"  - 蛋白质：≥{pro:.0f} g\n"
        f"  - 碳水：~{rest_carbs:.0f} g（-12%）\n"
        f"  - 脂肪：~{weekly_plan.daily_nutrition.fat_g * 1.07:.0f} g（+7%）"
    )

    # --- Section 4: Recipe reference pool ---
    recipe_block = kb.format_recipes_for_prompt(compatible_recipes)
    if recipe_block:
        sections.append(recipe_block)

    # --- Section 5: Food item database (compact) ---
    food_block = kb.format_foods_compact_for_prompt()
    if food_block:
        sections.append(food_block)

    # --- Section 6: Dietary substitution rules ---
    if profile.dietary_restrictions:
        diet_block = kb.format_nutrition_principles_for_prompt(
            dietary_restrictions=profile.dietary_restrictions,
            goal=profile.goal,
        )
        if diet_block:
            sections.append(diet_block)

    # --- Section 7: PlanAgent's existing meal suggestions ---
    plan_ref_lines = ["## PlanAgent 餐食参考（仅供参考，可调整）\n"]
    nut = weekly_plan.daily_nutrition
    if nut.meal_suggestions:
        for meal in nut.meal_suggestions:
            plan_ref_lines.append(f"- {meal}")
    for day in weekly_plan.training_days:
        if day.pre_workout_meal:
            plan_ref_lines.append(f"- [{day.day_label}训练前] {day.pre_workout_meal}")
        if day.post_workout_meal:
            plan_ref_lines.append(f"- [{day.day_label}训练后] {day.post_workout_meal}")
    if len(plan_ref_lines) > 1:
        sections.append("\n".join(plan_ref_lines))

    # --- Section 8: Already-generated days (diversity context) ---
    if already_generated_json:
        sections.append(
            f"## 已生成天历史（请勿重复菜品，每道菜全周最多出现 2 次）\n\n"
            f"以下是此前已生成的各天计划（JSON）。生成今天时请检查这些天用过的菜品，"
            f"确保同一 recipe_id 全周出现不超过 2 次：\n\n"
            f"```json\n{already_generated_json}\n```"
        )

    # --- Section 9: Final instruction for this specific day ---
    is_training = day_label in training_day_labels
    day_type = "训练日" if is_training else "休息日"
    day_cal_target = training_cal if is_training else rest_cal

    instruction_lines = [
        "## 任务\n",
        f"请为 {profile.name} 生成 **{day_label}**（{day_type}）的烹饪计划。",
        f"- 热量目标：~{day_cal_target:.0f} kcal",
        f"- 蛋白质目标：≥{pro:.0f} g",
    ]
    if is_training:
        instruction_lines += [
            "- 必须包含 pre_workout 和 post_workout 餐（訓練日要求）",
            "- post_workout 蛋白质 >= 35g",
            "- 训练日不同时包含 lunch 和 post_workout",
        ]
    else:
        instruction_lines += [
            "- 4–5 餐，无训练前/后餐",
            "- 通过加餐或增加主餐份量确保热量达标",
        ]
    instruction_lines += [
        "- food_id 必须严格使用食材数据库中的 ID",
        "- 检查已生成历史，避免菜品（recipe_id）超过 2 次",
        '- 输出单个 DayMealPlan JSON 对象，day_label 必须为 "' + day_label + '"',
    ]
    sections.append("\n".join(instruction_lines))

    return "\n\n".join(sections)
