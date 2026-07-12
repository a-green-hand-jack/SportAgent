"""Tests for gym output models (Pydantic validation)."""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from fitness_agent.gym.models import (
    ExerciseGuidance,
    GymSessionPlan,
    ProgressionWeek,
    WeeklyGymPlan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_exercise_guidance(
    exercise_id: str = "push_up",
    name_zh: str = "俯卧撑",
    name: str = "Push Up",
    sets: int = 3,
    reps: str = "10-12",
) -> dict:
    return {
        "exercise_id": exercise_id,
        "exercise_name_zh": name_zh,
        "exercise_name": name,
        "sets": sets,
        "reps": reps,
        "rest_seconds": 60,
        "coaching_tips_zh": ["保持核心收紧", "手指朝前"],
        "starting_weight_zh": "徒手开始",
        "breathing_zh": "下降时吸气，推起时呼气",
        "common_mistakes_zh": ["塌腰"],
    }


def _make_session(
    day_label: str = "周一 (Day 1)",
    focus: str = "上肢推力",
    n_exercises: int = 3,
) -> dict:
    exercises = [
        _make_exercise_guidance(exercise_id=f"ex_{i}")
        for i in range(n_exercises)
    ]
    return {
        "day_label": day_label,
        "focus": focus,
        "estimated_duration_minutes": 60,
        "exercises": exercises,
    }


def _make_progression_week(week: int = 1) -> dict:
    themes = {1: "适应期", 2: "渐进期", 3: "强化期", 4: "减量周"}
    return {
        "week_number": week,
        "theme_zh": themes.get(week, "调整周"),
        "volume_change_zh": "按计划执行",
        "intensity_change_zh": "维持当前强度",
        "rpe_target": f"RPE {5 + week}",
        "notes_zh": "注意动作质量",
    }


# ---------------------------------------------------------------------------
# ExerciseGuidance tests
# ---------------------------------------------------------------------------

class TestExerciseGuidance:
    def test_valid_exercise_guidance(self) -> None:
        eg = ExerciseGuidance.model_validate(_make_exercise_guidance())
        assert eg.exercise_id == "push_up"
        assert eg.exercise_name_zh == "俯卧撑"
        assert len(eg.coaching_tips_zh) == 2
        assert eg.breathing_zh != ""
        assert eg.video_url is None

    def test_missing_coaching_tips_fails(self) -> None:
        data = _make_exercise_guidance()
        data["coaching_tips_zh"] = []
        with pytest.raises(ValidationError):
            ExerciseGuidance.model_validate(data)

    def test_missing_common_mistakes_fails(self) -> None:
        data = _make_exercise_guidance()
        data["common_mistakes_zh"] = []
        with pytest.raises(ValidationError):
            ExerciseGuidance.model_validate(data)

    def test_sets_bounds(self) -> None:
        data = _make_exercise_guidance()
        data["sets"] = 0
        with pytest.raises(ValidationError):
            ExerciseGuidance.model_validate(data)

        data["sets"] = 11
        with pytest.raises(ValidationError):
            ExerciseGuidance.model_validate(data)

    def test_optional_fields_default_none(self) -> None:
        eg = ExerciseGuidance.model_validate(_make_exercise_guidance())
        assert eg.tempo_zh is None
        assert eg.injury_adaptations_zh is None
        assert eg.superset_with is None

    def test_kb_fields_default_empty(self) -> None:
        eg = ExerciseGuidance.model_validate(_make_exercise_guidance())
        assert eg.primary_muscles == []
        assert eg.secondary_muscles == []
        assert eg.equipment == []
        assert eg.kb_cues == []


# ---------------------------------------------------------------------------
# GymSessionPlan tests
# ---------------------------------------------------------------------------

class TestGymSessionPlan:
    def test_valid_session(self) -> None:
        session = GymSessionPlan.model_validate(_make_session())
        assert session.day_label == "周一 (Day 1)"
        assert len(session.exercises) == 3
        assert session.is_training_day is True

    def test_empty_exercises_fails(self) -> None:
        data = _make_session()
        data["exercises"] = []
        with pytest.raises(ValidationError):
            GymSessionPlan.model_validate(data)

    def test_duration_bounds(self) -> None:
        data = _make_session()
        data["estimated_duration_minutes"] = 10  # below 20
        with pytest.raises(ValidationError):
            GymSessionPlan.model_validate(data)

    def test_warmup_fields_default_empty(self) -> None:
        session = GymSessionPlan.model_validate(_make_session())
        assert session.warmup_sequence == []
        assert session.cooldown_sequence == []
        assert session.warmup_injury_modifications == {}


# ---------------------------------------------------------------------------
# ProgressionWeek tests
# ---------------------------------------------------------------------------

class TestProgressionWeek:
    def test_valid_week(self) -> None:
        pw = ProgressionWeek.model_validate(_make_progression_week(1))
        assert pw.week_number == 1
        assert pw.theme_zh == "适应期"

    def test_week_number_bounds(self) -> None:
        data = _make_progression_week(1)
        data["week_number"] = 0
        with pytest.raises(ValidationError):
            ProgressionWeek.model_validate(data)

        data["week_number"] = 5
        with pytest.raises(ValidationError):
            ProgressionWeek.model_validate(data)

    def test_exercise_specific_default_empty(self) -> None:
        pw = ProgressionWeek.model_validate(_make_progression_week(1))
        assert pw.exercise_specific_zh == []

    def test_exercise_specific_with_data(self) -> None:
        data = _make_progression_week(2)
        data["exercise_specific_zh"] = [
            "深蹲: 20kg→22.5kg",
            "卧推: 保持+1组",
        ]
        pw = ProgressionWeek.model_validate(data)
        assert len(pw.exercise_specific_zh) == 2
        assert "深蹲" in pw.exercise_specific_zh[0]


# ---------------------------------------------------------------------------
# WeeklyGymPlan tests
# ---------------------------------------------------------------------------

class TestWeeklyGymPlan:
    def test_valid_plan(self) -> None:
        sessions = [_make_session(day_label=f"Day {i+1}") for i in range(3)]
        progression = [_make_progression_week(w) for w in range(1, 5)]
        plan = WeeklyGymPlan.model_validate({
            "user_name": "TestUser",
            "sessions": sessions,
            "four_week_progression": progression,
        })
        assert plan.user_name == "TestUser"
        assert len(plan.sessions) == 3
        assert len(plan.four_week_progression) == 4

    def test_progression_must_be_4(self) -> None:
        sessions = [_make_session()]
        # Only 3 weeks
        progression = [_make_progression_week(w) for w in range(1, 4)]
        with pytest.raises(ValidationError):
            WeeklyGymPlan.model_validate({
                "user_name": "TestUser",
                "sessions": sessions,
                "four_week_progression": progression,
            })

    def test_summary(self) -> None:
        sessions = [_make_session(n_exercises=4), _make_session(n_exercises=3)]
        progression = [_make_progression_week(w) for w in range(1, 5)]
        plan = WeeklyGymPlan.model_validate({
            "user_name": "Bob",
            "sessions": sessions,
            "four_week_progression": progression,
        })
        s = plan.summary()
        assert "Bob" in s
        assert "2 training sessions" in s
        assert "7 exercises" in s

    def test_json_round_trip(self) -> None:
        sessions = [_make_session()]
        progression = [_make_progression_week(w) for w in range(1, 5)]
        plan = WeeklyGymPlan.model_validate({
            "user_name": "RoundTrip",
            "sessions": sessions,
            "four_week_progression": progression,
        })
        data = json.loads(plan.model_dump_json())
        plan2 = WeeklyGymPlan.model_validate(data)
        assert plan2.user_name == plan.user_name
        assert len(plan2.sessions) == len(plan.sessions)
