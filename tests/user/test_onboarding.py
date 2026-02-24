"""
Tests for the user onboarding flow.

The onboarding module is IO-injectable (ask_fn / print_fn), so we can
simulate a complete terminal session without any real user input.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.user.models import UserProfile
from fitness_agent.user.onboarding import (
    _ask_choice,
    _ask_float,
    _ask_int,
    load_profile,
    run_onboarding,
    save_profile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inputs(*answers: str):
    """Return an ask_fn that yields the given answers in sequence."""
    it = iter(answers)
    def ask(prompt: str) -> str:  # noqa: ANN202
        return next(it)
    return ask


def _silent_print(*args, **kwargs) -> None:
    """Print function that discards all output."""


def _full_onboarding_inputs(
    name: str = "Alice",
    age: str = "28",
    gender_choice: str = "1",        # 男
    height: str = "168",
    weight: str = "62",
    goal_choice: str = "2",          # 增肌 (fat_loss="1", muscle_gain="2", ...)
    target_weight: str = "",         # only consumed when goal_choice == "1" (fat_loss)
    level_choice: str = "1",         # 新手
    activity_choice: str = "2",      # lightly_active
    training_days: str = "3",
    session_dur: str = "60",
    equipment_choice: str = "1",     # bodyweight only
    injuries: str = "",              # free text, empty = skip
    injury_confirm: str = "",        # Y/n confirm (only used when LLM parses)
    diet: str = "",
) -> tuple[str, ...]:
    inputs = [
        name,
        age,
        gender_choice,
        height,
        weight,
        goal_choice,
    ]
    # target_weight prompt only appears for fat_loss (choice "1").
    # After the P1 fix, muscle_gain and other goals skip this prompt entirely.
    if goal_choice == "1":
        inputs.append(target_weight)

    inputs += [
        level_choice,
        activity_choice,
        training_days,
        session_dur,
        equipment_choice,
        injuries,
    ]
    # Confirmation prompt only appears when injuries are non-empty AND llm_client is provided
    if injuries and injury_confirm is not None:
        inputs.append(injury_confirm)
    inputs.append(diet)
    return tuple(inputs)


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------

class TestAskChoice:
    def test_valid_single_choice(self) -> None:
        ask = _make_inputs("2")
        result = _ask_choice("Pick:", ["A", "B", "C"], ask, _silent_print)
        assert result == "B"

    def test_invalid_then_valid(self) -> None:
        ask = _make_inputs("0", "abc", "3")
        result = _ask_choice("Pick:", ["A", "B", "C"], ask, _silent_print)
        assert result == "C"

    def test_multiple_choice_returns_list(self) -> None:
        ask = _make_inputs("1,3")
        result = _ask_choice(
            "Pick:", ["A", "B", "C"], ask, _silent_print, allow_multiple=True
        )
        assert result == ["A", "C"]

    def test_multiple_choice_retries_on_empty(self) -> None:
        ask = _make_inputs("", "2")
        result = _ask_choice(
            "Pick:", ["A", "B", "C"], ask, _silent_print, allow_multiple=True
        )
        assert result == ["B"]


class TestAskFloat:
    def test_valid_input(self) -> None:
        ask = _make_inputs("170.5")
        result = _ask_float("Height:", ask, _silent_print, min_val=120, max_val=220)
        assert result == pytest.approx(170.5)

    def test_out_of_range_then_valid(self) -> None:
        ask = _make_inputs("50", "165")
        result = _ask_float("Height:", ask, _silent_print, min_val=120, max_val=220)
        assert result == 165.0

    def test_non_numeric_then_valid(self) -> None:
        ask = _make_inputs("abc", "175")
        result = _ask_float("Height:", ask, _silent_print, min_val=120, max_val=220)
        assert result == 175.0


class TestAskInt:
    def test_valid_integer(self) -> None:
        ask = _make_inputs("3")
        result = _ask_int("Days:", ask, _silent_print, min_val=1, max_val=6)
        assert result == 3

    def test_float_rejected(self) -> None:
        ask = _make_inputs("2.5", "4")
        result = _ask_int("Days:", ask, _silent_print, min_val=1, max_val=6)
        assert result == 4

    def test_out_of_range_rejected(self) -> None:
        ask = _make_inputs("7", "2")
        result = _ask_int("Days:", ask, _silent_print, min_val=1, max_val=6)
        assert result == 2


# ---------------------------------------------------------------------------
# Full onboarding flow tests
# ---------------------------------------------------------------------------

class TestRunOnboarding:
    def test_returns_user_profile(self) -> None:
        inputs = _full_onboarding_inputs()
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert isinstance(profile, UserProfile)

    def test_name_captured(self) -> None:
        inputs = _full_onboarding_inputs(name="Charlie")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.name == "Charlie"

    def test_age_captured(self) -> None:
        inputs = _full_onboarding_inputs(age="35")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.age == 35

    def test_gender_male(self) -> None:
        inputs = _full_onboarding_inputs(gender_choice="1")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.gender == "male"

    def test_gender_female(self) -> None:
        inputs = _full_onboarding_inputs(gender_choice="2")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.gender == "female"

    def test_goal_fat_loss(self) -> None:
        # goal_choice "1" → fat_loss (first in list)
        inputs = _full_onboarding_inputs(goal_choice="1", target_weight="55")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.goal == GoalType.fat_loss
        assert profile.target_weight_kg == 55.0

    def test_goal_muscle_gain(self) -> None:
        inputs = _full_onboarding_inputs(goal_choice="2", target_weight="")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.goal == GoalType.muscle_gain

    def test_computed_fields_filled(self) -> None:
        inputs = _full_onboarding_inputs()
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.bmr is not None
        assert profile.tdee is not None
        assert profile.daily_calorie_target is not None
        assert profile.daily_protein_target_g is not None

    def test_equipment_bodyweight_only(self) -> None:
        inputs = _full_onboarding_inputs(equipment_choice="1")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert Equipment.bodyweight in profile.available_equipment

    def test_training_days_captured(self) -> None:
        inputs = _full_onboarding_inputs(training_days="4")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.training_days_per_week == 4

    def test_injuries_captured_with_llm(self) -> None:
        """With a mock LLM client, free-text injuries are parsed and confirmed."""
        from fitness_agent.knowledge_base.models import ContraindicationTag
        from fitness_agent.utils.llm_client import LLMResponse

        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(
            content='["wrist_injury", "knee_injury"]',
            provider="mock", model="mock",
        )
        # injuries text + Y confirm
        inputs = _full_onboarding_inputs(injuries="手腕疼，膝盖不好", injury_confirm="")
        profile = run_onboarding(
            ask_fn=_make_inputs(*inputs),
            print_fn=_silent_print,
            llm_client=mock_client,
        )
        assert ContraindicationTag.wrist_injury in profile.injuries
        assert ContraindicationTag.knee_injury in profile.injuries

    def test_injuries_rejected_by_user(self) -> None:
        """User rejects LLM parsed injuries -> empty list."""
        from fitness_agent.utils.llm_client import LLMResponse

        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(
            content='["wrist_injury"]',
            provider="mock", model="mock",
        )
        inputs = _full_onboarding_inputs(injuries="手腕", injury_confirm="n")
        profile = run_onboarding(
            ask_fn=_make_inputs(*inputs),
            print_fn=_silent_print,
            llm_client=mock_client,
        )
        assert profile.injuries == []

    def test_no_injuries_empty_list(self) -> None:
        inputs = _full_onboarding_inputs(injuries="")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.injuries == []

    def test_injuries_skipped_without_llm(self) -> None:
        """Without LLM client, free-text injuries are skipped gracefully."""
        inputs = _full_onboarding_inputs(injuries="手腕疼", injury_confirm=None)
        # Remove the confirm step since no LLM = no confirm
        filtered = [i for i in inputs if i is not None]
        profile = run_onboarding(
            ask_fn=_make_inputs(*filtered),
            print_fn=_silent_print,
        )
        assert profile.injuries == []

    def test_dietary_restrictions_captured(self) -> None:
        inputs = _full_onboarding_inputs(diet="vegetarian")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert "vegetarian" in profile.dietary_restrictions

    def test_experience_level_beginner(self) -> None:
        inputs = _full_onboarding_inputs(level_choice="1")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.experience_level == ExperienceLevel.beginner

    def test_experience_level_intermediate(self) -> None:
        inputs = _full_onboarding_inputs(level_choice="2")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        assert profile.experience_level == ExperienceLevel.intermediate


# ---------------------------------------------------------------------------
# Profile persistence
# ---------------------------------------------------------------------------

class TestProfilePersistence:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        inputs = _full_onboarding_inputs(name="Roundtrip")
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)

        out_path = tmp_path / "profile.json"
        save_profile(profile, out_path)

        assert out_path.exists()
        loaded = load_profile(out_path)
        assert loaded.name == "Roundtrip"
        assert loaded.goal == profile.goal
        assert loaded.bmr == profile.bmr

    def test_saved_file_is_valid_json(self, tmp_path: Path) -> None:
        inputs = _full_onboarding_inputs()
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        out_path = tmp_path / "p.json"
        save_profile(profile, out_path)
        data = json.loads(out_path.read_text())
        assert "name" in data
        assert "goal" in data

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        inputs = _full_onboarding_inputs()
        profile = run_onboarding(ask_fn=_make_inputs(*inputs), print_fn=_silent_print)
        nested = tmp_path / "a" / "b" / "profile.json"
        save_profile(profile, nested)
        assert nested.exists()
