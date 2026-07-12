"""Tests for the LLM-based free-text injury parser."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fitness_agent.knowledge_base.models import ContraindicationTag
from fitness_agent.utils.llm_client import LLMResponse
from fitness_agent.utils.text_parser import (
    format_injuries_for_display,
    parse_injuries_with_llm,
)


# ---------------------------------------------------------------------------
# parse_injuries_with_llm
# ---------------------------------------------------------------------------

class TestParseInjuriesWithLLM:
    def _make_client(self, response_content: str) -> MagicMock:
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content=response_content,
            provider="mock",
            model="mock",
        )
        return client

    def test_single_injury(self) -> None:
        client = self._make_client('["wrist_injury"]')
        result = parse_injuries_with_llm("手腕疼", client)
        assert result == [ContraindicationTag.wrist_injury]

    def test_multiple_injuries(self) -> None:
        client = self._make_client('["knee_injury", "lower_back_pain"]')
        result = parse_injuries_with_llm("膝盖和腰都不好", client)
        assert ContraindicationTag.knee_injury in result
        assert ContraindicationTag.lower_back_pain in result

    def test_empty_input_returns_empty(self) -> None:
        client = self._make_client("[]")
        result = parse_injuries_with_llm("", client)
        assert result == []
        # Should not call LLM for empty input
        client.chat.assert_not_called()

    def test_no_match_returns_empty(self) -> None:
        client = self._make_client("[]")
        result = parse_injuries_with_llm("我很健康", client)
        assert result == []

    def test_unknown_tag_ignored(self) -> None:
        client = self._make_client('["wrist_injury", "broken_spine"]')
        result = parse_injuries_with_llm("手腕和脊柱", client)
        assert result == [ContraindicationTag.wrist_injury]

    def test_llm_returns_non_list(self) -> None:
        client = self._make_client('"wrist_injury"')
        result = parse_injuries_with_llm("手腕", client)
        assert result == []

    def test_llm_returns_invalid_json(self) -> None:
        client = self._make_client("not json at all")
        result = parse_injuries_with_llm("手腕", client)
        assert result == []

    def test_llm_exception_returns_empty(self) -> None:
        client = MagicMock()
        client.chat.side_effect = RuntimeError("API down")
        result = parse_injuries_with_llm("手腕", client)
        assert result == []

    def test_markdown_fences_stripped(self) -> None:
        client = self._make_client('```json\n["wrist_injury"]\n```')
        result = parse_injuries_with_llm("手腕", client)
        assert result == [ContraindicationTag.wrist_injury]


# ---------------------------------------------------------------------------
# format_injuries_for_display
# ---------------------------------------------------------------------------

class TestFormatInjuriesForDisplay:
    def test_empty_list(self) -> None:
        assert format_injuries_for_display([]) == "无"

    def test_single_tag(self) -> None:
        result = format_injuries_for_display([ContraindicationTag.wrist_injury])
        assert "手腕" in result
        assert "wrist_injury" in result

    def test_multiple_tags(self) -> None:
        tags = [ContraindicationTag.wrist_injury, ContraindicationTag.knee_injury]
        result = format_injuries_for_display(tags)
        assert "、" in result  # Chinese separator
        assert "wrist_injury" in result
        assert "knee_injury" in result
