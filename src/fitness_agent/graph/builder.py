"""build_fitness_graph — factory that assembles the LangGraph StateGraph.

Graph topology
--------------
START → plan_node
              │
    route_after_plan
     ├── should_cook → cook_node → route_after_cook
     │                              ├── should_gym → gym_node → END
     │                              └── else       → END
     ├── should_gym  → gym_node → END
     └── else        → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from fitness_agent.graph.agents.cooking import cook_node
from fitness_agent.graph.agents.gym import gym_node
from fitness_agent.graph.agents.planner import plan_node
from fitness_agent.graph.edges import route_after_cook, route_after_plan
from fitness_agent.graph.state import FitnessAgentState


def build_fitness_graph() -> CompiledStateGraph:
    """Assemble and compile the FitnessAgent StateGraph.

    Returns
    -------
    StateGraph
        A compiled LangGraph graph ready to invoke with a FitnessAgentState dict.

    Usage
    -----
    >>> graph = build_fitness_graph()
    >>> result = graph.invoke({
    ...     "user_profile": profile.model_dump(),
    ...     "provider": "qwen",
    ...     "model": "qwen-plus",
    ...     "should_cook": True,
    ...     "should_gym": False,
    ...     "errors": [],
    ... })
    """
    builder = StateGraph(FitnessAgentState)

    # --- Nodes ---
    builder.add_node("plan_node", plan_node)
    builder.add_node("cook_node", cook_node)
    builder.add_node("gym_node", gym_node)

    # --- Edges: entry point ---
    builder.add_edge(START, "plan_node")

    # --- Conditional routing after plan_node ---
    builder.add_conditional_edges(
        "plan_node",
        route_after_plan,
        {
            "cook_node": "cook_node",
            "gym_node": "gym_node",
            "__end__": END,
        },
    )

    # --- Conditional routing after cook_node ---
    builder.add_conditional_edges(
        "cook_node",
        route_after_cook,
        {
            "gym_node": "gym_node",
            "__end__": END,
        },
    )

    # --- gym_node always leads to END ---
    builder.add_edge("gym_node", END)

    return builder.compile()
