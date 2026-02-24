"""Tests for UserProfile model."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    ExperienceLevel,
    GoalType,
)
from fitness_agent.user.models import UserProfile


def make_profile(**overrides) -> UserProfile:
    """Helper: build a valid UserProfile with sensible defaults."""
    defaults = dict(
        name="Test User",
        age=28,
        gender="male",
        height_cm=175.0,
        weight_kg=75.0,
        goal=GoalType.muscle_gain,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=60,
        available_equipment=[Equipment.dumbbell, Equipment.bodyweight],
    )
    defaults.update(overrides)
    return UserProfile(**defaults)


class TestUserProfileCreation:
    def test_minimal_valid_profile(self) -> None:
        profile = make_profile()
        assert profile.name == "Test User"
        assert profile.goal == GoalType.muscle_gain

    def test_default_optional_fields(self) -> None:
        profile = make_profile()
        assert profile.injuries == []
        assert profile.dietary_restrictions == []
        assert profile.activity_level == "lightly_active"
        assert profile.target_weight_kg is None
        assert profile.bmr is None
        assert profile.tdee is None
        assert profile.daily_calorie_target is None
        assert profile.daily_protein_target_g is None

    def test_datetime_defaults(self) -> None:
        before = datetime.now()
        profile = make_profile()
        after = datetime.now()
        assert before <= profile.created_at <= after
        assert before <= profile.updated_at <= after

    def test_all_goal_types(self) -> None:
        for goal in GoalType:
            profile = make_profile(goal=goal)
            assert profile.goal == goal

    def test_all_experience_levels(self) -> None:
        for level in ExperienceLevel:
            profile = make_profile(experience_level=level)
            assert profile.experience_level == level

    def test_with_injuries(self) -> None:
        profile = make_profile(
            injuries=[ContraindicationTag.knee_injury, ContraindicationTag.shoulder_injury]
        )
        assert ContraindicationTag.knee_injury in profile.injuries
        assert len(profile.injuries) == 2

    def test_with_dietary_restrictions(self) -> None:
        profile = make_profile(dietary_restrictions=["vegetarian", "no_pork"])
        assert "vegetarian" in profile.dietary_restrictions

    def test_computed_fields_can_be_set(self) -> None:
        profile = make_profile(
            bmr=1800.0,
            tdee=2300.0,
            daily_calorie_target=2500.0,
            daily_protein_target_g=150.0,
        )
        assert profile.bmr == 1800.0
        assert profile.tdee == 2300.0
        assert profile.daily_calorie_target == 2500.0
        assert profile.daily_protein_target_g == 150.0

    def test_all_equipment_types(self) -> None:
        all_equipment = list(Equipment)
        profile = make_profile(available_equipment=all_equipment)
        assert len(profile.available_equipment) == len(all_equipment)


class TestUserProfileValidation:
    def test_age_too_young(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(age=13)

    def test_age_too_old(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(age=81)

    def test_age_boundary_valid(self) -> None:
        assert make_profile(age=14).age == 14
        assert make_profile(age=80).age == 80

    def test_height_too_short(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(height_cm=119.0)

    def test_height_too_tall(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(height_cm=221.0)

    def test_weight_too_light(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(weight_kg=29.0)

    def test_weight_too_heavy(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(weight_kg=201.0)

    def test_training_days_zero(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(training_days_per_week=0)

    def test_training_days_too_many(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(training_days_per_week=7)

    def test_training_days_boundary_valid(self) -> None:
        assert make_profile(training_days_per_week=1).training_days_per_week == 1
        assert make_profile(training_days_per_week=6).training_days_per_week == 6

    def test_session_too_short(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(session_duration_minutes=19)

    def test_session_too_long(self) -> None:
        with pytest.raises(ValidationError):
            make_profile(session_duration_minutes=181)

    def test_session_boundary_valid(self) -> None:
        assert make_profile(session_duration_minutes=20).session_duration_minutes == 20
        assert make_profile(session_duration_minutes=180).session_duration_minutes == 180


class TestUserProfileSerialization:
    def test_round_trip_json(self) -> None:
        original = make_profile(
            injuries=[ContraindicationTag.knee_injury],
            bmr=1750.0,
            tdee=2200.0,
        )
        json_str = original.model_dump_json()
        restored = UserProfile.model_validate_json(json_str)
        assert restored.name == original.name
        assert restored.injuries == original.injuries
        assert restored.bmr == original.bmr

    def test_model_dump_excludes_none_optionally(self) -> None:
        profile = make_profile()
        data = profile.model_dump(exclude_none=True)
        assert "bmr" not in data
        assert "tdee" not in data
        assert "target_weight_kg" not in data
