"""
GYMAgent — orchestrates the gym training guidance generation pipeline:

  1. Extract training days from PlanAgent's WeeklyPlan
  2. Generate each training day incrementally (with context accumulation)
     a. Call LLM for personalised coaching tips, starting weights, etc.
     b. Deterministically inject KB cues, muscles, equipment
     c. Deterministically inject warmup/cooldown from templates
     d. Deterministically inject injury adaptations
     e. Validate exercise_ids exist in KB (retry if invalid)
  3. Generate 4-week progression table (separate LLM call)
  4. Validate session durations
  5. Assemble WeeklyGymPlan

The agent is deliberately stateless — each call is a fresh generation.
"""
from __future__ import annotations

import json

from fitness_agent.gym.models import (
    ExerciseGuidance,
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
from fitness_agent.utils.llm_client import BaseLLMClient, Message
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)


class GYMAgent:
    """
    AI gym coach that combines deterministic KB logic with LLM creativity.

    Parameters
    ----------
    client:
        Any ``BaseLLMClient`` instance.
    kb:
        Knowledge base providing exercises, warmup templates, and injury profiles.
    max_retries:
        Maximum number of additional LLM calls after the first attempt when
        exercise_id validation fails.
    """

    def __init__(
        self,
        client: BaseLLMClient,
        kb: KnowledgeBase,
        max_retries: int = 1,
    ) -> None:
        self.client = client
        self.kb = kb
        self.max_retries = max_retries

    # Duration estimation constants (seconds per set including rest)
    WARMUP_COOLDOWN_MINUTES = 15   # ~8 min warmup + ~7 min cooldown
    SECONDS_PER_SET_AVG = 90       # Avg work + rest per set

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def generate_gym_plan(
        self,
        weekly_plan: WeeklyPlan,
        profile: UserProfile,
    ) -> WeeklyGymPlan:
        """
        Generate a detailed weekly gym guidance plan from PlanAgent's WeeklyPlan.

        Follows the same incremental-context pattern as CookingAgent:
        each training day is generated in a separate LLM call, with all
        previously generated days injected as context.
        """
        training_days = weekly_plan.training_days
        if not training_days:
            raise ValueError("WeeklyPlan has no training days.")

        logger.info(
            f"GYMAgent: generating guidance for {len(training_days)} training days "
            f"(provider: {self.client.provider})"
        )

        # --- Step 1: Generate each session incrementally ---
        all_sessions: list[GymSessionPlan] = []
        for training_day in training_days:
            already_json: str | None = None
            if all_sessions:
                # Serialise sessions without KB-injected fields for a compact context
                already_json = json.dumps(
                    [self._session_to_compact_dict(s) for s in all_sessions],
                    ensure_ascii=False,
                    indent=2,
                )
            session = self._generate_session(
                profile, weekly_plan, training_day,
                already_generated_json=already_json,
            )
            all_sessions.append(session)

        # --- Step 2: Generate 4-week progression ---
        progression = self._generate_progression(profile, all_sessions)

        # --- Step 3: Validate durations ---
        duration_warnings = []
        for session in all_sessions:
            warnings = self._validate_duration(session, profile.session_duration_minutes)
            duration_warnings.extend(warnings)
        if duration_warnings:
            for w in duration_warnings:
                logger.warning(w)

        # --- Step 4: Assemble final plan ---
        # Aggregate equipment across all sessions
        all_equipment: set[str] = set()
        for session in all_sessions:
            all_equipment.update(session.equipment_needed)

        plan = WeeklyGymPlan(
            user_name=profile.name,
            sessions=all_sessions,
            four_week_progression=progression,
            general_tips_zh=self._build_general_tips(profile),
            equipment_checklist=sorted(all_equipment),
        )

        logger.info(f"GYMAgent plan generated: {plan.summary()}")
        return plan

    # ------------------------------------------------------------------
    # Single-session generation (incremental context)
    # ------------------------------------------------------------------

    def _generate_session(
        self,
        profile: UserProfile,
        weekly_plan: WeeklyPlan,
        training_day: TrainingDay,
        already_generated_json: str | None = None,
    ) -> GymSessionPlan:
        """Call the LLM to generate guidance for a single training day.

        After LLM response, deterministically inject:
        - KB cues (exercise.cues)
        - KB muscles and equipment
        - Warmup/cooldown templates
        - Injury adaptations
        - Video URLs from KB
        """
        user_message = build_gym_user_message(
            profile, weekly_plan, training_day, self.kb,
            already_generated_json=already_generated_json,
        )

        messages: list[Message] = [Message(role="user", content=user_message)]
        result: GymSessionPlan | None = None

        for attempt in range(self.max_retries + 1):
            logger.info(
                f"Calling {self.client.provider}/{self.client.model} "
                f"for day {training_day.day_label} "
                f"(attempt {attempt + 1}/{self.max_retries + 1})..."
            )
            response = self.client.chat(
                messages=messages,
                system=GYM_SYSTEM,
                max_tokens=4096,
                temperature=0.7,
            )
            logger.info(
                f"LLM responded: {response.total_tokens} tokens "
                f"(in={response.input_tokens}, out={response.output_tokens})"
            )

            # Parse response
            result = self._parse_session_response(
                response.content, training_day.day_label
            )

            # Deterministic post-processing
            self._inject_kb_data(result)
            self._inject_warmup_cooldown(result, training_day, profile)
            self._inject_injury_adaptations(result, profile)

            # Validate exercise_ids
            invalid_ids = self._validate_exercise_ids(result)

            if not invalid_ids:
                logger.info(f"Day {training_day.day_label}: validation passed.")
                break

            logger.info(
                f"Day {training_day.day_label}: {len(invalid_ids)} invalid exercise_id(s) "
                f"(attempt {attempt + 1}/{self.max_retries + 1})."
            )

            if attempt < self.max_retries:
                messages.append(Message(role="assistant", content=response.content))
                correction = self._build_exercise_id_correction(invalid_ids)
                messages.append(Message(role="user", content=correction))

        assert result is not None
        return result

    # ------------------------------------------------------------------
    # 4-week progression generation
    # ------------------------------------------------------------------

    def _generate_progression(
        self,
        profile: UserProfile,
        sessions: list[GymSessionPlan],
    ) -> list[ProgressionWeek]:
        """Generate the 4-week progression plan with a separate LLM call."""
        sessions_json = json.dumps(
            [self._session_to_compact_dict(s) for s in sessions],
            ensure_ascii=False,
            indent=2,
        )

        user_message = build_gym_progression_message(profile, sessions_json)

        logger.info(
            f"Calling {self.client.provider}/{self.client.model} "
            f"for 4-week progression..."
        )
        response = self.client.chat(
            messages=[Message(role="user", content=user_message)],
            system=GYM_PROGRESSION_SYSTEM,
            max_tokens=2048,
            temperature=0.5,
        )
        logger.info(
            f"Progression LLM responded: {response.total_tokens} tokens "
            f"(in={response.input_tokens}, out={response.output_tokens})"
        )

        return self._parse_progression_response(response.content)

    # ------------------------------------------------------------------
    # Deterministic KB injection
    # ------------------------------------------------------------------

    def _inject_kb_data(self, session: GymSessionPlan) -> None:
        """Inject KB cues, muscles, equipment, video URLs into exercises."""
        for eg in session.exercises:
            kb_ex = self.kb.get_exercise_by_id(eg.exercise_id)
            if kb_ex is None:
                continue

            # Inject KB cues
            eg.kb_cues = list(kb_ex.cues) if kb_ex.cues else []

            # Inject muscles
            eg.primary_muscles = [m.value for m in kb_ex.primary_muscles]
            eg.secondary_muscles = [m.value for m in kb_ex.secondary_muscles]

            # Inject equipment
            eg.equipment = [e.value for e in kb_ex.equipment]

            # Inject video URL from KB if available and LLM didn't provide one
            if kb_ex.video_url and not eg.video_url:
                eg.video_url = kb_ex.video_url

            # If KB has breathing pattern and LLM's is generic, prefer KB
            if kb_ex.breathing_pattern_zh and not eg.breathing_zh:
                eg.breathing_zh = kb_ex.breathing_pattern_zh

    def _inject_warmup_cooldown(
        self,
        session: GymSessionPlan,
        training_day: TrainingDay,
        profile: UserProfile,
    ) -> None:
        """Inject warmup/cooldown sequences from KB templates.

        Matches template by extracting movement patterns from the day's exercises.
        """
        # Collect movement patterns from KB for each exercise in the session
        movement_patterns: set[str] = set()
        for eg in session.exercises:
            kb_ex = self.kb.get_exercise_by_id(eg.exercise_id)
            if kb_ex is not None:
                movement_patterns.add(kb_ex.movement_pattern.value)

        if not movement_patterns:
            return

        template = self.kb.get_warmup_template(list(movement_patterns))
        if template is None:
            return

        session.warmup_sequence = list(template.warmup_sequence)
        session.cooldown_sequence = list(template.cooldown_sequence)

        # Inject injury-specific warmup modifications
        if profile.injuries and template.injury_modifications:
            mods: dict[str, str] = {}
            for injury in profile.injuries:
                tag_value = injury.value
                if tag_value in template.injury_modifications:
                    mods[tag_value] = template.injury_modifications[tag_value]
            session.warmup_injury_modifications = mods

    def _inject_injury_adaptations(
        self,
        session: GymSessionPlan,
        profile: UserProfile,
    ) -> None:
        """Inject injury adaptation notes from KB injury_profiles.

        For each exercise, check if any of its contraindication tags overlap
        with the user's injuries. If so, look up the injury profile and inject
        the relevant modification guidance.
        """
        if not profile.injuries:
            return

        user_injury_set = set(profile.injuries)

        for eg in session.exercises:
            kb_ex = self.kb.get_exercise_by_id(eg.exercise_id)
            if kb_ex is None:
                continue

            # Find overlapping injuries for this exercise
            exercise_contras = set(kb_ex.contraindications)
            overlapping = user_injury_set & exercise_contras

            if not overlapping and eg.injury_adaptations_zh:
                # LLM already provided adaptations, keep them
                continue

            if overlapping:
                # Build adaptation text from KB injury profiles
                adaptation_parts: list[str] = []
                for injury_tag in overlapping:
                    ip = self.kb.get_injury_profile(injury_tag)
                    if ip is None:
                        continue
                    # Check if this exercise's movement pattern needs modification
                    if kb_ex.movement_pattern.value in ip.modify_movement_patterns:
                        mod = ip.modify_movement_patterns[kb_ex.movement_pattern.value]
                        adaptation_parts.append(f"{ip.name_zh}: {mod}")
                    elif kb_ex.movement_pattern.value in ip.avoid_movement_patterns:
                        adaptation_parts.append(
                            f"{ip.name_zh}: 此动作模式应避免，请考虑替代动作"
                        )

                if adaptation_parts:
                    kb_adaptation = "；".join(adaptation_parts)
                    if eg.injury_adaptations_zh:
                        # Append KB info to LLM's adaptation
                        eg.injury_adaptations_zh += f"（KB补充：{kb_adaptation}）"
                    else:
                        eg.injury_adaptations_zh = kb_adaptation

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_exercise_ids(self, session: GymSessionPlan) -> list[str]:
        """Validate all exercise_ids exist in KB. Returns list of invalid IDs."""
        invalid: list[str] = []
        for eg in session.exercises:
            if self.kb.get_exercise_by_id(eg.exercise_id) is None:
                invalid.append(eg.exercise_id)
        return invalid

    def _validate_duration(
        self, session: GymSessionPlan, target_minutes: int
    ) -> list[str]:
        """Estimate session duration and compare to target. Returns warnings."""
        total_sets = sum(eg.sets for eg in session.exercises)
        estimated = (
            self.WARMUP_COOLDOWN_MINUTES
            + total_sets * self.SECONDS_PER_SET_AVG / 60
        )
        warnings: list[str] = []

        # Allow ±30% tolerance
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

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_session_response(raw: str, expected_day_label: str) -> GymSessionPlan:
        """Parse a single GymSessionPlan from the LLM's raw text response."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            )

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"LLM gym session response is not valid JSON: {exc}\n\n"
                f"Raw response:\n{raw[:500]}"
            ) from exc

        # Support wrapped format
        if isinstance(data, dict) and "sessions" in data:
            sessions = data["sessions"]
            if sessions:
                data = sessions[0]
        elif isinstance(data, list):
            if data:
                data = data[0]

        # Remove KB-injected fields if LLM erroneously included them
        # (they will be re-injected deterministically)
        for ex_data in data.get("exercises", []):
            for field in ("warmup_sequence", "cooldown_sequence",
                          "warmup_injury_modifications"):
                data.pop(field, None)
            for field in ("primary_muscles", "secondary_muscles",
                          "equipment", "kb_cues"):
                ex_data.pop(field, None)

        try:
            return GymSessionPlan.model_validate(data)
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse GymSessionPlan for {expected_day_label}: {exc}\n\n"
                f"Keys present: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            ) from exc

    @staticmethod
    def _parse_progression_response(raw: str) -> list[ProgressionWeek]:
        """Parse 4 ProgressionWeek objects from the LLM response."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            )

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"LLM progression response is not valid JSON: {exc}\n\n"
                f"Raw response:\n{raw[:500]}"
            ) from exc

        # Handle wrapper
        if isinstance(data, dict):
            data = data.get("four_week_progression", data.get("progression", []))

        if not isinstance(data, list):
            raise RuntimeError(
                f"Expected a JSON array for progression, got {type(data)}"
            )

        try:
            weeks = [ProgressionWeek.model_validate(w) for w in data]
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse ProgressionWeek list: {exc}"
            ) from exc

        if len(weeks) != 4:
            logger.warning(
                f"Expected 4 progression weeks, got {len(weeks)}. "
                f"Padding or truncating."
            )
            # Pad with defaults if too few
            while len(weeks) < 4:
                weeks.append(ProgressionWeek(
                    week_number=len(weeks) + 1,
                    theme_zh="调整周",
                    volume_change_zh="维持当前训练量",
                    intensity_change_zh="维持当前强度",
                    rpe_target="RPE 7",
                    notes_zh="根据身体状态调整",
                ))
            weeks = weeks[:4]

        return weeks

    # ------------------------------------------------------------------
    # Correction message builder
    # ------------------------------------------------------------------

    def _build_exercise_id_correction(self, invalid_ids: list[str]) -> str:
        """Build a correction message for invalid exercise_ids."""
        valid_ids = sorted(ex.id for ex in self.kb.exercises)
        return (
            f"以下 exercise_id 不在知识库中，请替换为有效的 ID：\n\n"
            f"【无效 ID】\n" + "\n".join(f"- {eid}" for eid in invalid_ids) + "\n\n"
            f"【有效 exercise_id 列表（部分）】\n"
            + ", ".join(valid_ids[:50]) + "\n\n"
            "调整要求：\n"
            "- 将无效 exercise_id 替换为语义最接近的有效 ID\n"
            "- 保持动作名称与新 ID 一致\n"
            "- 返回完整修正后的 JSON"
        )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def _session_to_compact_dict(session: GymSessionPlan) -> dict:
        """Convert a session to a compact dict for context injection.

        Excludes warmup/cooldown (KB-injected) and detailed KB data
        to keep the context small.
        """
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

    @staticmethod
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
                f"注意：您有 {injury_names} 相关问题，"
                f"训练中如有不适请立即停止并咨询专业人士。"
            )

        tips.append("组间休息时保持活动（轻微走动），避免完全静止。")
        tips.append("训练期间保持充足水分摄入（每 15-20 分钟小口饮水）。")
        tips.append("记录每次训练的重量和次数，以便追踪进步。")

        return "\n".join(f"- {t}" for t in tips)
