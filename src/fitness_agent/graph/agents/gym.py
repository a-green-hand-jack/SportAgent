"""gym_node — LangGraph node for detailed gym training guidance generation.

Orchestrates:
  Incremental session generation (LLM) → training_card_exporter (KB injection)
  → 4-week progression (LLM) → duration validation → write gym_plan to state.
"""

from __future__ import annotations

import json

from fitness_agent.graph.knowledge.accessors import GYMKnowledge
from fitness_agent.graph.state import FitnessAgentState
from fitness_agent.graph.tools.gym_tools import training_card_exporter
from fitness_agent.gym.models import (
    GymSessionPlan,
    ProgressionWeek,
    WeeklyGymPlan,
)
from fitness_agent.gym.prompt import (
    GYM_PROGRESSION_SYSTEM,
    GYM_SYSTEM,
    build_gym_progression_message,
    build_gym_user_message,
)
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.planner.models import TrainingDay, WeeklyPlan
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import Message, build_client
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 1
WARMUP_COOLDOWN_MINUTES = 15
SECONDS_PER_SET_AVG = 90


def gym_node(state: FitnessAgentState) -> dict:
    """Generate detailed gym guidance and write it to the graph state.

    Reads
    -----
    state["user_profile"]  : dict
    state["weekly_plan"]   : dict (from plan_node)
    state["provider"]      : str
    state["model"]         : str

    Writes
    ------
    {"gym_plan": dict, "errors": list[str]}
    """
    profile = UserProfile.model_validate(state["user_profile"])
    weekly_plan_raw = state.get("weekly_plan")
    if weekly_plan_raw is None:
        return {"errors": ["gym_node: weekly_plan is required but not present in state."]}

    weekly_plan = WeeklyPlan.model_validate(weekly_plan_raw)
    client = build_client(provider=state["provider"], model=state["model"])
    kb = KnowledgeBase()
    _knowledge = GYMKnowledge(kb)  # available for future use

    training_days = weekly_plan.training_days
    if not training_days:
        return {"errors": ["gym_node: WeeklyPlan has no training days."]}

    logger.info(
        f"gym_node: generating guidance for {len(training_days)} training days "
        f"(provider: {client.provider})"
    )

    # --- Step 1: Generate each session incrementally ---
    all_sessions: list[GymSessionPlan] = []
    for training_day in training_days:
        already_json: str | None = None
        if all_sessions:
            already_json = json.dumps(
                [_session_to_compact_dict(s) for s in all_sessions],
                ensure_ascii=False,
                indent=2,
            )
        session = _generate_session(
            client,
            kb,
            profile,
            weekly_plan,
            training_day,
            already_generated_json=already_json,
        )
        # Tool: training_card_exporter — inject KB data into session
        training_card_exporter(session, training_day, profile, kb)
        all_sessions.append(session)

    # --- Step 2: Generate 4-week progression ---
    progression = _generate_progression(client, profile, all_sessions)

    # --- Step 3: Validate durations ---
    for session in all_sessions:
        for w in _validate_duration(session, profile.session_duration_minutes):
            logger.warning(w)

    # --- Step 4: Assemble final plan ---
    all_equipment: set[str] = set()
    for session in all_sessions:
        all_equipment.update(session.equipment_needed)

    plan = WeeklyGymPlan(
        user_name=profile.name,
        sessions=all_sessions,
        four_week_progression=progression,
        general_tips_zh=_build_general_tips(profile),
        equipment_checklist=sorted(all_equipment),
    )

    logger.info(f"gym_node: {plan.summary()}")
    return {
        "gym_plan": plan.model_dump(),
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Single-session generation
# ---------------------------------------------------------------------------


def _generate_session(
    client: object,
    kb: KnowledgeBase,
    profile: UserProfile,
    weekly_plan: WeeklyPlan,
    training_day: TrainingDay,
    already_generated_json: str | None,
) -> GymSessionPlan:
    """Call the LLM to generate guidance for a single training day."""
    from fitness_agent.utils.llm_client import BaseLLMClient

    assert isinstance(client, BaseLLMClient)

    user_message = build_gym_user_message(
        profile,
        weekly_plan,
        training_day,
        kb,
        already_generated_json=already_generated_json,
    )
    messages: list[Message] = [Message(role="user", content=user_message)]
    result: GymSessionPlan | None = None

    for attempt in range(MAX_RETRIES + 1):
        logger.info(
            f"gym_node: calling {client.provider}/{client.model} "
            f"for day {training_day.day_label} (attempt {attempt + 1}/{MAX_RETRIES + 1})..."
        )
        response = client.chat(
            messages=messages,
            system=GYM_SYSTEM,
            max_tokens=4096,
            temperature=0.7,
        )
        logger.info(
            f"gym_node: LLM responded {response.total_tokens} tokens "
            f"(in={response.input_tokens}, out={response.output_tokens})"
        )

        result = _parse_session_response(response.content, training_day.day_label)

        invalid_ids = _validate_exercise_ids(result, kb)
        if not invalid_ids:
            logger.info(f"gym_node: day {training_day.day_label}: validation passed.")
            break

        logger.info(
            f"gym_node: day {training_day.day_label}: {len(invalid_ids)} invalid exercise_id(s) "
            f"(attempt {attempt + 1})."
        )
        if attempt < MAX_RETRIES:
            messages.append(Message(role="assistant", content=response.content))
            correction = _build_exercise_id_correction(invalid_ids, kb)
            messages.append(Message(role="user", content=correction))

    assert result is not None
    return result


# ---------------------------------------------------------------------------
# 4-week progression generation
# ---------------------------------------------------------------------------


def _generate_progression(
    client: object,
    profile: UserProfile,
    sessions: list[GymSessionPlan],
) -> list[ProgressionWeek]:
    """Generate the 4-week progression plan with a separate LLM call."""
    from fitness_agent.utils.llm_client import BaseLLMClient

    assert isinstance(client, BaseLLMClient)

    sessions_json = json.dumps(
        [_session_to_compact_dict(s) for s in sessions],
        ensure_ascii=False,
        indent=2,
    )
    user_message = build_gym_progression_message(profile, sessions_json)

    logger.info(f"gym_node: calling {client.provider}/{client.model} for 4-week progression...")
    response = client.chat(
        messages=[Message(role="user", content=user_message)],
        system=GYM_PROGRESSION_SYSTEM,
        max_tokens=2048,
        temperature=0.5,
    )
    logger.info(
        f"gym_node: progression LLM responded {response.total_tokens} tokens "
        f"(in={response.input_tokens}, out={response.output_tokens})"
    )
    return _parse_progression_response(response.content)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_session_response(raw: str, expected_day_label: str) -> GymSessionPlan:
    """Parse a single GymSessionPlan from the LLM's raw text response."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"gym_node: LLM session response is not valid JSON: {exc}\n\n"
            f"Raw response:\n{raw[:500]}"
        ) from exc

    if isinstance(data, dict) and "sessions" in data:
        sessions = data["sessions"]
        if sessions:
            data = sessions[0]
    elif isinstance(data, list):
        if data:
            data = data[0]

    # Remove KB-injected fields the LLM may have erroneously included
    for ex_data in data.get("exercises", []):
        for field in ("warmup_sequence", "cooldown_sequence", "warmup_injury_modifications"):
            data.pop(field, None)
        for field in ("primary_muscles", "secondary_muscles", "equipment", "kb_cues"):
            ex_data.pop(field, None)

    try:
        return GymSessionPlan.model_validate(data)
    except Exception as exc:
        raise RuntimeError(
            f"gym_node: could not parse GymSessionPlan for {expected_day_label}: {exc}\n\n"
            f"Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        ) from exc


def _parse_progression_response(raw: str) -> list[ProgressionWeek]:
    """Parse 4 ProgressionWeek objects from the LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"gym_node: LLM progression response is not valid JSON: {exc}\n\n"
            f"Raw response:\n{raw[:500]}"
        ) from exc

    if isinstance(data, dict):
        data = data.get("four_week_progression", data.get("progression", []))

    if not isinstance(data, list):
        raise RuntimeError(f"gym_node: expected JSON array for progression, got {type(data)}")

    try:
        weeks = [ProgressionWeek.model_validate(w) for w in data]
    except Exception as exc:
        raise RuntimeError(f"gym_node: could not parse ProgressionWeek list: {exc}") from exc

    if len(weeks) != 4:
        logger.warning(f"gym_node: expected 4 progression weeks, got {len(weeks)}. Padding.")
        while len(weeks) < 4:
            weeks.append(
                ProgressionWeek(
                    week_number=len(weeks) + 1,
                    theme_zh="调整周",
                    volume_change_zh="维持当前训练量",
                    intensity_change_zh="维持当前强度",
                    rpe_target="RPE 7",
                    notes_zh="根据身体状态调整",
                )
            )
        weeks = weeks[:4]

    return weeks


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_exercise_ids(session: GymSessionPlan, kb: KnowledgeBase) -> list[str]:
    """Return list of exercise IDs not found in the KB."""
    return [
        eg.exercise_id for eg in session.exercises if kb.get_exercise_by_id(eg.exercise_id) is None
    ]


def _validate_duration(session: GymSessionPlan, target_minutes: int) -> list[str]:
    """Estimate session duration and compare to target."""
    total_sets = sum(eg.sets for eg in session.exercises)
    estimated = WARMUP_COOLDOWN_MINUTES + total_sets * SECONDS_PER_SET_AVG / 60
    warnings: list[str] = []
    if estimated > target_minutes * 1.3:
        warnings.append(
            f"{session.day_label}: 估算时长 {estimated:.0f} 分钟 "
            f"超过目标 {target_minutes} 分钟（+{(estimated/target_minutes-1)*100:.0f}%）"
        )
    elif estimated < target_minutes * 0.7:
        warnings.append(
            f"{session.day_label}: 估算时长 {estimated:.0f} 分钟 "
            f"低于目标 {target_minutes} 分钟（{(estimated/target_minutes-1)*100:.0f}%）"
        )
    return warnings


# ---------------------------------------------------------------------------
# Correction message builder
# ---------------------------------------------------------------------------


def _build_exercise_id_correction(invalid_ids: list[str], kb: KnowledgeBase) -> str:
    """Build a correction message for invalid exercise IDs."""
    valid_ids = sorted(ex.id for ex in kb.exercises)
    return (
        "以下 exercise_id 不在知识库中，请替换为有效的 ID：\n\n"
        "【无效 ID】\n" + "\n".join(f"- {eid}" for eid in invalid_ids) + "\n\n"
        "【有效 exercise_id 列表（部分）】\n" + ", ".join(valid_ids[:50]) + "\n\n"
        "调整要求：\n"
        "- 将无效 exercise_id 替换为语义最接近的有效 ID\n"
        "- 保持动作名称与新 ID 一致\n"
        "- 返回完整修正后的 JSON"
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _session_to_compact_dict(session: GymSessionPlan) -> dict:
    """Convert a session to a compact dict for context injection."""
    return {
        "day_label": session.day_label,
        "focus": session.focus,
        "estimated_duration_minutes": session.estimated_duration_minutes,
        "exercises": [
            {
                "exercise_id": eg.exercise_id,
                "exercise_name_zh": eg.exercise_name_zh,
                "sets": eg.sets,
                "reps": eg.reps,
                "coaching_tips_zh": eg.coaching_tips_zh,
                "starting_weight_zh": eg.starting_weight_zh,
                "tempo_zh": eg.tempo_zh,
            }
            for eg in session.exercises
        ],
        "session_flow_notes_zh": session.session_flow_notes_zh,
    }


def _build_general_tips(profile: UserProfile) -> str:
    """Build general training tips based on user profile."""
    tips: list[str] = []
    tips.append("训练前确保充分热身，训练后进行拉伸放松。")
    if profile.experience_level.value == "beginner":
        tips.append("初学者应优先掌握正确动作模式，重量其次。")
        tips.append("每个动作开始前先用空杆或极轻重量练习动作模式。")
    elif profile.experience_level.value == "intermediate":
        tips.append("中级训练者应注重渐进超负荷，每周小幅增加重量或组数。")
    if profile.injuries:
        injury_names = ", ".join(i.value for i in profile.injuries)
        tips.append(
            f"注意：您有 {injury_names} 相关问题，" f"训练中如有不适请立即停止并咨询专业人士。"
        )
    tips.append("组间休息时保持活动（轻微走动），避免完全静止。")
    tips.append("训练期间保持充足水分摄入（每 15-20 分钟小口饮水）。")
    tips.append("记录每次训练的重量和次数，以便追踪进步。")
    return "\n".join(f"- {t}" for t in tips)
