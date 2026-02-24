"""
Output data models for the weekly fitness plan.

These are the structured results produced by PlannerAgent.
All fields are Pydantic v2 BaseModel so the plan can be
serialised to JSON, stored, and loaded back.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from fitness_agent.knowledge_base.models import GoalType


# ---------------------------------------------------------------------------
# Exercise-level detail inside a training day
# ---------------------------------------------------------------------------

class ExerciseSet(BaseModel):
    """A single exercise entry within a training session."""

    exercise_id: str = Field(
        description="Snake-case ID matching the knowledge base entry (e.g. 'push_up').",
    )
    exercise_name: str = Field(
        description="English exercise name.",
    )
    exercise_name_zh: str = Field(
        description="Chinese exercise name.",
    )
    sets: int = Field(ge=1, le=10, description="Number of sets.")
    reps: str = Field(
        description="Rep range or duration (e.g. '8-12', '30s', 'AMRAP').",
    )
    rest_seconds: int = Field(
        ge=0,
        le=300,
        description="Rest between sets in seconds.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional coaching notes, form cues, or substitution hints.",
    )


# ---------------------------------------------------------------------------
# A single training day
# ---------------------------------------------------------------------------

class TrainingDay(BaseModel):
    """One structured training session within the week."""

    day_label: str = Field(
        description="Label for the training day (e.g. 'Day 1', 'Monday', 'Push A').",
    )
    focus: str = Field(
        description="Session focus description (e.g. 'Upper body push', 'Full body strength').",
    )
    exercises: list[ExerciseSet] = Field(
        min_length=1,
        description="Ordered list of exercises for this session.",
    )
    estimated_duration_minutes: int = Field(
        ge=20,
        le=180,
        description="Estimated session duration in minutes.",
    )
    warmup_notes: Optional[str] = Field(
        default=None,
        description="Warm-up recommendations for this session.",
    )
    cooldown_notes: Optional[str] = Field(
        default=None,
        description="Cool-down / stretch recommendations for this session.",
    )


# ---------------------------------------------------------------------------
# Daily nutrition guidance
# ---------------------------------------------------------------------------

class DailyNutrition(BaseModel):
    """Nutrition targets and meal suggestions for a single day."""

    calorie_target: float = Field(ge=800, description="Daily calorie target (kcal).")
    protein_g: float = Field(ge=0, description="Daily protein target (g).")
    carbs_g: float = Field(ge=0, description="Estimated carbohydrate target (g).")
    fat_g: float = Field(ge=0, description="Estimated fat target (g).")
    meal_suggestions: list[str] = Field(
        default_factory=list,
        description="3-5 meal ideas or food suggestions for the day.",
    )
    supplements: list[str] = Field(
        default_factory=list,
        description="Optional supplement recommendations.",
    )


# ---------------------------------------------------------------------------
# Top-level plan
# ---------------------------------------------------------------------------

class WeeklyPlan(BaseModel):
    """
    Full personalised weekly training + nutrition plan.

    Produced by PlannerAgent and ready to display or store.
    """

    user_name: str = Field(description="User's name, for personalisation.")
    goal: GoalType = Field(description="Primary fitness goal.")
    experience_level: str = Field(
        description="User's experience level (beginner / intermediate / advanced).",
    )
    training_days: list[TrainingDay] = Field(
        min_length=1,
        description="Ordered training sessions for the week.",
    )
    rest_days: list[str] = Field(
        default_factory=list,
        description="Rest or active-recovery day labels (e.g. ['Day 4', 'Day 7']).",
    )
    daily_nutrition: DailyNutrition = Field(
        description="Nutrition targets (same every day for simplicity in V1).",
    )
    coach_notes: str = Field(
        default="",
        description="General coaching advice, progression tips, and encouragement.",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Plan generation timestamp.",
    )

    def summary(self) -> str:
        """Return a short human-readable summary string."""
        n_train = len(self.training_days)
        return (
            f"{self.user_name} | {self.goal.value} | "
            f"{n_train} training days | "
            f"{self.daily_nutrition.calorie_target:.0f} kcal/day | "
            f"{self.daily_nutrition.protein_g:.0f}g protein"
        )
