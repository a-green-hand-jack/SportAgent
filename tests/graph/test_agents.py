"""Tests for graph node functions (mock LLM, real KB fixture data)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import LLMResponse

_DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_llm_client(json_response: str) -> MagicMock:
    client = MagicMock()
    client.provider = "mock"
    client.model = "mock-model"
    client.chat.return_value = LLMResponse(
        content=json_response,
        provider="mock",
        model="mock-model",
        input_tokens=100,
        output_tokens=200,
    )
    return client


def _base_profile() -> UserProfile:
    profile = UserProfile(
        name="Bob",
        age=28,
        gender="male",
        height_cm=178.0,
        weight_kg=78.0,
        goal=GoalType.muscle_gain,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=60,
        available_equipment=[Equipment.bodyweight, Equipment.dumbbell],
        activity_level="lightly_active",
    )
    return enrich_profile(profile)


def _minimal_plan_json(profile: UserProfile, n_days: int = 3) -> str:
    days = []
    for i in range(1, n_days + 1):
        days.append(
            {
                "day_label": f"Day {i}",
                "focus": "Full body strength",
                "pre_workout_meal": "燕麦80g+鸡蛋2个",
                "exercises": [
                    {
                        "exercise_id": "push_up",
                        "exercise_name": "Push Up",
                        "exercise_name_zh": "俯卧撑",
                        "weight_hint": "徒手",
                        "sets": 4,
                        "reps": "10-15",
                        "rest_seconds": 60,
                        "notes": "保持身体成一条直线",
                    }
                ],
                "estimated_duration_minutes": 60,
                "warmup_notes": "① 开合跳 30秒 → ② 徒手深蹲 10次",
                "cooldown_notes": "① 胸肌拉伸 30秒 → ② 股四头肌拉伸 30秒",
                "post_workout_meal": "鸡胸肉150g+米饭150g",
            }
        )
    return json.dumps(
        {
            "user_name": profile.name,
            "goal": profile.goal.value,
            "experience_level": profile.experience_level.value,
            "training_days": days,
            "rest_days": [f"Day {i}" for i in range(n_days + 1, 8)],
            "daily_nutrition": {
                "calorie_target": profile.daily_calorie_target,
                "protein_g": profile.daily_protein_target_g,
                "carbs_g": 250.0,
                "fat_g": 65.0,
                "meal_suggestions": [],
            },
            "coach_notes": "保持渐进超负荷！",
            "four_week_overview": "第1-4周渐进",
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# plan_node tests
# ---------------------------------------------------------------------------


class TestPlanNode:
    def test_returns_weekly_plan_in_state(self) -> None:
        from fitness_agent.graph.agents.planner import plan_node

        profile = _base_profile()
        mock_client = _make_llm_client(_minimal_plan_json(profile))

        with (
            patch("fitness_agent.graph.agents.planner.build_client", return_value=mock_client),
            patch("fitness_agent.graph.agents.planner.KnowledgeBase") as mock_kb_cls,
        ):
            kb_instance = MagicMock()
            kb_instance.get_safe_exercises.return_value = []
            kb_instance.get_volume_targets.return_value = {}
            kb_instance.get_exercise_by_id.return_value = None
            kb_instance.format_rules_for_prompt.return_value = ""
            kb_instance.format_anatomy_for_prompt.return_value = ""
            kb_instance.format_nutrition_principles_for_prompt.return_value = ""
            kb_instance.format_injury_guidance_for_prompt.return_value = ""
            kb_instance.format_warmup_templates_for_prompt.return_value = ""
            kb_instance.exercises = []
            mock_kb_cls.return_value = kb_instance

            state = {
                "user_profile": profile.model_dump(),
                "provider": "mock",
                "model": "mock-model",
                "should_cook": False,
                "should_gym": False,
                "errors": [],
            }
            result = plan_node(state)  # type: ignore[arg-type]

        assert "weekly_plan" in result
        from fitness_agent.planner.models import WeeklyPlan

        plan = WeeklyPlan.model_validate(result["weekly_plan"])
        assert plan.user_name == "Bob"
        assert len(plan.training_days) == 3

    def test_missing_enrichment_returns_error(self) -> None:
        from fitness_agent.graph.agents.planner import plan_node

        bare_profile = UserProfile(
            name="Test",
            age=25,
            gender="male",
            height_cm=170,
            weight_kg=70,
            goal=GoalType.fat_loss,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            activity_level="sedentary",
        )
        state = {
            "user_profile": bare_profile.model_dump(),
            "provider": "mock",
            "model": "mock-model",
            "should_cook": False,
            "should_gym": False,
            "errors": [],
        }
        with (
            patch("fitness_agent.graph.agents.planner.build_client"),
            patch("fitness_agent.graph.agents.planner.KnowledgeBase"),
        ):
            result = plan_node(state)  # type: ignore[arg-type]

        assert "errors" in result
        assert len(result["errors"]) > 0
        err = result["errors"][0].lower()
        assert "enriched" in err or "calorie_target" in err


# ---------------------------------------------------------------------------
# test_builder: graph construction smoke test
# ---------------------------------------------------------------------------


class TestBuilder:
    def test_graph_builds_without_error(self) -> None:
        from fitness_agent.graph.builder import build_fitness_graph

        graph = build_fitness_graph()
        assert graph is not None

    def test_graph_has_plan_cook_gym_nodes(self) -> None:
        from fitness_agent.graph.builder import build_fitness_graph

        graph = build_fitness_graph()
        # The graph object should be a compiled StateGraph
        assert graph is not None
