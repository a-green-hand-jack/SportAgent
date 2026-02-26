"""Tests for the K&T Registry."""

from __future__ import annotations

import pytest

from fitness_agent.graph.registry import REGISTRY, get_resources_for_agent


class TestRegistry:
    def test_all_agents_present(self) -> None:
        assert "planner" in REGISTRY
        assert "cooking" in REGISTRY
        assert "gym" in REGISTRY
        assert "injuries" in REGISTRY

    def test_planner_has_expected_knowledge(self) -> None:
        resources = get_resources_for_agent("planner")
        assert "rules" in resources["knowledge"]
        assert "anatomy" in resources["knowledge"]
        assert "exercises" in resources["knowledge"]

    def test_planner_has_expected_tools(self) -> None:
        resources = get_resources_for_agent("planner")
        assert "split_engine" in resources["tools"]
        assert "volume_checker" in resources["tools"]

    def test_cooking_has_expected_knowledge(self) -> None:
        resources = get_resources_for_agent("cooking")
        assert "recipes" in resources["knowledge"]
        assert "nutrition" in resources["knowledge"]
        assert "nutrition_principles" in resources["knowledge"]

    def test_cooking_has_expected_tools(self) -> None:
        resources = get_resources_for_agent("cooking")
        assert "deterministic_scaler" in resources["tools"]
        assert "grocery_gen" in resources["tools"]

    def test_gym_has_expected_knowledge(self) -> None:
        resources = get_resources_for_agent("gym")
        assert "exercises" in resources["knowledge"]
        assert "warmup_templates" in resources["knowledge"]
        assert "injury_profiles" in resources["knowledge"]

    def test_gym_has_expected_tools(self) -> None:
        resources = get_resources_for_agent("gym")
        assert "training_card_exporter" in resources["tools"]
        assert "rpe_engine" in resources["tools"]

    def test_injuries_agent_resources(self) -> None:
        resources = get_resources_for_agent("injuries")
        assert "safety_guard" in resources["tools"]
        assert "anatomy" in resources["knowledge"]

    def test_unknown_agent_raises(self) -> None:
        with pytest.raises(KeyError, match="not registered"):
            get_resources_for_agent("nonexistent_agent")

    def test_registry_entries_have_knowledge_and_tools(self) -> None:
        for agent_name, resources in REGISTRY.items():
            assert "knowledge" in resources, f"{agent_name} missing 'knowledge'"
            assert "tools" in resources, f"{agent_name} missing 'tools'"
            assert isinstance(resources["knowledge"], list)
            assert isinstance(resources["tools"], list)
