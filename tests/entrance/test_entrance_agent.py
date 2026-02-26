"""
Unit tests for EntranceAgent.

All LLM calls are mocked so no real API keys are required.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fitness_agent.entrance.agent import (
    EntranceAgent,
    _build_required_fields,
    _is_complete,
    _parse_turn,
)
from fitness_agent.utils.llm_client import BaseLLMClient, LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQ_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "onboarding_requirements.json"

# A minimal valid profile dict (all core fields filled)
_CORE_PROFILE: dict = {
    "name": "Test User",
    "age": 28,
    "gender": "male",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "goal": "muscle_gain",
    "experience_level": "beginner",
    "training_days_per_week": 3,
    "session_duration_minutes": 60,
    "available_equipment": ["dumbbell", "bodyweight"],
    "activity_level": "lightly_active",
}

_CORE_WITH_COOK: dict = {**_CORE_PROFILE, "dietary_restrictions": []}

_CORE_WITH_GYM: dict = {
    **_CORE_PROFILE,
    "injuries": [],
    "strength_assessment": "beginner_light",
    "preferred_training_time": "evening",
}

_FULL_PROFILE: dict = {
    **_CORE_PROFILE,
    "dietary_restrictions": [],
    "injuries": [],
    "strength_assessment": "beginner_light",
    "preferred_training_time": "evening",
}


def _make_llm_response(reply: str, extracted: dict) -> LLMResponse:
    """Build a mock LLMResponse with dual-output JSON content."""
    content = json.dumps({"reply": reply, "extracted": extracted}, ensure_ascii=False)
    return LLMResponse(content=content, provider="mock", model="mock-model")


def _make_mock_client(*responses: LLMResponse) -> BaseLLMClient:
    """Return a mock BaseLLMClient that yields the given responses in sequence."""
    mock = MagicMock(spec=BaseLLMClient)
    mock.chat.side_effect = list(responses)
    mock.provider = "mock"
    mock.model = "mock-model"
    return mock


# ---------------------------------------------------------------------------
# _parse_turn tests
# ---------------------------------------------------------------------------


class TestParseTurn:
    def test_valid_json(self) -> None:
        raw = json.dumps({"reply": "Hello!", "extracted": {"age": 28}})
        result = _parse_turn(raw)
        assert result.reply == "Hello!"
        assert result.extracted == {"age": 28}

    def test_empty_extracted(self) -> None:
        raw = json.dumps({"reply": "Got it.", "extracted": {}})
        result = _parse_turn(raw)
        assert result.reply == "Got it."
        assert result.extracted == {}

    def test_markdown_code_fence(self) -> None:
        raw = textwrap.dedent("""\
            ```json
            {"reply": "Hi", "extracted": {"name": "Alice"}}
            ```""")
        result = _parse_turn(raw)
        assert result.reply == "Hi"
        assert result.extracted == {"name": "Alice"}

    def test_fallback_on_invalid_json(self) -> None:
        raw = "This is not JSON at all"
        result = _parse_turn(raw)
        assert result.reply == raw
        assert result.extracted == {}

    def test_fallback_when_extracted_not_dict(self) -> None:
        raw = json.dumps({"reply": "Hi", "extracted": ["not", "a", "dict"]})
        result = _parse_turn(raw)
        assert result.reply == "Hi"
        assert result.extracted == {}


# ---------------------------------------------------------------------------
# _is_complete tests
# ---------------------------------------------------------------------------


class TestIsComplete:
    def test_complete(self) -> None:
        assert _is_complete({"a": 1, "b": 2}, ["a", "b"]) is True

    def test_incomplete(self) -> None:
        assert _is_complete({"a": 1}, ["a", "b"]) is False

    def test_empty_required(self) -> None:
        assert _is_complete({}, []) is True

    def test_extra_fields_ok(self) -> None:
        assert _is_complete({"a": 1, "b": 2, "c": 3}, ["a", "b"]) is True


# ---------------------------------------------------------------------------
# _build_required_fields tests
# ---------------------------------------------------------------------------


class TestBuildRequiredFields:
    def _load_req(self) -> dict:
        return json.loads(REQ_PATH.read_text(encoding="utf-8"))

    def test_core_only(self) -> None:
        req = self._load_req()
        fields = _build_required_fields(req, should_cook=False, should_gym=False)
        assert "name" in fields
        assert "goal" in fields
        assert "dietary_restrictions" not in fields
        assert "injuries" not in fields

    def test_with_cook(self) -> None:
        req = self._load_req()
        fields = _build_required_fields(req, should_cook=True, should_gym=False)
        assert "dietary_restrictions" in fields
        assert "injuries" not in fields

    def test_with_gym(self) -> None:
        req = self._load_req()
        fields = _build_required_fields(req, should_cook=False, should_gym=True)
        assert "injuries" in fields
        assert "strength_assessment" in fields
        assert "preferred_training_time" in fields
        assert "dietary_restrictions" not in fields

    def test_with_both(self) -> None:
        req = self._load_req()
        fields = _build_required_fields(req, should_cook=True, should_gym=True)
        assert "dietary_restrictions" in fields
        assert "injuries" in fields

    def test_no_duplicates(self) -> None:
        req = self._load_req()
        fields = _build_required_fields(req, should_cook=True, should_gym=True)
        assert len(fields) == len(set(fields))


# ---------------------------------------------------------------------------
# EntranceAgent integration tests (mock LLM)
# ---------------------------------------------------------------------------


class TestEntranceAgent:
    """Tests that mock the LLM to verify the dialogue loop logic."""

    def test_collects_core_profile(self) -> None:
        """Agent should return a valid UserProfile when all core fields are collected."""
        # Greeting response
        greeting_resp = _make_llm_response("你好！请告诉我你的基本信息。", {})
        # Single turn that provides all core fields at once
        turn_resp = _make_llm_response("收到！已为你记录所有信息。", _CORE_PROFILE)

        client = _make_mock_client(greeting_resp, turn_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        user_msg = "28岁男，175cm，70kg，增肌，新手，3次/周，60min，哑铃自重，轻度活跃"
        inputs = iter([user_msg])
        printed: list[str] = []

        profile = agent.run(
            ask_fn=lambda _: next(inputs),
            print_fn=printed.append,
            should_cook=False,
            should_gym=False,
        )

        assert profile.name == "Test User"
        assert profile.age == 28
        assert profile.gender == "male"
        assert profile.bmr is not None and profile.bmr > 0
        assert profile.tdee is not None and profile.tdee > profile.bmr

    def test_cooking_fields_when_should_cook(self) -> None:
        """should_cook=True should include dietary_restrictions in required fields."""
        greeting_resp = _make_llm_response("你好！", {})
        turn_resp = _make_llm_response("好的！", _CORE_WITH_COOK)

        client = _make_mock_client(greeting_resp, turn_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        inputs = iter(["所有信息"])
        profile = agent.run(
            ask_fn=lambda _: next(inputs),
            print_fn=lambda _: None,
            should_cook=True,
            should_gym=False,
        )

        assert profile.dietary_restrictions == []

    def test_gym_fields_when_should_gym(self) -> None:
        """should_gym=True should collect injuries, strength_assessment, preferred_training_time."""
        greeting_resp = _make_llm_response("你好！", {})
        turn_resp = _make_llm_response("已记录！", _CORE_WITH_GYM)

        client = _make_mock_client(greeting_resp, turn_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        inputs = iter(["所有信息"])
        profile = agent.run(
            ask_fn=lambda _: next(inputs),
            print_fn=lambda _: None,
            should_cook=False,
            should_gym=True,
        )

        assert profile.injuries == []
        assert profile.strength_assessment == "beginner_light"
        assert profile.preferred_training_time == "evening"

    def test_injury_mapping(self) -> None:
        """LLM should map '腰痛' to lower_back_pain (tested via extracted dict)."""
        greeting_resp = _make_llm_response("你好！", {})
        # First turn: core fields without injuries
        core_no_inj = {k: v for k, v in _CORE_WITH_GYM.items() if k != "injuries"}
        turn1_resp = _make_llm_response("还需要了解伤病信息。", core_no_inj)
        # Second turn: injury extracted from "腰痛"
        turn2_resp = _make_llm_response(
            "好的，已记录你的腰部伤病。", {"injuries": ["lower_back_pain"]}
        )

        client = _make_mock_client(greeting_resp, turn1_resp, turn2_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        inputs = iter(["基本信息", "腰痛"])
        profile = agent.run(
            ask_fn=lambda _: next(inputs),
            print_fn=lambda _: None,
            should_cook=False,
            should_gym=True,
        )

        from fitness_agent.knowledge_base.models import ContraindicationTag

        assert ContraindicationTag.lower_back_pain in profile.injuries

    def test_partial_extraction_continues(self) -> None:
        """Agent should keep looping when not all fields are collected yet."""
        greeting_resp = _make_llm_response("你好！", {})
        # Turn 1: only name and age
        turn1_resp = _make_llm_response("好的！还需要更多信息。", {"name": "Alice", "age": 25})
        # Turn 2: remaining core fields
        remaining = {k: v for k, v in _CORE_PROFILE.items() if k not in ("name", "age")}
        turn2_resp = _make_llm_response("信息收集完毕！", remaining)

        client = _make_mock_client(greeting_resp, turn1_resp, turn2_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        inputs = iter(["我叫Alice，25岁", "其余信息"])
        call_count = 0

        def counting_ask(_: str) -> str:
            nonlocal call_count
            call_count += 1
            return next(inputs)

        profile = agent.run(
            ask_fn=counting_ask,
            print_fn=lambda _: None,
            should_cook=False,
            should_gym=False,
        )

        assert profile.name == "Alice"
        assert profile.age == 25
        assert call_count == 2  # Two user inputs were needed

    def test_pydantic_rejects_invalid_age(self) -> None:
        """If LLM extracts an invalid age, UserProfile.model_validate should raise."""
        from pydantic import ValidationError

        greeting_resp = _make_llm_response("你好！", {})
        bad_profile = {**_CORE_PROFILE, "age": 200}  # age > 80 is invalid
        turn_resp = _make_llm_response("好的！", bad_profile)

        client = _make_mock_client(greeting_resp, turn_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        inputs = iter(["所有信息"])
        with pytest.raises(ValidationError):
            agent.run(
                ask_fn=lambda _: next(inputs),
                print_fn=lambda _: None,
                should_cook=False,
                should_gym=False,
            )

    def test_empty_input_skipped(self) -> None:
        """Empty user inputs should be skipped without calling the LLM."""
        greeting_resp = _make_llm_response("你好！", {})
        turn_resp = _make_llm_response("完成！", _CORE_PROFILE)

        client = _make_mock_client(greeting_resp, turn_resp)
        agent = EntranceAgent(client=client, requirements_path=REQ_PATH)

        # First two inputs are empty, third has all data
        inputs = iter(["", "   ", "实际内容"])
        agent.run(
            ask_fn=lambda _: next(inputs),
            print_fn=lambda _: None,
            should_cook=False,
            should_gym=False,
        )

        # LLM.chat should be called exactly twice: greeting + one real turn
        assert client.chat.call_count == 2
