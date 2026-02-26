"""
EntranceAgent — LLM-driven conversational user profile collection.

Replaces the static form-based ``run_onboarding()`` with a multi-turn
dialogue where the LLM extracts structured fields from free-form user input.

Each LLM turn returns a dual-output JSON:
    {"reply": "<message to user>", "extracted": {<field: value>}}

The agent continues until all required fields are collected (or MAX_TURNS
is reached), then validates the collected data via ``UserProfile.model_validate()``
and enriches it with BMR/TDEE calculations.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fitness_agent.entrance.prompt import build_system_prompt
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import BaseLLMClient, Message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

AskFn = Callable[[str], str]
PrintFn = Callable[..., None]

# ---------------------------------------------------------------------------
# Default requirements file path
# ---------------------------------------------------------------------------

_DEFAULT_REQ_PATH = (
    Path(__file__).parent.parent.parent.parent / "data" / "raw" / "onboarding_requirements.json"
)


# ---------------------------------------------------------------------------
# TurnResult dataclass
# ---------------------------------------------------------------------------


@dataclass
class TurnResult:
    reply: str
    extracted: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_requirements(path: Path) -> dict:  # type: ignore[type-arg]
    """Load onboarding_requirements.json."""
    data: dict = json.loads(path.read_text(encoding="utf-8"))
    return data


def _build_required_fields(requirements: dict, should_cook: bool, should_gym: bool) -> list[str]:
    """Assemble the list of required fields based on which downstream agents are enabled."""
    fields: list[str] = list(requirements["core"]["fields"])
    if should_cook:
        fields.extend(requirements["cooking"]["fields"])
    if should_gym:
        fields.extend(requirements["gym"]["fields"])
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for f in fields:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def _is_complete(partial_profile: dict, required_fields: list[str]) -> bool:
    """Return True if all required fields have been collected."""
    return all(f in partial_profile for f in required_fields)


def _parse_turn(raw: str) -> TurnResult:
    """
    Parse the LLM's dual-output JSON response.

    Expected format:
        {"reply": "...", "extracted": {...}}

    Falls back to TurnResult(reply=raw, extracted={}) on any parse error,
    so the conversation can continue gracefully.
    """
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening fence line (```json or ```)
        start = 1
        # Remove closing fence line if present
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end]).strip()

    try:
        data = json.loads(text)
        reply = str(data.get("reply", raw))
        extracted = data.get("extracted", {})
        if not isinstance(extracted, dict):
            extracted = {}
        return TurnResult(reply=reply, extracted=extracted)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(f"EntranceAgent: failed to parse turn JSON: {exc!r}. Raw: {raw[:200]!r}")
        return TurnResult(reply=raw, extracted={})


def _save_conversation_log(
    path: Path,
    messages: list[Message],
    required_fields: list[str],
    partial_profile: dict,  # type: ignore[type-arg]
) -> None:
    """Persist the full conversation to a JSON file for debugging."""
    path.parent.mkdir(parents=True, exist_ok=True)
    log = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "required_fields": required_fields,
        "collected": partial_profile,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug(f"EntranceAgent: conversation log saved to {path}")


def _generate_greeting(client: BaseLLMClient, required_fields: list[str]) -> str:
    """
    Ask the LLM to generate an opening greeting message.

    The LLM is asked to produce the greeting in the standard dual-output format;
    we only use the ``reply`` field.
    """
    system = build_system_prompt(required_fields, {})
    trigger = Message(
        role="user",
        content="请你先向用户打招呼，并开始收集信息。",
    )
    response = client.chat(
        messages=[trigger],
        system=system,
        max_tokens=512,
        temperature=0.7,
    )
    result = _parse_turn(response.content)
    return result.reply


# ---------------------------------------------------------------------------
# EntranceAgent
# ---------------------------------------------------------------------------


class EntranceAgent:
    """
    LLM-driven conversational agent for collecting user profile information.

    Usage::

        agent = EntranceAgent(client=llm_client)
        profile = agent.run(
            ask_fn=lambda _: input("> "),
            print_fn=print,
            should_cook=True,
            should_gym=True,
        )
    """

    MAX_TURNS: int = 15

    def __init__(
        self,
        client: BaseLLMClient,
        requirements_path: Path | None = None,
    ) -> None:
        self.client = client
        req_path = requirements_path or _DEFAULT_REQ_PATH
        self._requirements = _load_requirements(req_path)

    def run(
        self,
        ask_fn: AskFn,
        print_fn: PrintFn,
        should_cook: bool = False,
        should_gym: bool = False,
        conversation_log_path: Path | None = None,
    ) -> UserProfile:
        """
        Run the conversational onboarding loop.

        Parameters
        ----------
        ask_fn:                Callable that prompts the user and returns their input string.
        print_fn:              Callable used to display messages to the user.
        should_cook:           Whether the CookingAgent will be used (adds dietary fields).
        should_gym:            Whether the GYMAgent will be used (adds injury/strength fields).
        conversation_log_path: Optional path to save the full conversation as JSON (for debugging).
                               Parent directories are created automatically if needed.

        Returns
        -------
        A fully-enriched ``UserProfile`` (BMR/TDEE calculated).
        """
        required_fields = _build_required_fields(self._requirements, should_cook, should_gym)
        messages: list[Message] = []
        partial_profile: dict = {}

        # --- 1. LLM generates the opening greeting ---
        try:
            greeting = _generate_greeting(self.client, required_fields)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"EntranceAgent: greeting generation failed: {exc!r}")
            greeting = (
                "你好！我是你的 AI 健身教练助手。请告诉我你的基本信息，我将为你定制个人健身计划。"
            )

        print_fn(greeting)

        # Record the greeting as the first assistant message so the conversation
        # history is coherent for subsequent turns.
        messages.append(Message(role="assistant", content=greeting))

        # --- 2. Conversation loop ---
        for turn in range(self.MAX_TURNS):
            if _is_complete(partial_profile, required_fields):
                logger.debug(f"EntranceAgent: all fields collected after {turn} turns.")
                break

            # Get user input
            try:
                user_input = ask_fn("> ").strip()
            except (KeyboardInterrupt, EOFError):
                logger.warning("EntranceAgent: user input interrupted.")
                break

            if not user_input:
                continue

            messages.append(Message(role="user", content=user_input))

            # Call LLM
            system = build_system_prompt(required_fields, partial_profile)
            try:
                response = self.client.chat(
                    messages=messages,
                    system=system,
                    max_tokens=1024,
                    temperature=0.5,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(f"EntranceAgent: LLM call failed: {exc!r}")
                print_fn("抱歉，出现了一个错误，请重试。")
                continue

            result = _parse_turn(response.content)
            partial_profile.update(result.extracted)
            logger.debug(
                f"EntranceAgent turn {turn + 1}: extracted={result.extracted}, "
                f"collected={list(partial_profile.keys())}"
            )

            print_fn(result.reply)
            messages.append(Message(role="assistant", content=response.content))

        else:
            logger.warning(
                f"EntranceAgent: reached MAX_TURNS ({self.MAX_TURNS}) "
                f"without collecting all fields. Missing: "
                f"{[f for f in required_fields if f not in partial_profile]}"
            )

        # --- 3. Optionally persist conversation log ---
        if conversation_log_path is not None:
            try:
                _save_conversation_log(
                    conversation_log_path, messages, required_fields, partial_profile
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"EntranceAgent: failed to save conversation log: {exc!r}")

        # --- 4. Validate and enrich ---
        profile = UserProfile.model_validate(partial_profile)
        return enrich_profile(profile)
