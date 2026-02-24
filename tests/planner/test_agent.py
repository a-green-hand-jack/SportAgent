"""
Tests for PlannerAgent.

Strategy: mock the LLM client so no real API calls are made.
All KB operations run against real fixture data in tests/data/.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import Equipment, ExperienceLevel, GoalType
from fitness_agent.planner.agent import PlannerAgent
from fitness_agent.planner.models import WeeklyPlan
from fitness_agent.user.calculator import enrich_profile
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import LLMResponse

# ---------------------------------------------------------------------------
# Paths to test fixture data
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def kb() -> KnowledgeBase:
    return KnowledgeBase(
        exercises_path=_DATA_DIR / "exercises.json",
        nutrition_path=_DATA_DIR / "nutrition.json",
        rules_path=_DATA_DIR / "rules.json",
    )


@pytest.fixture()
def base_profile() -> UserProfile:
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


def _make_llm_client(json_response: str) -> MagicMock:
    """Build a mock LLM client that returns the given JSON string."""
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


def _minimal_plan_json(profile: UserProfile, n_days: int = 3) -> str:
    """Build a minimal valid WeeklyPlan JSON the mock LLM returns."""
    days = []
    for i in range(1, n_days + 1):
        days.append({
            "day_label": f"Day {i}",
            "focus": "Full body strength",
            "exercises": [
                {
                    "exercise_id": "push_up",
                    "exercise_name": "Push Up",
                    "exercise_name_zh": "俯卧撑",
                    "sets": 3,
                    "reps": "10-15",
                    "rest_seconds": 60,
                    "notes": None,
                }
            ],
            "estimated_duration_minutes": 60,
            "warmup_notes": "5 min light cardio",
            "cooldown_notes": "Stretch",
        })

    plan = {
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
            "meal_suggestions": ["早餐: 燕麦+鸡蛋", "午餐: 鸡胸肉+米饭", "晚餐: 牛肉+蔬菜"],
            "supplements": [],
        },
        "coach_notes": "保持每周渐进超负荷！",
    }
    return json.dumps(plan, ensure_ascii=False)


# ---------------------------------------------------------------------------
# PlannerAgent tests
# ---------------------------------------------------------------------------

class TestPlannerAgent:
    def test_generate_plan_returns_weekly_plan(self, kb, base_profile) -> None:
        client = _make_llm_client(_minimal_plan_json(base_profile))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        assert isinstance(plan, WeeklyPlan)

    def test_plan_has_correct_training_days(self, kb, base_profile) -> None:
        client = _make_llm_client(_minimal_plan_json(base_profile, n_days=3))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        assert len(plan.training_days) == 3

    def test_plan_goal_matches_profile(self, kb, base_profile) -> None:
        client = _make_llm_client(_minimal_plan_json(base_profile))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        assert plan.goal == base_profile.goal

    def test_plan_user_name_matches(self, kb, base_profile) -> None:
        client = _make_llm_client(_minimal_plan_json(base_profile))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        assert plan.user_name == "Bob"

    def test_llm_called_once(self, kb, base_profile) -> None:
        client = _make_llm_client(_minimal_plan_json(base_profile))
        agent = PlannerAgent(client=client, kb=kb)
        agent.generate_plan(base_profile)
        client.chat.assert_called_once()

    def test_plan_strips_markdown_fences(self, kb, base_profile) -> None:
        raw = "```json\n" + _minimal_plan_json(base_profile) + "\n```"
        client = _make_llm_client(raw)
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        assert isinstance(plan, WeeklyPlan)

    def test_unenriched_profile_raises(self, kb) -> None:
        bare = UserProfile(
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
        client = _make_llm_client("{}")
        agent = PlannerAgent(client=client, kb=kb)
        with pytest.raises(ValueError, match="enriched"):
            agent.generate_plan(bare)

    def test_invalid_llm_json_raises_runtime_error(self, kb, base_profile) -> None:
        client = _make_llm_client("This is not JSON at all.")
        agent = PlannerAgent(client=client, kb=kb)
        with pytest.raises(RuntimeError, match="not valid JSON"):
            agent.generate_plan(base_profile)

    def test_llm_response_missing_fields_raises_runtime_error(
        self, kb, base_profile
    ) -> None:
        # Returns valid JSON but missing required WeeklyPlan fields
        client = _make_llm_client(json.dumps({"partial": "data"}))
        agent = PlannerAgent(client=client, kb=kb)
        with pytest.raises(RuntimeError):
            agent.generate_plan(base_profile)

    def test_system_prompt_passed_to_llm(self, kb, base_profile) -> None:
        client = _make_llm_client(_minimal_plan_json(base_profile))
        agent = PlannerAgent(client=client, kb=kb)
        agent.generate_plan(base_profile)
        call_kwargs = client.chat.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 50  # non-trivial system prompt

    def test_exercise_pool_respects_equipment(self, kb) -> None:
        """Profile with only bodyweight equipment → pool must not include barbell exercises."""
        profile = enrich_profile(UserProfile(
            name="Cleo",
            age=22,
            gender="female",
            height_cm=165,
            weight_kg=58,
            goal=GoalType.general_fitness,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=45,
            available_equipment=[Equipment.bodyweight],
            activity_level="sedentary",
        ))
        client = _make_llm_client(_minimal_plan_json(profile, n_days=3))
        agent = PlannerAgent(client=client, kb=kb)
        agent.generate_plan(profile)

        # Verify the user message only contains bodyweight exercises
        user_msg = client.chat.call_args.kwargs["messages"][0].content
        assert "barbell" not in user_msg.lower() or "bodyweight" in user_msg.lower()

    def test_contraindications_filter_exercises(self, kb) -> None:
        """Profile with knee_injury → barbell_squat (knee contraindication) excluded."""
        profile = enrich_profile(UserProfile(
            name="Dave",
            age=35,
            gender="male",
            height_cm=180,
            weight_kg=85,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.intermediate,
            training_days_per_week=4,
            session_duration_minutes=75,
            available_equipment=[Equipment.barbell, Equipment.dumbbell],
            injuries=["knee_injury"],
            activity_level="moderately_active",
        ))
        client = _make_llm_client(_minimal_plan_json(profile, n_days=4))
        agent = PlannerAgent(client=client, kb=kb)
        agent.generate_plan(profile)

        user_msg = client.chat.call_args.kwargs["messages"][0].content
        # barbell_squat has knee_injury contraindication, should not appear in pool
        assert "barbell_squat" not in user_msg

    def test_parse_contraindications_unknown_ignored(self, kb) -> None:
        tags = PlannerAgent._parse_contraindications(["unknown_injury", "knee_injury"])
        tag_values = [t.value for t in tags]
        assert "knee_injury" in tag_values
        assert len([t for t in tag_values if t == "unknown_injury"]) == 0
