"""
Output data models for the GYM training guidance plan.

These structured results are produced by GYMAgent to enrich
PlanAgent's training plan with detailed exercise guidance,
warmup/cooldown sequences, injury adaptations, and progression.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Exercise-level guidance
# ---------------------------------------------------------------------------


class ExerciseGuidance(BaseModel):
    """Detailed execution guidance for a single exercise."""

    exercise_id: str = Field(
        description="Snake-case ID matching the knowledge base (e.g. 'barbell_squat').",
    )
    exercise_name_zh: str = Field(description="Chinese exercise name.")
    exercise_name: str = Field(description="English exercise name.")
    sets: int = Field(ge=1, le=10, description="Number of sets.")
    reps: str = Field(
        description="Rep range or duration (e.g. '8-12', '30s', 'AMRAP').",
    )
    rest_seconds: int = Field(
        ge=0, le=300, description="Rest between sets in seconds.",
    )

    # --- From KB (deterministic injection) ---
    primary_muscles: list[str] = Field(
        default_factory=list,
        description="Primary target muscles from KB.",
    )
    secondary_muscles: list[str] = Field(
        default_factory=list,
        description="Secondary muscles from KB.",
    )
    equipment: list[str] = Field(
        default_factory=list,
        description="Equipment options from KB.",
    )
    kb_cues: list[str] = Field(
        default_factory=list,
        description="Base form cues from exercises.json.",
    )

    # --- From LLM (creative generation) ---
    coaching_tips_zh: list[str] = Field(
        min_length=1,
        description="2-3 personalised coaching tips (beyond KB cues).",
    )
    starting_weight_zh: str = Field(
        description="Starting weight recommendation, e.g. '从 10kg 哑铃开始'.",
    )
    breathing_zh: str = Field(
        description="Breathing pattern, e.g. '下降时吸气，推起时呼气'.",
    )
    common_mistakes_zh: list[str] = Field(
        min_length=1,
        description="At least 1 common mistake to avoid.",
    )
    tempo_zh: Optional[str] = Field(
        default=None,
        description="Movement tempo: eccentric-pause-concentric, e.g. '3-1-2'.",
    )

    # --- Injury-related (KB + LLM hybrid) ---
    injury_adaptations_zh: Optional[str] = Field(
        default=None,
        description="Injury-specific adaptation notes if user has relevant injuries.",
    )

    # --- Optional extensions ---
    video_url: Optional[str] = Field(
        default=None,
        description="Tutorial video URL (Bilibili / YouTube).",
    )
    superset_with: Optional[str] = Field(
        default=None,
        description="Exercise ID for superset pairing.",
    )


# ---------------------------------------------------------------------------
# Session-level plan (one training day)
# ---------------------------------------------------------------------------


class GymSessionPlan(BaseModel):
    """Complete training card for a single training day."""

    day_label: str = Field(
        description="Day label, e.g. '周一 (Day 1)'.",
    )
    focus: str = Field(
        description="Session focus, e.g. '上肢推力'.",
    )
    is_training_day: bool = Field(
        default=True,
        description="Always True for gym sessions.",
    )
    estimated_duration_minutes: int = Field(
        ge=20, le=180,
        description="Estimated total session duration including warmup/cooldown.",
    )

    # --- Warmup / cooldown (KB deterministic injection) ---
    warmup_sequence: list[str] = Field(
        default_factory=list,
        description="Ordered warmup steps from KB warmup_templates.",
    )
    cooldown_sequence: list[str] = Field(
        default_factory=list,
        description="Ordered cooldown/stretch steps from KB warmup_templates.",
    )
    warmup_injury_modifications: dict[str, str] = Field(
        default_factory=dict,
        description="Injury tag → modification note from KB warmup_templates.",
    )

    # --- Exercises (LLM + KB) ---
    exercises: list[ExerciseGuidance] = Field(
        min_length=1,
        description="Detailed guidance for each exercise in execution order.",
    )

    # --- LLM generated ---
    session_flow_notes_zh: str = Field(
        default="",
        description="General session flow advice (rest management, superset tips).",
    )
    equipment_needed: list[str] = Field(
        default_factory=list,
        description="Equipment needed for this session.",
    )


# ---------------------------------------------------------------------------
# 4-week progression
# ---------------------------------------------------------------------------


class ProgressionWeek(BaseModel):
    """One week within a 4-week progression plan."""

    week_number: int = Field(ge=1, le=4, description="Week number (1-4).")
    theme_zh: str = Field(
        description="Week theme, e.g. '适应期' / '渐进期' / '强化期' / '减量周'.",
    )
    volume_change_zh: str = Field(
        description="Volume adjustment, e.g. '与第一周相同' / '每个动作 +1 组'.",
    )
    intensity_change_zh: str = Field(
        description="Intensity adjustment, e.g. '重量不变' / '+2.5kg 或 +5%'.",
    )
    rpe_target: str = Field(
        description="Target RPE range, e.g. 'RPE 6-7'.",
    )
    notes_zh: str = Field(
        default="",
        description="Additional notes for this week.",
    )


# ---------------------------------------------------------------------------
# Top-level weekly gym plan
# ---------------------------------------------------------------------------


class WeeklyGymPlan(BaseModel):
    """
    Complete weekly gym training guidance plan.

    Produced by GYMAgent from PlanAgent's WeeklyPlan.
    """

    user_name: str = Field(description="User's name.")
    sessions: list[GymSessionPlan] = Field(
        min_length=1,
        description="Training sessions (one per training day).",
    )
    four_week_progression: list[ProgressionWeek] = Field(
        min_length=4,
        max_length=4,
        description="Exactly 4 weeks of progression parameters.",
    )
    general_tips_zh: str = Field(
        default="",
        description="General training tips and advice.",
    )
    equipment_checklist: list[str] = Field(
        default_factory=list,
        description="Aggregated equipment needed for the entire week.",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Plan generation timestamp.",
    )

    def summary(self) -> str:
        """Return a short human-readable summary string."""
        n_sessions = len(self.sessions)
        total_exercises = sum(len(s.exercises) for s in self.sessions)
        return (
            f"{self.user_name} | {n_sessions} training sessions | "
            f"{total_exercises} exercises | 4-week progression"
        )
