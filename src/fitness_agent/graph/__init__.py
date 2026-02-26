"""FitnessAgent LangGraph module.

Public API
----------
build_fitness_graph:   Factory that returns a compiled LangGraph StateGraph.
FitnessAgentState:     TypedDict defining the shared graph state.
"""

from fitness_agent.graph.builder import build_fitness_graph
from fitness_agent.graph.state import FitnessAgentState

__all__ = ["build_fitness_graph", "FitnessAgentState"]
