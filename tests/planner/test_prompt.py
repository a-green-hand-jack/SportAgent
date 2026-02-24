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

    def test_exercise_pool_is_valid_json_array(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)

        # Extract the JSON portion after the "## 可用动作库" header
        pool_section = msg.split("## 可用动作库\n\n", 1)[1]
        # The JSON block ends before the next section (if any)
        pool_json = pool_section.split("\n\n")[0]
        parsed = json.loads(pool_json)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_exercise_pool_entries_have_required_fields(self, kb, profile) -> None:
        exercises = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=profile.available_equipment,
        )
        msg = build_user_message(profile, kb, exercises)
        pool_section = msg.split("## 可用动作库\n\n", 1)[1]
        pool_json = pool_section.split("\n\n")[0]
        entries = json.loads(pool_json)
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
        pool_section = msg.split("## 可用动作库\n\n", 1)[1]
        pool_json = pool_section.split("\n\n")[0]
        parsed = json.loads(pool_json)
        assert parsed == []
