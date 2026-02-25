"""
PlannerAgent — orchestrates the full planning pipeline:

  1. Deterministic KB filtering (safety + equipment)
  2. Build structured LLM prompt (user context + rules + exercise pool)
  3. Call LLM and parse the JSON response into a WeeklyPlan
  4. Validate weekly volume; retry with correction message if below target

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

# Maps fine-grained MuscleGroup values → anatomy.json parent IDs for volume validation.
# Muscles without anatomy targets (forearms, hip_flexors, adductors, full_body) are
# intentionally omitted — they pass through unchanged and are simply not checked.
MUSCLE_ROLLUP: dict[str, str] = {
    "back": "lats",
    "front_delt": "shoulders",
    "side_delt": "shoulders",
    "rear_delt": "shoulders",
    "abs": "core",
    "obliques": "core",
}


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
    max_retries:
        Maximum number of additional LLM calls after the first attempt when
        volume validation fails. Total calls = max_retries + 1.
    """

    def __init__(
        self,
        client: BaseLLMClient,
        kb: KnowledgeBase,
        max_exercises_in_pool: int = 60,
        max_retries: int = 2,
    ) -> None:
        self.client = client
        self.kb = kb
        self.max_exercises_in_pool = max_exercises_in_pool
        self.max_retries = max_retries

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

        # --- Step 3: LLM call with generate-validate-fix retry loop ---
        messages: list[Message] = [Message(role="user", content=user_message)]
        plan: WeeklyPlan | None = None
        volume_warnings: list[str] = []

        for attempt in range(self.max_retries + 1):
            logger.info(
                f"Calling {self.client.provider}/{self.client.model} for plan generation "
                f"(attempt {attempt + 1}/{self.max_retries + 1})…"
            )
            response = self.client.chat(
                messages=messages,
                system=PLANNER_SYSTEM,
                max_tokens=8192,
                temperature=0.7,
            )
            logger.info(
                f"LLM responded: {response.total_tokens} tokens "
                f"(in={response.input_tokens}, out={response.output_tokens})"
            )

            plan = self._parse_response(response.content, profile)

            # Post-validate training days count (existing behavior preserved)
            expected = profile.training_days_per_week
            actual = len(plan.training_days)
            if actual != expected:
                logger.warning(
                    f"Training days mismatch: user requested {expected} but LLM generated {actual}. "
                    "This is a known LLM compliance issue — consider retrying."
                )

            # Validate weekly volume
            volume_warnings = self._validate_volume(plan, profile.experience_level)
            if not volume_warnings:
                logger.info("Volume validation: all muscle groups within target ranges.")
                break

            logger.info(
                f"Volume validation: {len(volume_warnings)} muscle group(s) below target "
                f"(attempt {attempt + 1}/{self.max_retries + 1})."
            )

            if attempt < self.max_retries:
                messages.append(Message(role="assistant", content=response.content))
                correction = self._build_correction_message(volume_warnings)
                messages.append(Message(role="user", content=correction))
                logger.debug(f"Retry {attempt + 1}: appended correction message.")

        # After all attempts: append remaining warnings to coach_notes
        assert plan is not None
        if volume_warnings:
            warning_text = (
                "📊 **周训练量提醒**（系统自动检测）\n"
                + "\n".join(volume_warnings)
                + "\n\n建议在上述不足的肌群对应训练日中额外补充1-2组复合动作。"
            )
            plan.coach_notes = (
                (plan.coach_notes + "\n\n" + warning_text) if plan.coach_notes else warning_text
            )
            logger.info(
                f"Volume warnings appended to coach_notes after {self.max_retries + 1} attempt(s)."
            )

        logger.info(f"Plan generated: {plan.summary()}")
        return plan

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _count_weekly_sets(self, plan: WeeklyPlan) -> dict[str, int]:
        """
        Count effective working sets per anatomy muscle group across all training days.

        Primary muscles are counted at full coefficient (1.0).
        Secondary muscles are counted at half coefficient (0.5).
        Fine-grained muscle names (e.g. 'back', 'front_delt') are rolled up
        to their anatomy parent group via the module-level MUSCLE_ROLLUP map.
        Exercises not found in the KB (e.g. LLM hallucinations) are skipped.
        """
        raw_counts: dict[str, float] = {}
        for day in plan.training_days:
            for ex_set in day.exercises:
                exercise = self.kb.get_exercise_by_id(ex_set.exercise_id)
                if exercise is None:
                    logger.debug(
                        f"_count_weekly_sets: exercise_id '{ex_set.exercise_id}' not in KB, skipping."
                    )
                    continue
                # Primary muscles — full coefficient
                for muscle in exercise.primary_muscles:
                    muscle_id = MUSCLE_ROLLUP.get(muscle.value, muscle.value)
                    raw_counts[muscle_id] = raw_counts.get(muscle_id, 0.0) + ex_set.sets
                # Secondary muscles — 0.5 coefficient
                for muscle in exercise.secondary_muscles:
                    muscle_id = MUSCLE_ROLLUP.get(muscle.value, muscle.value)
                    raw_counts[muscle_id] = raw_counts.get(muscle_id, 0.0) + ex_set.sets * 0.5
        return {k: round(v) for k, v in raw_counts.items()}

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
    def _build_correction_message(warnings: list[str]) -> str:
        """Build a follow-up user message asking the LLM to fix volume deficiencies."""
        joined = "\n".join(warnings)
        return (
            f"以下主要肌群的周训练量不足，请调整计划：\n"
            f"{joined}\n\n"
            "调整要求：\n"
            "- 不要改变训练日数量或整体训练结构\n"
            "- 在对应训练日增加 1-2 组针对该肌群的复合动作\n"
            "- 保持每日总训练时长在合理范围内\n"
            "- 返回完整修正后的 JSON 计划（格式与之前相同，不要有任何额外文字）"
        )

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
