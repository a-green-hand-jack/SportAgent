"""planner_tools — deterministic tools for the PlannerAgent node.

Tools
-----
split_engine:   Build the safe exercise pool for a user (contraindication + equipment filter).
volume_checker: Validate weekly training volume against anatomy targets.
"""

from __future__ import annotations

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    Exercise,
    ExperienceLevel,
)
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Muscle rollup — fine-grained MuscleGroup → anatomy parent for volume checks
# ---------------------------------------------------------------------------

MUSCLE_ROLLUP: dict[str, str] = {
    "back": "lats",
    "front_delt": "shoulders",
    "side_delt": "shoulders",
    "rear_delt": "shoulders",
    "abs": "core",
    "obliques": "core",
}

MAX_EXERCISES_IN_POOL = 60


# ---------------------------------------------------------------------------
# split_engine
# ---------------------------------------------------------------------------


def split_engine(
    profile: UserProfile,
    kb: KnowledgeBase,
    max_exercises: int = MAX_EXERCISES_IN_POOL,
) -> list[Exercise]:
    """Build the safe exercise pool for a user profile.

    Steps
    -----
    1. Parse injury strings into ``ContraindicationTag`` enum values.
    2. Call ``KnowledgeBase.get_safe_exercises`` (contraindication + equipment filter).
    3. If the pool is empty (no equipment match), fall back to bodyweight-only.
    4. Limit pool to ``max_exercises`` to keep the LLM prompt lean.

    Parameters
    ----------
    profile:
        Fully enriched user profile.
    kb:
        Initialised knowledge base.
    max_exercises:
        Maximum number of exercises to include in the pool.

    Returns
    -------
    list[Exercise]
        Safe, equipment-filtered exercise pool (up to ``max_exercises`` entries).
    """
    contraindications = _parse_contraindications(profile.injuries)

    exercise_pool = kb.get_safe_exercises(
        contraindications=contraindications,
        available_equipment=profile.available_equipment,
    )

    if not exercise_pool:
        logger.warning(
            "split_engine: exercise pool is empty after filtering — falling back to bodyweight."
        )
        exercise_pool = kb.get_safe_exercises(
            contraindications=contraindications,
            available_equipment=[Equipment.bodyweight],
        )

    exercise_pool = exercise_pool[:max_exercises]

    logger.info(
        f"split_engine: {len(exercise_pool)} exercises for "
        f"{profile.name} ({profile.goal.value}, {profile.experience_level.value})"
    )
    return exercise_pool


# ---------------------------------------------------------------------------
# volume_checker
# ---------------------------------------------------------------------------


def volume_checker(
    plan: WeeklyPlan,
    kb: KnowledgeBase,
    level: ExperienceLevel,
) -> list[str]:
    """Validate weekly training volume against anatomy-based targets.

    Parameters
    ----------
    plan:
        The generated WeeklyPlan to check.
    kb:
        Initialised knowledge base (provides volume targets and exercise lookup).
    level:
        User's experience level (determines target ranges).

    Returns
    -------
    list[str]
        Warning strings for muscle groups below their minimum weekly set target.
        Empty list if all validations pass.
    """
    targets = kb.get_volume_targets(level)
    counts = _count_weekly_sets(plan, kb)
    warnings: list[str] = []
    for muscle_id, (min_sets, max_sets) in targets.items():
        actual = counts.get(muscle_id, 0)
        if actual == 0:
            continue
        if actual < min_sets:
            warnings.append(f"- {muscle_id}：本周 {actual} 组，推荐最低 {min_sets} 组")
        elif actual > max_sets:
            logger.debug(f"volume_checker: {muscle_id} above max: {actual} > {max_sets}")
    return warnings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_contraindications(injuries: list[ContraindicationTag]) -> list[ContraindicationTag]:
    """Return valid ContraindicationTag values from the profile's injuries list.

    The ``UserProfile.injuries`` field is already typed as ``list[ContraindicationTag]``,
    so this is effectively a pass-through that logs any unexpected values.
    """
    valid = {t.value for t in ContraindicationTag}
    result: list[ContraindicationTag] = []
    for tag in injuries:
        if isinstance(tag, ContraindicationTag):
            result.append(tag)
        elif isinstance(tag, str) and tag in valid:
            result.append(ContraindicationTag(tag))
        else:
            logger.warning(f"_parse_contraindications: unknown tag ignored: {tag!r}")
    return result


def _count_weekly_sets(plan: WeeklyPlan, kb: KnowledgeBase) -> dict[str, int]:
    """Count effective working sets per anatomy muscle group across all training days.

    Primary muscles are counted at full coefficient (1.0).
    Secondary muscles are counted at half coefficient (0.5).
    Fine-grained muscle names (e.g. 'back', 'front_delt') are rolled up
    to their anatomy parent group via the module-level MUSCLE_ROLLUP map.
    Exercises not found in the KB (e.g. LLM hallucinations) are skipped.
    """
    raw_counts: dict[str, float] = {}
    for day in plan.training_days:
        for ex_set in day.exercises:
            exercise = kb.get_exercise_by_id(ex_set.exercise_id)
            if exercise is None:
                logger.debug(
                    f"_count_weekly_sets: exercise_id '{ex_set.exercise_id}' not in KB, skipping."
                )
                continue
            for muscle in exercise.primary_muscles:
                muscle_id = MUSCLE_ROLLUP.get(muscle.value, muscle.value)
                raw_counts[muscle_id] = raw_counts.get(muscle_id, 0.0) + ex_set.sets
            for muscle in exercise.secondary_muscles:
                muscle_id = MUSCLE_ROLLUP.get(muscle.value, muscle.value)
                raw_counts[muscle_id] = raw_counts.get(muscle_id, 0.0) + ex_set.sets * 0.5
    return {k: round(v) for k, v in raw_counts.items()}
