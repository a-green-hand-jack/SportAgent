"""
Prompt builder for GYMAgent.

Constructs the structured prompt that is injected into the LLM to generate
detailed exercise guidance for a single training day.  The LLM receives:
  1. A system prompt explaining its role and the JSON output format.
  2. A user message containing:
     - User profile summary (weight, experience, injuries, equipment, strength)
     - Training day details from PlanAgent
     - Exercise reference data from KB
     - Injury guidance (from KB injury_profiles)
     - Already-generated sessions (for consistency)
     - Final instruction for the specific day

A separate progression prompt generates the 4-week periodisation table
after all sessions are complete.
"""
from __future__ import annotations

import json

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import ContraindicationTag, Exercise
from fitness_agent.planner.models import TrainingDay, WeeklyPlan
from fitness_agent.user.models import UserProfile


# ---------------------------------------------------------------------------
# System prompt (role + output schema)
# ---------------------------------------------------------------------------

GYM_SYSTEM = """\
你是一位经验丰富的健身教练，擅长为不同水平的训练者提供精细化的训练执行指导。

## ⚠️ 最高优先级约束（不可违反）

1. **每次只生成当天指定的一个训练日指导**，输出单个 GymSessionPlan JSON 对象（不是数组）。
2. 每个动作必须包含 2-3 条个性化教练提示（coaching_tips_zh），**不要重复 KB 中已有的 cues**。
3. 每个动作的 exercise_id **必须使用** PlanAgent 提供的 ID，不可自创。
4. 每个动作必须包含呼吸指导（breathing_zh）。
5. 每个动作必须包含至少 1 条常见错误（common_mistakes_zh）。
6. 起始重量建议（starting_weight_zh）必须基于用户的 strength_assessment 和 experience_level。
7. 有伤病时必须提供具体适配方案（injury_adaptations_zh），说明如何修改动作。
8. 输出纯 JSON，不含任何 markdown 代码块、注释或额外文字。
9. 节奏标注格式：离心-停顿-向心（如 "3-1-2"），可选填。
10. session_flow_notes_zh 应包含训练流程建议（超级组搭配、休息管理等）。
11. equipment_needed 列出当天训练需要的器材。
12. estimated_duration_minutes 需要合理估算（考虑组间休息和热身拉伸）。

## 起始重量参考（基于 strength_assessment）

- **beginner_no_weights**: 所有动作从徒手或最轻重量开始
- **beginner_light**: 杠铃 20kg（空杆），哑铃 2-5kg
- **beginner_moderate**: 杠铃 25-35kg，哑铃 5-10kg
- **intermediate**: 根据动作类型建议合理重量（大肌群复合动作更重）

⚠️ **重要**：GYMAgent 的起始重量建议**不应超过** PlanAgent 提供的 weight_hint。\
有伤病时应在 weight_hint 基础上降低 20-40%，而非增加。

## 输出格式

严格输出单个 GymSessionPlan JSON 对象：

{
  "day_label": "周一 (Day 1)",
  "focus": "上肢推力",
  "is_training_day": true,
  "estimated_duration_minutes": 60,
  "exercises": [
    {
      "exercise_id": "barbell_bench_press",
      "exercise_name_zh": "杠铃卧推",
      "exercise_name": "Barbell Bench Press",
      "sets": 4,
      "reps": "8-12",
      "rest_seconds": 90,
      "coaching_tips_zh": [
        "想象把杆弯成U型来激活背阔肌稳定",
        "触胸时短暂停顿消除惯性，感受胸肌发力"
      ],
      "starting_weight_zh": "从空杆(20kg)开始，每组加2.5kg找到合适重量",
      "breathing_zh": "下放时深吸气并憋住，推起过最难点后呼气",
      "common_mistakes_zh": [
        "双脚乱动失去下半身稳定性"
      ],
      "tempo_zh": "3-1-2",
      "injury_adaptations_zh": null,
      "video_url": null,
      "superset_with": null
    }
  ],
  "session_flow_notes_zh": "建议先完成复合动作（卧推），再做孤立动作...",
  "equipment_needed": ["杠铃", "卧推凳", "哑铃"]
}

注意：**不需要输出 warmup_sequence、cooldown_sequence、warmup_injury_modifications**，\
这些字段由系统从 KB 确定性注入。\
也不需要输出 primary_muscles、secondary_muscles、equipment、kb_cues，这些也由系统注入。
"""


# ---------------------------------------------------------------------------
# Progression system prompt
# ---------------------------------------------------------------------------

GYM_PROGRESSION_SYSTEM = """\
你是一位经验丰富的健身教练，擅长制定周期化训练的渐进方案。

## 任务

根据用户档案和已生成的训练计划，生成一个 4 周的渐进参数表。

## 约束

1. 必须恰好 4 周。
2. 第 1 周为适应期（RPE 6-7），第 4 周为减量周（降低训练量和强度）。
3. 渐进须符合用户经验水平：初学者增量更保守，中级可更激进。
4. 输出纯 JSON 数组（4 个 ProgressionWeek 对象）。
5. 不含 markdown 代码块或额外文字。
6. **exercise_specific_zh** 字段必须绑定到具体动作，给出明确数值变化。\
格式示例：["深蹲: 20kg→22.5kg", "卧推: 保持 3×8-12 但 +1 组至 4×8-12"]。
7. 有伤病的动作渐进幅度应更保守（如每周仅增加 1 rep 而非增加重量）。

## 输出格式

[
  {
    "week_number": 1,
    "theme_zh": "适应期",
    "volume_change_zh": "按计划执行基准组数",
    "intensity_change_zh": "使用计划建议的起始重量",
    "rpe_target": "RPE 6-7",
    "notes_zh": "重点掌握动作模式，不要追求重量",
    "exercise_specific_zh": [
      "杠铃深蹲: 空杆 20kg × 4组8-12次",
      "哑铃卧推: 5kg × 3组10-12次"
    ]
  },
  ...
]
"""


# ---------------------------------------------------------------------------
# User message builder — single session
# ---------------------------------------------------------------------------

def build_gym_user_message(
    profile: UserProfile,
    weekly_plan: WeeklyPlan,
    training_day: TrainingDay,
    kb: KnowledgeBase,
    already_generated_json: str | None = None,
) -> str:
    """
    Assemble the user message for a single training-day GYMAgent LLM call.

    Sections (in order):
    1. User profile summary
    2. Training day details (from PlanAgent)
    3. Exercise reference data (from KB)
    4. Injury guidance
    5. Already-generated sessions history
    6. Final instruction
    """
    sections: list[str] = []

    # --- Section 1: User profile summary ---
    injuries_str = ", ".join(i.value for i in profile.injuries) if profile.injuries else "无"
    equipment_str = ", ".join(e.value for e in profile.available_equipment) if profile.available_equipment else "无"
    strength = profile.strength_assessment or "未评估"
    preferred_time = profile.preferred_training_time or "flexible"

    sections.append(
        f"## 用户概况\n\n"
        f"- 姓名：{profile.name}\n"
        f"- 年龄：{profile.age} 岁\n"
        f"- 体重：{profile.weight_kg} kg\n"
        f"- 身高：{profile.height_cm} cm\n"
        f"- 目标：{profile.goal.value}\n"
        f"- 经验水平：{profile.experience_level.value}\n"
        f"- 力量评估：{strength}\n"
        f"- 每次训练时长：{profile.session_duration_minutes} 分钟\n"
        f"- 伤病/禁忌：{injuries_str}\n"
        f"- 可用器材：{equipment_str}\n"
        f"- 偏好训练时间：{preferred_time}"
    )

    # --- Section 2: Training day details (from PlanAgent) ---
    exercise_lines = []
    for ex in training_day.exercises:
        line = (
            f"  - {ex.exercise_name_zh} ({ex.exercise_id}): "
            f"{ex.sets}×{ex.reps}, 休息{ex.rest_seconds}s"
        )
        if ex.weight_hint:
            line += f" [{ex.weight_hint}]"
        if ex.notes:
            line += f" 注: {ex.notes}"
        exercise_lines.append(line)

    plan_section = (
        f"## 当天训练计划（来自 PlanAgent）\n\n"
        f"- 训练日：{training_day.day_label}\n"
        f"- 重点：{training_day.focus}\n"
        f"- 预估时长：{training_day.estimated_duration_minutes} 分钟\n"
        f"- 动作列表：\n" + "\n".join(exercise_lines)
    )
    if training_day.warmup_notes:
        plan_section += f"\n- PlanAgent 热身方案：{training_day.warmup_notes}"
    if training_day.cooldown_notes:
        plan_section += f"\n- PlanAgent 拉伸方案：{training_day.cooldown_notes}"
    sections.append(plan_section)

    # --- Section 3: Exercise reference data from KB ---
    kb_exercise_lines = ["## 动作 KB 参考数据\n"]
    kb_exercise_lines.append(
        "以下是每个动作在知识库中的详细信息，供你参考（不要重复这些 cues）：\n"
    )
    for ex_set in training_day.exercises:
        kb_ex = kb.get_exercise_by_id(ex_set.exercise_id)
        if kb_ex is None:
            kb_exercise_lines.append(
                f"**{ex_set.exercise_name_zh} ({ex_set.exercise_id})**：KB 中无数据\n"
            )
            continue
        kb_exercise_lines.append(
            _format_exercise_kb_reference(kb_ex)
        )
    sections.append("\n".join(kb_exercise_lines))

    # --- Section 4: Injury guidance ---
    if profile.injuries:
        injury_block = kb.format_injury_guidance_for_prompt(profile.injuries)
        if injury_block:
            sections.append(injury_block)

    # --- Section 5: Already-generated sessions (consistency context) ---
    if already_generated_json:
        sections.append(
            f"## 已生成训练日历史（确保风格一致、器材建议连贯）\n\n"
            f"以下是此前已生成的训练日指导（JSON）。生成今天时请保持风格一致，"
            f"教练提示不要与之前的完全重复：\n\n"
            f"```json\n{already_generated_json}\n```"
        )

    # --- Section 6: Final instruction ---
    sections.append(
        f"## 任务\n\n"
        f"请为 {profile.name} 生成 **{training_day.day_label}**"
        f"（{training_day.focus}）的详细训练执行指导。\n"
        f"- exercise_id 必须严格使用上方 PlanAgent 提供的 ID\n"
        f"- 每个动作 2-3 条教练提示（不要重复 KB cues 中已有的内容）\n"
        f"- 基于力量评估（{strength}）给出合理的起始重量建议\n"
        f"- 起始重量不应超过 PlanAgent 提供的 weight_hint；有伤病时应进一步降低 20-40%\n"
        f"- 输出单个 GymSessionPlan JSON 对象，day_label 必须为 \"{training_day.day_label}\""
    )

    return "\n\n".join(sections)


def _format_exercise_kb_reference(ex: Exercise) -> str:
    """Format a single Exercise from KB as a reference block for the prompt."""
    lines = [f"**{ex.name_zh} ({ex.id})**"]
    lines.append(f"  - 主要肌群：{', '.join(m.value for m in ex.primary_muscles)}")
    if ex.secondary_muscles:
        lines.append(f"  - 次要肌群：{', '.join(m.value for m in ex.secondary_muscles)}")
    lines.append(f"  - 器材：{', '.join(e.value for e in ex.equipment)}")
    lines.append(f"  - 动作模式：{ex.movement_pattern.value}")
    lines.append(f"  - 难度：{ex.difficulty}")
    if ex.cues:
        lines.append(f"  - KB Cues：{' | '.join(ex.cues)}")
    if ex.detailed_technique_zh:
        lines.append(f"  - 技术细节：{ex.detailed_technique_zh}")
    if ex.common_mistakes_zh:
        lines.append(f"  - KB 常见错误：{'；'.join(ex.common_mistakes_zh)}")
    if ex.breathing_pattern_zh:
        lines.append(f"  - KB 呼吸模式：{ex.breathing_pattern_zh}")
    if ex.contraindications:
        lines.append(
            f"  - 禁忌：{', '.join(c.value for c in ex.contraindications)}"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Progression message builder
# ---------------------------------------------------------------------------

def build_gym_progression_message(
    profile: UserProfile,
    sessions_json: str,
) -> str:
    """
    Build the user message for the 4-week progression LLM call.

    Called once after all training sessions have been generated,
    so the model has full context.
    """
    strength = profile.strength_assessment or "未评估"

    sections: list[str] = []

    injuries_str = ", ".join(i.value for i in profile.injuries) if profile.injuries else "无"

    sections.append(
        f"## 用户概况\n\n"
        f"- 姓名：{profile.name}\n"
        f"- 经验水平：{profile.experience_level.value}\n"
        f"- 力量评估：{strength}\n"
        f"- 目标：{profile.goal.value}\n"
        f"- 每周训练天数：{profile.training_days_per_week}\n"
        f"- 伤病/禁忌：{injuries_str}"
    )

    sections.append(
        f"## 已生成的训练计划\n\n"
        f"以下是本周所有训练日的详细指导（JSON）：\n\n"
        f"```json\n{sessions_json}\n```"
    )

    sections.append(
        f"## 任务\n\n"
        f"请为 {profile.name} 生成 4 周渐进参数表。\n"
        f"- 恰好 4 个 ProgressionWeek 对象组成的 JSON 数组\n"
        f"- 第 1 周：适应期（RPE 6-7）\n"
        f"- 第 2-3 周：渐进增加（重量或组数）\n"
        f"- 第 4 周：减量周（降低 ~40% 训练量）\n"
        f"- 渐进幅度匹配经验水平（{profile.experience_level.value}）\n"
        f"- 输出纯 JSON 数组，不含 markdown 或额外文字"
    )

    return "\n\n".join(sections)
