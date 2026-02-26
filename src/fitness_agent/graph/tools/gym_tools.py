"""gym_tools — deterministic tools for the GYMAgent node.

Tools
-----
training_card_exporter:  Inject KB data (cues, muscles, equipment, warmup/cooldown,
                         injury adaptations) into a GymSessionPlan.
rpe_engine:              (Placeholder) Compute 4-week RPE progression parameters.
"""

from __future__ import annotations

import re

from fitness_agent.gym.models import GymSessionPlan
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.planner.models import TrainingDay
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# training_card_exporter
# ---------------------------------------------------------------------------


def training_card_exporter(
    session: GymSessionPlan,
    training_day: TrainingDay,
    profile: UserProfile,
    kb: KnowledgeBase,
) -> GymSessionPlan:
    """Inject KB data into a GymSessionPlan after LLM generation.

    Deterministically injects:
    - Exercise cues, muscle groups, equipment (from KB exercises)
    - Video URLs and breathing patterns (from KB exercises)
    - Warmup and cooldown sequences (from PlannerAgent notes or KB templates)
    - Injury-specific warmup modifications and warmup routine prepend
    - Injury adaptation notes for each exercise

    Modifies ``session`` in-place and returns it.

    Parameters
    ----------
    session:
        Parsed GymSessionPlan (LLM output, not yet KB-enriched).
    training_day:
        Corresponding TrainingDay from the WeeklyPlan (source of warmup/cooldown notes).
    profile:
        User profile (for injury information).
    kb:
        Initialised knowledge base.

    Returns
    -------
    GymSessionPlan
        The same session object, now enriched with KB data.
    """
    _inject_kb_data(session, kb)
    _inject_warmup_cooldown(session, training_day, profile, kb)
    _inject_injury_adaptations(session, profile, kb)
    return session


# ---------------------------------------------------------------------------
# rpe_engine (placeholder)
# ---------------------------------------------------------------------------


def rpe_engine(profile: UserProfile, session_count: int) -> list[dict]:
    """(Placeholder) Compute 4-week RPE progression parameters.

    Currently a stub — RPE progression is handled by the LLM in
    ``_generate_progression``.  This function is reserved for a future
    fully-deterministic RPE calculation based on profile and session count.

    Returns
    -------
    list[dict]
        Empty list (no deterministic RPE output yet).
    """
    logger.debug(
        f"rpe_engine: placeholder called for {profile.name}, "
        f"{session_count} sessions — returning empty list."
    )
    return []


# ---------------------------------------------------------------------------
# Internal helpers (extracted from GYMAgent private methods)
# ---------------------------------------------------------------------------


def _inject_kb_data(session: GymSessionPlan, kb: KnowledgeBase) -> None:
    """Inject KB cues, muscles, equipment, video URLs into exercises."""
    for eg in session.exercises:
        kb_ex = kb.get_exercise_by_id(eg.exercise_id)
        if kb_ex is None:
            continue

        eg.kb_cues = list(kb_ex.cues) if kb_ex.cues else []
        eg.primary_muscles = [m.value for m in kb_ex.primary_muscles]
        eg.secondary_muscles = [m.value for m in kb_ex.secondary_muscles]
        eg.equipment = [e.value for e in kb_ex.equipment]

        if kb_ex.video_url and not eg.video_url:
            eg.video_url = kb_ex.video_url

        if kb_ex.breathing_pattern_zh and not eg.breathing_zh:
            eg.breathing_zh = kb_ex.breathing_pattern_zh


def _inject_warmup_cooldown(
    session: GymSessionPlan,
    training_day: TrainingDay,
    profile: UserProfile,
    kb: KnowledgeBase,
) -> None:
    """Inject warmup/cooldown sequences.

    Priority: PlannerAgent's warmup_notes/cooldown_notes > KB templates > empty.
    After base warmup is determined, injury-specific warmup routines are
    prepended from KB injury_profiles.
    """
    # Priority 1: PlannerAgent's targeted warmup/cooldown
    if training_day.warmup_notes:
        session.warmup_sequence = _parse_notes_to_sequence(training_day.warmup_notes)
    if training_day.cooldown_notes:
        session.cooldown_sequence = _parse_notes_to_sequence(training_day.cooldown_notes)

    # Priority 2: KB template fallback
    movement_patterns: set[str] = set()
    for eg in session.exercises:
        kb_ex = kb.get_exercise_by_id(eg.exercise_id)
        if kb_ex is not None:
            movement_patterns.add(kb_ex.movement_pattern.value)

    template = kb.get_warmup_template(list(movement_patterns)) if movement_patterns else None

    if not session.warmup_sequence and template is not None:
        session.warmup_sequence = list(template.warmup_sequence)
    if not session.cooldown_sequence and template is not None:
        session.cooldown_sequence = list(template.cooldown_sequence)

    # Injury-specific warmup modifications from KB template
    if profile.injuries and template is not None and template.injury_modifications:
        mods: dict[str, str] = {}
        for injury in profile.injuries:
            tag_value = injury.value
            if tag_value in template.injury_modifications:
                mods[tag_value] = template.injury_modifications[tag_value]
        session.warmup_injury_modifications = mods

    # Injury-specific warmup routine prepend
    if profile.injuries and session.warmup_sequence:
        injury_warmup_steps: list[str] = []
        for injury_tag in profile.injuries:
            ip = kb.get_injury_profile(injury_tag)
            if ip is not None and ip.warmup_routine:
                injury_warmup_steps.append(f"【{ip.name_zh}专项热身 ~3分钟】")
                injury_warmup_steps.extend(ip.warmup_routine)
        if injury_warmup_steps:
            session.warmup_sequence = injury_warmup_steps + ["---"] + session.warmup_sequence


def _inject_injury_adaptations(
    session: GymSessionPlan,
    profile: UserProfile,
    kb: KnowledgeBase,
) -> None:
    """Inject injury adaptation notes from KB injury_profiles."""
    if not profile.injuries:
        return

    user_injury_set = set(profile.injuries)

    for eg in session.exercises:
        kb_ex = kb.get_exercise_by_id(eg.exercise_id)
        if kb_ex is None:
            continue

        exercise_contras = set(kb_ex.contraindications)
        overlapping = user_injury_set & exercise_contras

        if not overlapping and eg.injury_adaptations_zh:
            continue

        if overlapping:
            adaptation_parts: list[str] = []
            for injury_tag in overlapping:
                ip = kb.get_injury_profile(injury_tag)
                if ip is None:
                    continue
                if kb_ex.movement_pattern.value in ip.modify_movement_patterns:
                    mod = ip.modify_movement_patterns[kb_ex.movement_pattern.value]
                    adaptation_parts.append(f"{ip.name_zh}: {mod}")
                elif kb_ex.movement_pattern.value in ip.avoid_movement_patterns:
                    adaptation_parts.append(f"{ip.name_zh}: 此动作模式应避免，请考虑替代动作")

            if adaptation_parts:
                kb_adaptation = "；".join(adaptation_parts)
                if eg.injury_adaptations_zh:
                    eg.injury_adaptations_zh += f"（KB补充：{kb_adaptation}）"
                else:
                    eg.injury_adaptations_zh = kb_adaptation


def _parse_notes_to_sequence(notes: str) -> list[str]:
    """Parse PlannerAgent's warmup/cooldown notes into a step list.

    Handles three formats:
    1. ``"① 动作A → ② 动作B"``  (split on →)
    2. ``"① 动作A ② 动作B"``    (split on circled-number markers)
    3. Newline-separated text
    """
    notes = notes.strip()
    if not notes:
        return []

    if "→" in notes:
        parts = [p.strip() for p in notes.split("→") if p.strip()]
        if len(parts) > 1:
            return parts

    circled_re = re.compile(r"(?=[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])")
    parts = [p.strip() for p in circled_re.split(notes) if p.strip()]
    if len(parts) > 1:
        return parts

    parts = [p.strip() for p in notes.splitlines() if p.strip()]
    if len(parts) > 1:
        return parts

    return [notes]
