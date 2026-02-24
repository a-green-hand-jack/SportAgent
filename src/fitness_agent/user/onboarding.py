"""
Interactive Q&A onboarding flow that collects user information and
builds a fully-enriched UserProfile.

The module is designed to be IO-injectable so it can be tested without
a real terminal:
    - `ask_fn`  — defaults to `input()` but can be replaced in tests
    - `print_fn` — defaults to `print()` but can be replaced in tests

When running inside the CLI, the caller passes Rich's `console.print`
and a custom `input` wrapper so that colours and prompts work correctly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.logging import get_logger

if TYPE_CHECKING:
    from fitness_agent.utils.llm_client import BaseLLMClient

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Type alias for the IO functions
# ---------------------------------------------------------------------------

AskFn = Callable[[str], str]
PrintFn = Callable[..., None]


# ---------------------------------------------------------------------------
# Low-level Q&A helpers
# ---------------------------------------------------------------------------

def _ask(prompt: str, ask_fn: AskFn) -> str:
    """Ask a question and return the stripped answer, retrying until non-empty."""
    while True:
        answer = ask_fn(prompt).strip()
        if answer:
            return answer


def _ask_choice(
    prompt: str,
    choices: list[str],
    ask_fn: AskFn,
    print_fn: PrintFn,
    *,
    allow_multiple: bool = False,
) -> str | list[str]:
    """
    Present a numbered-choice menu and return the user's selection.

    If `allow_multiple` is True the user can enter comma-separated indices
    and a list of values is returned.
    """
    while True:
        print_fn(prompt)
        for i, choice in enumerate(choices, 1):
            print_fn(f"  {i}. {choice}")

        if allow_multiple:
            raw = ask_fn("输入编号（多选用逗号分隔）: ").strip()
            indices = [p.strip() for p in raw.split(",") if p.strip()]
            selected = []
            valid = True
            for idx_str in indices:
                if not idx_str.isdigit() or not (1 <= int(idx_str) <= len(choices)):
                    print_fn(f"  ⚠️  无效编号: {idx_str!r}，请重新输入")
                    valid = False
                    break
                selected.append(choices[int(idx_str) - 1])
            if valid and selected:
                return selected
        else:
            raw = ask_fn("输入编号: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(choices):
                return choices[int(raw) - 1]
            print_fn(f"  ⚠️  请输入 1 到 {len(choices)} 之间的数字")


def _ask_float(
    prompt: str,
    ask_fn: AskFn,
    print_fn: PrintFn,
    *,
    min_val: float,
    max_val: float,
) -> float:
    """Ask for a float value within [min_val, max_val]."""
    while True:
        raw = ask_fn(prompt).strip()
        try:
            val = float(raw)
            if min_val <= val <= max_val:
                return val
            print_fn(f"  ⚠️  请输入 {min_val}–{max_val} 之间的数字")
        except ValueError:
            print_fn("  ⚠️  请输入有效数字")


def _ask_int(
    prompt: str,
    ask_fn: AskFn,
    print_fn: PrintFn,
    *,
    min_val: int,
    max_val: int,
) -> int:
    """Ask for an integer value within [min_val, max_val]."""
    while True:
        raw = ask_fn(prompt).strip()
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            print_fn(f"  ⚠️  请输入 {min_val}–{max_val} 之间的整数")
        except ValueError:
            print_fn("  ⚠️  请输入有效整数")


# ---------------------------------------------------------------------------
# Equipment display helpers
# ---------------------------------------------------------------------------

_EQUIPMENT_LABELS: dict[str, str] = {
    Equipment.bodyweight.value:     "徒手/自重 (bodyweight)",
    Equipment.dumbbell.value:       "哑铃 (dumbbell)",
    Equipment.barbell.value:        "杠铃 (barbell)",
    Equipment.kettlebell.value:     "壶铃 (kettlebell)",
    Equipment.resistance_band.value:"弹力带 (resistance_band)",
    Equipment.cable_machine.value:  "绳索器械 (cable_machine)",
    Equipment.machine.value:        "固定器械 (machine)",
    Equipment.pull_up_bar.value:    "单杠 (pull_up_bar)",
    Equipment.bench.value:          "长凳/哑铃凳 (bench)",
    Equipment.ez_bar.value:         "EZ 杆 (ez_bar)",
}

_GOAL_LABELS: dict[str, str] = {
    GoalType.fat_loss.value:           "减脂 (fat_loss)",
    GoalType.muscle_gain.value:        "增肌 (muscle_gain)",
    GoalType.body_recomposition.value: "增肌减脂 (body_recomposition)",
    GoalType.general_fitness.value:    "提升体能 (general_fitness)",
}

_LEVEL_LABELS: dict[str, str] = {
    ExperienceLevel.beginner.value:    "新手 (beginner) — 训练不足1年",
    ExperienceLevel.intermediate.value:"中级 (intermediate) — 1-3年",
    ExperienceLevel.advanced.value:    "高级 (advanced) — 3年以上",
}

_ACTIVITY_LABELS: dict[str, str] = {
    "sedentary":         "久坐不动 (办公室工作，几乎不运动)",
    "lightly_active":    "轻度活跃 (每周轻度运动 1-3 次)",
    "moderately_active": "中度活跃 (每周中度运动 3-5 次)",
    "very_active":       "高度活跃 (每周高强度运动 6-7 次)",
}



# ---------------------------------------------------------------------------
# Main onboarding flow
# ---------------------------------------------------------------------------

def run_onboarding(
    ask_fn: AskFn | None = None,
    print_fn: PrintFn | None = None,
    llm_client: BaseLLMClient | None = None,
) -> UserProfile:
    """
    Run an interactive Q&A session and return a fully-enriched UserProfile.

    Parameters
    ----------
    ask_fn:
        Callable that takes a prompt string and returns the user's input.
        Defaults to the built-in ``input``.
    print_fn:
        Callable used to display text.  Defaults to the built-in ``print``.
    """
    if ask_fn is None:
        ask_fn = input
    if print_fn is None:
        print_fn = print

    print_fn("\n" + "=" * 60)
    print_fn("  🏋️  欢迎使用 AI 健身规划助手  🏋️")
    print_fn("=" * 60)
    print_fn("请回答以下问题，我将为你生成个性化的训练计划。\n")

    # --- Basic info ---
    name = _ask("你的名字: ", ask_fn)

    age = _ask_int(
        "你的年龄: ",
        ask_fn, print_fn,
        min_val=14, max_val=80,
    )

    gender_choice = _ask_choice(
        "性别:", ["男 (male)", "女 (female)", "其他 (other)"],
        ask_fn, print_fn,
    )
    gender_map = {
        "男 (male)": "male",
        "女 (female)": "female",
        "其他 (other)": "other",
    }
    gender = gender_map[gender_choice]  # type: ignore[index]

    height_cm = _ask_float(
        "身高（cm）: ",
        ask_fn, print_fn,
        min_val=120, max_val=220,
    )

    weight_kg = _ask_float(
        "体重（kg）: ",
        ask_fn, print_fn,
        min_val=30, max_val=200,
    )

    # --- Goal ---
    goal_choices = list(_GOAL_LABELS.values())
    goal_label = _ask_choice(
        "\n你的训练目标:", goal_choices, ask_fn, print_fn,
    )
    goal_value = [k for k, v in _GOAL_LABELS.items() if v == goal_label][0]
    goal = GoalType(goal_value)

    target_weight_kg: float | None = None
    if goal == GoalType.fat_loss:
        tw_raw = ask_fn("目标体重（kg，可跳过直接回车）: ").strip()
        if tw_raw:
            try:
                tw = float(tw_raw)
                if 30 <= tw <= 200:
                    target_weight_kg = tw
            except ValueError:
                pass

    # --- Experience ---
    level_choices = list(_LEVEL_LABELS.values())
    level_label = _ask_choice(
        "\n你的训练经验:", level_choices, ask_fn, print_fn,
    )
    level_value = [k for k, v in _LEVEL_LABELS.items() if v == level_label][0]
    experience_level = ExperienceLevel(level_value)

    # --- Activity ---
    act_choices = list(_ACTIVITY_LABELS.values())
    act_label = _ask_choice(
        "\n日常活动水平（不含训练）:", act_choices, ask_fn, print_fn,
    )
    activity_level = [k for k, v in _ACTIVITY_LABELS.items() if v == act_label][0]

    # --- Training schedule ---
    print_fn("")
    training_days_per_week = _ask_int(
        "每周训练几天（1-6）: ",
        ask_fn, print_fn,
        min_val=1, max_val=6,
    )

    session_duration_minutes = _ask_int(
        "每次训练时长（分钟，20-180）: ",
        ask_fn, print_fn,
        min_val=20, max_val=180,
    )

    # --- Equipment ---
    eq_choices = list(_EQUIPMENT_LABELS.values())
    eq_selected = _ask_choice(
        "\n你能使用哪些器材（多选）:",
        eq_choices,
        ask_fn,
        print_fn,
        allow_multiple=True,
    )
    eq_values = [k for k, v in _EQUIPMENT_LABELS.items() if v in eq_selected]
    available_equipment = [Equipment(e) for e in eq_values]

    # --- Injuries / contraindications (optional, free-text + LLM) ---
    from fitness_agent.knowledge_base.models import ContraindicationTag
    from fitness_agent.utils.text_parser import format_injuries_for_display, parse_injuries_with_llm

    injuries: list[ContraindicationTag] = []
    print_fn("\n是否有受伤史或需要规避的动作？（可跳过直接回车）")
    inj_raw = ask_fn(
        '请描述你的伤病情况（自由输入，如 "手腕疼、膝盖不好"，直接回车跳过）: '
    ).strip()
    if inj_raw and llm_client is not None:
        print_fn("  🔍 正在分析你的伤病描述…")
        injuries = parse_injuries_with_llm(inj_raw, llm_client)
        display = format_injuries_for_display(injuries)
        print_fn(f"  📋 识别到的伤病: {display}")
        confirm = ask_fn("以上是否正确？(Y/n，直接回车确认): ").strip().lower()
        if confirm in ("n", "no", "否"):
            injuries = []
            print_fn("  ✏️  已清除伤病记录，你可以稍后在个人资料中手动添加。")
    elif inj_raw:
        # No LLM client — warn user but don't crash
        print_fn("  ⚠️  无法解析自由文本（LLM 未配置），已跳过伤病输入。")
        logger.warning("Skipped injury parsing: no LLM client provided.")

    # --- Dietary restrictions (optional) ---
    diet_raw = ask_fn("\n饮食限制（如素食/乳糖不耐，可跳过直接回车）: ").strip()
    dietary_restrictions: list[str] = []
    if diet_raw:
        dietary_restrictions = [p.strip() for p in diet_raw.split(",") if p.strip()]

    # --- Build and enrich profile ---
    profile = UserProfile(
        name=name,
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg,
        goal=goal,
        target_weight_kg=target_weight_kg,
        experience_level=experience_level,
        training_days_per_week=training_days_per_week,
        session_duration_minutes=session_duration_minutes,
        available_equipment=available_equipment,
        injuries=injuries,
        activity_level=activity_level,
        dietary_restrictions=dietary_restrictions,
    )

    enriched = enrich_profile(profile)

    print_fn("\n✅ 信息收集完成！")
    print_fn(f"  BMR:          {enriched.bmr:.0f} kcal/day")
    print_fn(f"  TDEE:         {enriched.tdee:.0f} kcal/day")
    print_fn(f"  热量目标:     {enriched.daily_calorie_target:.0f} kcal/day")
    print_fn(f"  蛋白质目标:   {enriched.daily_protein_target_g:.0f} g/day")

    return enriched


# ---------------------------------------------------------------------------
# Profile persistence helpers
# ---------------------------------------------------------------------------

def save_profile(profile: UserProfile, path: Path) -> None:
    """Serialise profile to JSON (excluding unset computed fields if None)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        profile.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info(f"Profile saved to {path}")


def load_profile(path: Path) -> UserProfile:
    """Load a UserProfile from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserProfile.model_validate(data)
