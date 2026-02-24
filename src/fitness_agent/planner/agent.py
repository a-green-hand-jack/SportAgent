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
from fitness_agent.knowledge_base.models import ContraindicationTag, Equipment
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
            max_tokens=4096,
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

        logger.info(f"Plan generated: {plan.summary()}")
        return plan

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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

        try:
            return WeeklyPlan.model_validate(data)
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse LLM output into WeeklyPlan: {exc}\n\n"
                f"Data keys: {list(data.keys())}"
            ) from exc
