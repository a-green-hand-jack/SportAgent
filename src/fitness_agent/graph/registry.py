"""K&T Registry — authorisation matrix that maps each agent to its allowed KB domains and tools.

Each agent node reads its own entry from REGISTRY to discover which
Knowledge Accessors and Tool functions it is authorised to use.
"""

from __future__ import annotations

from typing import TypedDict


class AgentResources(TypedDict):
    knowledge: list[str]
    tools: list[str]


# ---------------------------------------------------------------------------
# Central registry
# ---------------------------------------------------------------------------

REGISTRY: dict[str, AgentResources] = {
    "planner": {
        "knowledge": ["rules", "anatomy", "exercises"],
        "tools": ["split_engine", "volume_checker"],
    },
    "cooking": {
        "knowledge": ["recipes", "nutrition", "nutrition_principles"],
        "tools": ["deterministic_scaler", "grocery_gen"],
    },
    "gym": {
        "knowledge": ["exercises", "warmup_templates", "injury_profiles"],
        "tools": ["training_card_exporter", "rpe_engine"],
    },
    "injuries": {
        "knowledge": ["anatomy", "injury_profiles"],
        "tools": ["safety_guard"],
    },
}


def get_resources_for_agent(agent_name: str) -> AgentResources:
    """Return the authorised knowledge domains and tool names for the given agent.

    Raises
    ------
    KeyError
        If ``agent_name`` is not registered.
    """
    if agent_name not in REGISTRY:
        raise KeyError(
            f"Agent '{agent_name}' is not registered. " f"Available agents: {list(REGISTRY.keys())}"
        )
    return REGISTRY[agent_name]
