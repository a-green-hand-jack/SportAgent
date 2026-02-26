"""LangGraph state definition for the FitnessAgent pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, NotRequired, TypedDict


class FitnessAgentState(TypedDict):
    # ── 输入 ────────────────────────────────────────────────────────────────
    user_profile: dict  # UserProfile.model_dump()
    provider: str
    model: str
    should_cook: bool
    should_gym: bool

    # ── 输出（节点逐步写入）──────────────────────────────────────────────────
    weekly_plan: NotRequired[dict]
    cooking_plan: NotRequired[dict]
    gym_plan: NotRequired[dict]

    # ── 诊断（errors 由多个节点追加，使用 Annotated[list, operator.add]）──────
    errors: Annotated[list[str], operator.add]
