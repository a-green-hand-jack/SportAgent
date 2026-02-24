"""Tests for planner output data models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from fitness_agent.knowledge_base.models import GoalType
from fitness_agent.planner.models import (
    DailyNutrition,
    ExerciseSet,
    TrainingDay,
    WeeklyPlan,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _exercise_set(**kw) -> dict:
    defaults = dict(
        exercise_id="push_up",
        exercise_name="Push Up",
        exercise_name_zh="俯卧撑",
        sets=3,
        reps="10-15",
        rest_seconds=60,
    )
    defaults.update(kw)
    return defaults


def _training_day(**kw) -> dict:
    defaults = dict(
        day_label="Day 1",
        focus="Upper body push",
        exercises=[_exercise_set()],
        estimated_duration_minutes=45,
    )
    defaults.update(kw)
    return defaults


def _daily_nutrition(**kw) -> dict:
    defaults = dict(
        calorie_target=2000,
        protein_g=150,
        carbs_g=200,
        fat_g=60,
    )
    defaults.update(kw)
    return defaults


def _weekly_plan(**kw) -> dict:
    defaults = dict(
        user_name="Alice",
        goal="muscle_gain",
        experience_level="beginner",
        training_days=[_training_day()],
        daily_nutrition=_daily_nutrition(),
    )
    defaults.update(kw)
    return defaults


# ---------------------------------------------------------------------------
# ExerciseSet
# ---------------------------------------------------------------------------

class TestExerciseSet:
    def test_valid_entry(self) -> None:
        ex = ExerciseSet(**_exercise_set())
        assert ex.exercise_id == "push_up"
        assert ex.sets == 3
        assert ex.notes is None

    def test_with_notes(self) -> None:
        ex = ExerciseSet(**_exercise_set(notes="Focus on chest squeeze"))
        assert ex.notes == "Focus on chest squeeze"

    def test_sets_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ExerciseSet(**_exercise_set(sets=0))
        with pytest.raises(ValidationError):
            ExerciseSet(**_exercise_set(sets=11))

    def test_rest_seconds_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ExerciseSet(**_exercise_set(rest_seconds=-1))
        with pytest.raises(ValidationError):
            ExerciseSet(**_exercise_set(rest_seconds=301))

    def test_duration_string_reps(self) -> None:
        ex = ExerciseSet(**_exercise_set(reps="30s"))
        assert ex.reps == "30s"

    def test_amrap_reps(self) -> None:
        ex = ExerciseSet(**_exercise_set(reps="AMRAP"))
        assert ex.reps == "AMRAP"


# ---------------------------------------------------------------------------
# TrainingDay
# ---------------------------------------------------------------------------

class TestTrainingDay:
    def test_valid_day(self) -> None:
        day = TrainingDay(**_training_day())
        assert day.day_label == "Day 1"
        assert len(day.exercises) == 1

    def test_multiple_exercises(self) -> None:
        day = TrainingDay(**_training_day(exercises=[
            _exercise_set(exercise_id="push_up"),
            _exercise_set(exercise_id="pull_up", exercise_name="Pull Up",
                          exercise_name_zh="引体向上"),
        ]))
        assert len(day.exercises) == 2

    def test_empty_exercises_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TrainingDay(**_training_day(exercises=[]))

    def test_duration_bounds(self) -> None:
        with pytest.raises(ValidationError):
            TrainingDay(**_training_day(estimated_duration_minutes=10))
        with pytest.raises(ValidationError):
            TrainingDay(**_training_day(estimated_duration_minutes=200))

    def test_optional_warmup_cooldown(self) -> None:
        day = TrainingDay(**_training_day(
            warmup_notes="5 min jog",
            cooldown_notes="Stretch quads",
        ))
        assert day.warmup_notes == "5 min jog"
        assert day.cooldown_notes == "Stretch quads"


# ---------------------------------------------------------------------------
# DailyNutrition
# ---------------------------------------------------------------------------

class TestDailyNutrition:
    def test_valid_nutrition(self) -> None:
        nut = DailyNutrition(**_daily_nutrition())
        assert nut.calorie_target == 2000
        assert nut.meal_suggestions == []
        assert nut.supplements == []

    def test_with_meal_suggestions(self) -> None:
        nut = DailyNutrition(**_daily_nutrition(
            meal_suggestions=["早餐: 燕麦+鸡蛋", "午餐: 鸡胸肉+米饭"],
        ))
        assert len(nut.meal_suggestions) == 2

    def test_low_calorie_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DailyNutrition(**_daily_nutrition(calorie_target=500))


# ---------------------------------------------------------------------------
# WeeklyPlan
# ---------------------------------------------------------------------------

class TestWeeklyPlan:
    def test_valid_plan(self) -> None:
        plan = WeeklyPlan(**_weekly_plan())
        assert plan.user_name == "Alice"
        assert plan.goal == GoalType.muscle_gain
        assert len(plan.training_days) == 1

    def test_empty_training_days_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WeeklyPlan(**_weekly_plan(training_days=[]))

    def test_rest_days_default_empty(self) -> None:
        plan = WeeklyPlan(**_weekly_plan())
        assert plan.rest_days == []

    def test_with_rest_days(self) -> None:
        plan = WeeklyPlan(**_weekly_plan(rest_days=["Day 4", "Day 7"]))
        assert "Day 4" in plan.rest_days

    def test_coach_notes_default_empty(self) -> None:
        plan = WeeklyPlan(**_weekly_plan())
        assert plan.coach_notes == ""

    def test_created_at_set_automatically(self) -> None:
        plan = WeeklyPlan(**_weekly_plan())
        assert plan.created_at is not None

    def test_summary_contains_key_info(self) -> None:
        plan = WeeklyPlan(**_weekly_plan())
        summary = plan.summary()
        assert "Alice" in summary
        assert "muscle_gain" in summary
        assert "1 training days" in summary

    def test_goal_enum_validation(self) -> None:
        with pytest.raises(ValidationError):
            WeeklyPlan(**_weekly_plan(goal="invalid_goal"))

    def test_multiple_training_days(self) -> None:
        plan = WeeklyPlan(**_weekly_plan(training_days=[
            _training_day(day_label="Day 1"),
            _training_day(day_label="Day 2"),
            _training_day(day_label="Day 3"),
        ]))
        assert len(plan.training_days) == 3
        assert plan.summary().startswith("Alice")
