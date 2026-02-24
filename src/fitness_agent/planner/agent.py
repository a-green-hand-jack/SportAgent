"""
PlannerAgent — orchestrates the full planning pipeline:

  1. Deterministic KB filtering (safety + equipment)
  2. Build structured LLM prompt (user context + rules + exercise pool)
  3. Call LLM and parse the JSON response into a WeeklyPlan

The agent is deliberately stateless (no session history) — each call
is a fresh plan generation.
"""
from __future__ import annotations

import json

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import ContraindicationTag, Equipment, ExperienceLevel
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.planner.prompt import PLANNER_SYSTEM, build_user_message
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import BaseLLMClient, Message
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)


class PlannerAgent:
    """
    AI fitness planner that combines deterministic KB logic with LLM creativity.

    Parameters
    ----------
    client:
        Any ``BaseLLMClient`` instance (Anthropic, DeepSeek, Gemini, …).
    kb:
        Knowledge base providing exercises, foods, and rules.
    max_exercises_in_pool:
        Cap on the number of exercises sent to the LLM (keeps prompt short).
    """

    def __init__(
        self,
        client: BaseLLMClient,
        kb: KnowledgeBase,
        max_exercises_in_pool: int = 60,
    ) -> None:
        self.client = client
        self.kb = kb
        self.max_exercises_in_pool = max_exercises_in_pool

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_plan(self, profile: UserProfile) -> WeeklyPlan:
        """
        Generate a personalised WeeklyPlan for the given profile.

        The profile **must** be fully enriched (bmr/tdee/calorie_target set).
        Call ``enrich_profile(profile)`` first if needed.

        Raises
        ------
        ValueError
            If the profile is missing computed nutrition fields.
        RuntimeError
            If the LLM returns a response that cannot be parsed as a WeeklyPlan.
        """
        if profile.bmr is None or profile.daily_calorie_target is None:
            raise ValueError(
                "Profile must be enriched before planning. "
                "Call enrich_profile(profile) first."
            )

        # --- Step 1: deterministic KB filtering ---
        contraindications = self._parse_contraindications(profile.injuries)
        exercise_pool = self.kb.get_safe_exercises(
            contraindications=contraindications,
            available_equipment=profile.available_equipment,
        )

        # If pool is empty (e.g. no equipment matched), fall back to bodyweight
        if not exercise_pool:
            logger.warning(
                "Exercise pool is empty after filtering — falling back to bodyweight."
            )
            exercise_pool = self.kb.get_safe_exercises(
                contraindications=contraindications,
                available_equipment=[Equipment.bodyweight],
            )

        # Limit pool size to keep the prompt lean
        exercise_pool = exercise_pool[: self.max_exercises_in_pool]

        logger.info(
            f"Exercise pool: {len(exercise_pool)} exercises for "
            f"{profile.name} ({profile.goal.value}, {profile.experience_level.value})"
        )

        # --- Step 2: build prompt ---
        user_message = build_user_message(profile, self.kb, exercise_pool)
        logger.debug(f"Prompt length: ~{len(user_message)} chars")

        # --- Step 3: LLM call ---
        logger.info(
            f"Calling {self.client.provider}/{self.client.model} for plan generation…"
        )
        response = self.client.chat(
            messages=[Message(role="user", content=user_message)],
            system=PLANNER_SYSTEM,
            max_tokens=8192,
            temperature=0.7,
        )
        logger.info(
            f"LLM responded: {response.total_tokens} tokens "
            f"(in={response.input_tokens}, out={response.output_tokens})"
        )

        # --- Step 4: parse response ---
        plan = self._parse_response(response.content, profile)

        # --- Step 5: post-validate training days count ---
        expected = profile.training_days_per_week
        actual = len(plan.training_days)
        if actual != expected:
            logger.warning(
                f"Training days mismatch: user requested {expected} but LLM generated {actual}. "
                "This is a known LLM compliance issue — consider retrying."
            )

        # --- Step 6: validate weekly volume and append warnings to coach_notes ---
        volume_warnings = self._validate_volume(plan, profile.experience_level)
        if volume_warnings:
            warning_text = (
                "📊 **周训练量提醒**（系统自动检测）\n"
                + "\n".join(volume_warnings)
                + "\n\n建议在上述不足的肌群对应训练日中额外补充1-2组复合动作。"
            )
            if plan.coach_notes:
                plan.coach_notes = plan.coach_notes + "\n\n" + warning_text
            else:
                plan.coach_notes = warning_text
            logger.info(f"Volume validation: {len(volume_warnings)} muscle group(s) below target.")
        else:
            logger.info("Volume validation: all muscle groups within target ranges.")

        logger.info(f"Plan generated: {plan.summary()}")
        return plan

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _count_weekly_sets(self, plan: WeeklyPlan) -> dict[str, int]:
        """
        Count direct working sets per primary muscle group across all training days.

        Uses the KB to resolve exercise_id → primary_muscles.
        Exercises not found in the KB (e.g. LLM hallucinations) are skipped.
        """
        counts: dict[str, int] = {}
        for day in plan.training_days:
            for ex_set in day.exercises:
                exercise = self.kb.get_exercise_by_id(ex_set.exercise_id)
                if exercise is None:
                    logger.debug(
                        f"_count_weekly_sets: exercise_id '{ex_set.exercise_id}' not in KB, skipping."
                    )
                    continue
                for muscle in exercise.primary_muscles:
                    muscle_id = muscle.value
                    counts[muscle_id] = counts.get(muscle_id, 0) + ex_set.sets
        return counts

    def _validate_volume(
        self, plan: WeeklyPlan, level: ExperienceLevel
    ) -> list[str]:
        """
        Return warning strings for muscle groups below their minimum weekly set target.

        Only major muscle groups with volume targets in the anatomy data are checked.
        Groups that are not trained at all (count=0) and have a target are flagged.
        Groups that are above the maximum are logged but not surfaced to the user.
        """
        targets = self.kb.get_volume_targets(level)
        counts = self._count_weekly_sets(plan)
        warnings: list[str] = []
        for muscle_id, (min_sets, max_sets) in targets.items():
            actual = counts.get(muscle_id, 0)
            if actual == 0:
                # skip muscles that are never primary targets (e.g. obliques at beginner level)
                continue
            if actual < min_sets:
                warnings.append(
                    f"- {muscle_id}：本周 {actual} 组，推荐最低 {min_sets} 组"
                )
            elif actual > max_sets:
                logger.debug(
                    f"Volume above max for {muscle_id}: {actual} > {max_sets}"
                )
        return warnings

    @staticmethod
    def _parse_contraindications(injuries: list[str]) -> list[ContraindicationTag]:
        """Convert raw injury strings to ContraindicationTag enum values (best-effort)."""
        tags: list[ContraindicationTag] = []
        valid = {t.value for t in ContraindicationTag}
        for inj in injuries:
            inj_norm = inj.strip().lower()
            if inj_norm in valid:
                tags.append(ContraindicationTag(inj_norm))
            else:
                logger.warning(f"Unknown contraindication tag ignored: {inj!r}")
        return tags

    @staticmethod
    def _patch_exercises(data: dict) -> dict:
        """Best-effort fill of missing exercise fields from exercise_id.

        LLMs occasionally omit ``exercise_name`` or ``exercise_name_zh``.
        Rather than crashing, we derive sensible defaults from the
        ``exercise_id`` (e.g. ``"dumbbell_curl"`` → ``"Dumbbell Curl"``).
        """
        for day in data.get("training_days", []):
            for ex in day.get("exercises", []):
                eid = ex.get("exercise_id", "")
                if "exercise_name" not in ex or not ex["exercise_name"]:
                    fallback = eid.replace("_", " ").title()
                    logger.warning(
                        f"Missing exercise_name for '{eid}' — using fallback: '{fallback}'"
                    )
                    ex["exercise_name"] = fallback
                if "exercise_name_zh" not in ex or not ex["exercise_name_zh"]:
                    # Use English name as fallback when Chinese name is missing
                    fallback = ex.get("exercise_name", eid.replace("_", " ").title())
                    logger.warning(
                        f"Missing exercise_name_zh for '{eid}' — using fallback: '{fallback}'"
                    )
                    ex["exercise_name_zh"] = fallback
        return data

    @staticmethod
    def _parse_response(raw: str, profile: UserProfile) -> WeeklyPlan:
        """
        Strip markdown fences (if any) and parse the LLM output into a WeeklyPlan.

        Falls back gracefully: if the top-level JSON is missing ``user_name``
        or ``goal``, they are filled from the profile.
        """
        text = raw.strip()

        # Strip ```json ... ``` or ``` ... ``` fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[1:end])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"LLM response is not valid JSON: {exc}\n\nRaw response:\n{raw[:500]}"
            ) from exc

        # Fill in fields the LLM might have omitted or got wrong
        data.setdefault("user_name", profile.name)
        data.setdefault("goal", profile.goal.value)
        data.setdefault("experience_level", profile.experience_level.value)

        # Patch missing exercise-level fields before validation
        PlannerAgent._patch_exercises(data)

        try:
            return WeeklyPlan.model_validate(data)
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse LLM output into WeeklyPlan: {exc}\n\n"
                f"Data keys: {list(data.keys())}"
            ) from exc
