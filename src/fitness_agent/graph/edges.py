"""Graph routing edges for the FitnessAgent pipeline.

Functions
---------
route_after_plan:  Decide what to run after plan_node.
route_after_cook:  Decide what to run after cook_node.
"""

from __future__ import annotations

from fitness_agent.graph.state import FitnessAgentState


def route_after_plan(state: FitnessAgentState) -> str:
    """Decide the next node after plan_node completes.

    Decision tree
    -------------
    should_cook AND should_gym → "cook_node"  (cook first, then gym)
    should_cook only           → "cook_node"
    should_gym only            → "gym_node"
    neither                    → END
    """
    if state.get("should_cook"):
        return "cook_node"
    if state.get("should_gym"):
        return "gym_node"
    return "__end__"


def route_after_cook(state: FitnessAgentState) -> str:
    """Decide the next node after cook_node completes.

    Decision tree
    -------------
    should_gym → "gym_node"
    else       → END
    """
    if state.get("should_gym"):
        return "gym_node"
    return "__end__"
