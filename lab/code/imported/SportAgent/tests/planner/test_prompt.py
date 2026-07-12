"""Tests for the planner prompt builder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.planner.prompt import PLANNER_SYSTEM, build_user_message
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile

_DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture()
def kb() -> KnowledgeBase:
    return KnowledgeBase(
        exercises_path=_DATA_DIR / "exercises.json",
        nutrition_path=_DATA_DIR / "nutrition.json",
        rules_path=_DATA_DIR / "rules.json",
        anatomy_path=_DATA_DIR / "anatomy.json",
        nutrition_principles_path=_DATA_DIR / "nutrition_principles.json",
    )


@pytest.fixture()
def profile() -> UserProfile:
    return enrich_profile(UserProfile(
        name="Eve",
        age=30,
        gender="female",
        height_cm=163,
        weight_kg=60,
        goal=GoalType.fat_loss,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=45,
        available_equipment=[Equipment.bodyweight, Equipment.dumbbell],
        activity_level="lightly_active",
    ))


class TestPlannerSystem:
    def test_system_prompt_nonempty(self) -> None:
        assert len(PLANNER_SYSTEM) > 100

    def test_system_prompt_mentions_json(self) -> None:
        assert "JSON" in PLANNER_SYSTEM

    def test_system_prompt_mentions_training_days(self) -> None:
        assert "training_days" in PLANNER_SYSTEM

    def test_system_prompt_notes_required(self) -> None:
        # notes must be clearly marked as required
        assert "notes" in PLANNER_SYSTEM
        assert "必填" in PLANNER_SYSTEM

    def test_system_prompt_mentions_pre_workout_meal(self) -> None:
        assert "pre_workout_meal" in PLANNER_SYSTEM

    def test_system_prompt_mentions_post_workout_meal(self) -> None:
        assert "post_workout_meal" in PLANNER_SYSTEM

    def test_system_prompt_mentions_meal_alternatives(self) -> None:
        assert "替换" in PLANNER_SYSTEM

    def test_system_prompt_mentions_volume_self_check(self) -> None:
        assert "周训练量" in PLANNER_SYSTEM


class TestBuildUserMessage:
    def test_contains_user_name(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        assert "Eve" in msg

    def test_contains_calorie_target(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        # :.0f formatting rounds, so use round() not int()
        assert str(round(profile.daily_calorie_target)) in msg

    def test_contains_protein_target(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        assert str(round(profile.daily_protein_target_g)) in msg

    def test_contains_exercise_pool_section(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        assert "可用动作库" in msg

    @staticmethod
    def _extract_pool_json(msg: str) -> list:
        """
        Extract the exercise pool JSON array from the user message.

        The pool section starts with "## 可用动作库" followed by a note line,
        then the JSON array. We find the '[' and use raw_decode() to parse
        just the JSON array without trailing text.
        """
        pool_part = msg.split("## 可用动作库", 1)[1]
        start = pool_part.index("[")
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(pool_part, start)
        return obj

    def test_exercise_pool_is_valid_json_array(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        parsed = self._extract_pool_json(msg)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_exercise_pool_entries_have_required_fields(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        entries = self._extract_pool_json(msg)
        for entry in entries:
            assert "id" in entry
            assert "name" in entry
            assert "name_zh" in entry

    def test_rules_section_included_when_rules_exist(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        # Rules section should be present if KB has applicable rules
        rules = kb.get_rules_for_context(goal=profile.goal, level=profile.experience_level)
        if rules:
            assert "训练规则" in msg

    def test_injuries_included_when_present(self, kb) -> None:
        profile_inj = enrich_profile(UserProfile(
            name="Frank",
            age=40,
            gender="male",
            height_cm=175,
            weight_kg=80,
            goal=GoalType.general_fitness,
            experience_level=ExperienceLevel.intermediate,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            injuries=["knee_injury", "lower_back_pain"],
            activity_level="sedentary",
        ))
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile_inj.available_equipment,
        )
        msg = build_user_message(profile_inj, kb, exercises)
        assert "knee_injury" in msg
        assert "lower_back_pain" in msg

    def test_empty_exercise_pool_produces_valid_message(self, kb, profile) -> None:
        msg = build_user_message(profile, kb, [])
        assert "Eve" in msg
        # Pool section should still exist, just with an empty array
        parsed = self._extract_pool_json(msg)
        assert parsed == []

    def test_strength_assessment_injected_when_set(self, kb) -> None:
        from fitness_agent.user.calculator import enrich_profile
        profile_with_strength = enrich_profile(UserProfile(
            name="Grace",
            age=25,
            gender="female",
            height_cm=165,
            weight_kg=58,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=45,
            available_equipment=[Equipment.bodyweight, Equipment.dumbbell],
            activity_level="lightly_active",
            strength_assessment="beginner_moderate",
        ))
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile_with_strength.available_equipment,
        )
        msg = build_user_message(profile_with_strength, kb, exercises)
        assert "beginner_moderate" in msg
        assert "weight_hint" in msg

    def test_preferred_training_time_injected_when_set(self, kb) -> None:
        from fitness_agent.user.calculator import enrich_profile
        profile_with_time = enrich_profile(UserProfile(
            name="Henry",
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=75,
            goal=GoalType.fat_loss,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=45,
            available_equipment=[Equipment.bodyweight],
            activity_level="sedentary",
            preferred_training_time="morning",
        ))
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile_with_time.available_equipment,
        )
        msg = build_user_message(profile_with_time, kb, exercises)
        assert "morning" in msg

    def test_strength_assessment_absent_when_not_set(self, kb, profile) -> None:
        # Default profile (fixture) has no strength_assessment
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        # "当前力量水平" line should not appear when field is None
        assert "当前力量水平:" not in msg
