"""
Free-text → structured enum parser using LLM.

Converts arbitrary user descriptions (Chinese, English, mixed) of injuries
into validated ``ContraindicationTag`` enum values via a single LLM call.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fitness_agent.knowledge_base.models import ContraindicationTag
from fitness_agent.utils.logging import get_logger

if TYPE_CHECKING:
    from fitness_agent.utils.llm_client import BaseLLMClient

logger = get_logger(__name__)

# Build a reference block that the LLM can use to map descriptions
_TAG_DESCRIPTIONS: dict[str, str] = {
    "knee_injury":      "膝关节损伤 / 膝盖受伤",
    "lower_back_pain":  "腰痛 / 下背痛 / 腰部不适",
    "shoulder_injury":  "肩关节损伤 / 肩膀受伤",
    "wrist_injury":     "手腕损伤 / 手腕疼",
    "neck_pain":        "颈部疼痛 / 脖子痛",
    "hip_injury":       "髋关节损伤 / 胯部受伤",
    "ankle_injury":     "踝关节损伤 / 脚踝受伤",
    "herniated_disc":   "椎间盘突出 / 腰椎间盘",
    "hypertension":     "高血压",
    "elbow_injury":     "肘关节损伤 / 手肘受伤",
}

_SYSTEM_PROMPT = """\
你是一个健身安全分析助手。用户会用自然语言描述他们的伤病或身体限制。
你的任务是从以下预定义标签中，选出所有与用户描述匹配的标签。

可选标签及含义：
{tag_list}

规则：
1. 只返回一个 JSON 数组，包含匹配的标签字符串，如 ["wrist_injury", "knee_injury"]
2. 如果没有任何匹配，返回空数组 []
3. 不要返回任何其他内容，只返回 JSON 数组
4. 对模糊描述做合理推断（如"手腕"→"wrist_injury"，"腰不好"→"lower_back_pain"）
"""


def _build_system_prompt() -> str:
    tag_list = "\n".join(
        f"- {tag}: {desc}" for tag, desc in _TAG_DESCRIPTIONS.items()
    )
    return _SYSTEM_PROMPT.format(tag_list=tag_list)


def parse_injuries_with_llm(
    user_text: str,
    client: BaseLLMClient,
) -> list[ContraindicationTag]:
    """
    Parse free-text injury descriptions into ContraindicationTag values via LLM.

    Parameters
    ----------
    user_text:
        Raw user input describing injuries (any language, any format).
    client:
        An initialised LLM client.

    Returns
    -------
    list[ContraindicationTag]
        Matched tags. Returns empty list on any failure.
    """
    if not user_text.strip():
        return []

    from fitness_agent.utils.llm_client import Message

    try:
        response = client.chat(
            messages=[Message(role="user", content=user_text)],
            system=_build_system_prompt(),
            max_tokens=256,
            temperature=0.0,
        )
        raw = response.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[1:end])

        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            logger.warning(f"LLM returned non-list: {raw!r}")
            return []

        valid = {t.value for t in ContraindicationTag}
        tags = []
        for item in parsed:
            if isinstance(item, str) and item in valid:
                tags.append(ContraindicationTag(item))
            else:
                logger.warning(f"LLM returned unknown tag: {item!r}")
        return tags

    except Exception as exc:
        logger.warning(f"LLM injury parsing failed: {exc}")
        return []


def format_injuries_for_display(tags: list[ContraindicationTag]) -> str:
    """Format a list of tags into a human-readable Chinese string."""
    if not tags:
        return "无"
    parts = [f"{_TAG_DESCRIPTIONS.get(t.value, t.value)} ({t.value})" for t in tags]
    return "、".join(parts)
