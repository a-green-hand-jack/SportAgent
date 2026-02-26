"""Tests for graph builder and end-to-end routing."""

from __future__ import annotations

from pathlib import Path

from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile

_DATA_DIR = Path(__file__).parent.parent / "data"


def _base_profile() -> UserProfile:
    profile = UserProfile(
        name="Alice",
        age=30,
        gender="female",
        height_cm=165.0,
        weight_kg=60.0,
        goal=GoalType.general_fitness,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=45,
        available_equipment=[Equipment.bodyweight],
        activity_level="sedentary",
    )
    return enrich_profile(profile)


class TestBuildFitnessGraph:
    def test_graph_can_be_imported(self) -> None:
        from fitness_agent.graph import build_fitness_graph

        assert callable(build_fitness_graph)

    def test_graph_compiles(self) -> None:
        from fitness_agent.graph.builder import build_fitness_graph

        graph = build_fitness_graph()
        assert graph is not None

    def test_state_type_has_required_keys(self) -> None:
        from fitness_agent.graph.state import FitnessAgentState

        # TypedDict keys should include the required fields
        hints = FitnessAgentState.__annotations__
        assert "user_profile" in hints
        assert "provider" in hints
        assert "model" in hints
        assert "should_cook" in hints
        assert "should_gym" in hints
        assert "errors" in hints


class TestEdgeRouting:
    def test_route_after_plan_cook_only(self) -> None:
        from fitness_agent.graph.edges import route_after_plan

        state = {
            "user_profile": {},
            "provider": "mock",
            "model": "mock",
            "should_cook": True,
            "should_gym": False,
            "errors": [],
        }
        assert route_after_plan(state) == "cook_node"  # type: ignore[arg-type]

    def test_route_after_plan_gym_only(self) -> None:
        from fitness_agent.graph.edges import route_after_plan

        state = {
            "user_profile": {},
            "provider": "mock",
            "model": "mock",
            "should_cook": False,
            "should_gym": True,
            "errors": [],
        }
        assert route_after_plan(state) == "gym_node"  # type: ignore[arg-type]

    def test_route_after_plan_neither(self) -> None:
        from fitness_agent.graph.edges import route_after_plan

        state = {
            "user_profile": {},
            "provider": "mock",
            "model": "mock",
            "should_cook": False,
            "should_gym": False,
            "errors": [],
        }
        assert route_after_plan(state) == "__end__"  # type: ignore[arg-type]

    def test_route_after_plan_both(self) -> None:
        from fitness_agent.graph.edges import route_after_plan

        state = {
            "user_profile": {},
            "provider": "mock",
            "model": "mock",
            "should_cook": True,
            "should_gym": True,
            "errors": [],
        }
        # cook comes first when both are requested
        assert route_after_plan(state) == "cook_node"  # type: ignore[arg-type]

    def test_route_after_cook_with_gym(self) -> None:
        from fitness_agent.graph.edges import route_after_cook

        state = {
            "user_profile": {},
            "provider": "mock",
            "model": "mock",
            "should_cook": True,
            "should_gym": True,
            "errors": [],
        }
        assert route_after_cook(state) == "gym_node"  # type: ignore[arg-type]

    def test_route_after_cook_without_gym(self) -> None:
        from fitness_agent.graph.edges import route_after_cook

        state = {
            "user_profile": {},
            "provider": "mock",
            "model": "mock",
            "should_cook": True,
            "should_gym": False,
            "errors": [],
        }
        assert route_after_cook(state) == "__end__"  # type: ignore[arg-type]
