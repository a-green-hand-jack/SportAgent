"""Knowledge Accessors — domain-scoped views into the KnowledgeBase."""

from fitness_agent.graph.knowledge.accessors import (
    CookingKnowledge,
    GYMKnowledge,
    PlannerKnowledge,
)

__all__ = ["PlannerKnowledge", "CookingKnowledge", "GYMKnowledge"]
