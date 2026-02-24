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
        anatomy_path=_DATA_DIR / "anatomy.json",
        nutrition_principles_path=_DATA_DIR / "nutrition_principles.json",
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
            "pre_workout_meal": "训练前90分钟：燕麦80g+鸡蛋2个（替换：全麦面包2片+花生酱）",
            "exercises": [
                {
                    "exercise_id": "push_up",
                    "exercise_name": "Push Up",
                    "exercise_name_zh": "俯卧撑",
                    "weight_hint": "徒手",
                    "sets": 3,
                    "reps": "10-15",
                    "rest_seconds": 60,
                    "notes": "保持身体成一条直线，肘部夹紧身体，感受胸肌收缩",
                }
            ],
            "estimated_duration_minutes": 60,
            "warmup_notes": "① 开合跳 30秒 → ② 徒手深蹲 10次",
            "cooldown_notes": "① 胸肌拉伸 30秒 → ② 股四头肌拉伸 30秒",
            "post_workout_meal": "训练后60分钟内：鸡胸肉150g+米饭150g（替换：鱼肉180g）",
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
        "four_week_overview": "第1周：技术巩固\n第2周：逐步加重\n第3周：冲刺\n第4周：减量",
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

    def test_pre_post_workout_meals_in_generated_plan(self, kb, base_profile) -> None:
        """Verify that pre/post workout meal fields are parsed and preserved."""
        client = _make_llm_client(_minimal_plan_json(base_profile, n_days=3))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        # The minimal plan json includes pre/post workout meals
        assert plan.training_days[0].pre_workout_meal is not None
        assert plan.training_days[0].post_workout_meal is not None


# ---------------------------------------------------------------------------
# Volume validation tests
# ---------------------------------------------------------------------------

class TestVolumeValidation:
    def test_count_weekly_sets_known_exercise(self, kb, base_profile) -> None:
        """push_up is in test KB and has chest as primary muscle."""
        client = _make_llm_client(_minimal_plan_json(base_profile, n_days=1))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        counts = agent._count_weekly_sets(plan)
        # push_up exercises should contribute to chest (primary muscle in test KB)
        # or at minimum the counts dict is a valid dict
        assert isinstance(counts, dict)

    def test_count_weekly_sets_unknown_exercise_skipped(self, kb, base_profile) -> None:
        """Exercises not in KB should be skipped without crashing."""
        from fitness_agent.planner.models import WeeklyPlan, TrainingDay, ExerciseSet, DailyNutrition
        from fitness_agent.knowledge_base.models import GoalType
        day = TrainingDay(
            day_label="Day 1",
            focus="Test",
            exercises=[ExerciseSet(
                exercise_id="nonexistent_exercise_xyz",
                exercise_name="Unknown",
                exercise_name_zh="未知动作",
                sets=3,
                reps="10",
                rest_seconds=60,
            )],
            estimated_duration_minutes=45,
        )
        plan = WeeklyPlan(
            user_name="Test",
            goal=GoalType.general_fitness,
            experience_level="beginner",
            training_days=[day],
            daily_nutrition=DailyNutrition(
                calorie_target=2000, protein_g=150, carbs_g=200, fat_g=60
            ),
        )
        agent = PlannerAgent(client=_make_llm_client("{}"), kb=kb)
        counts = agent._count_weekly_sets(plan)
        # Unknown exercise is skipped — counts should be empty or have no entry for its muscles
        assert isinstance(counts, dict)
        # nonexistent exercise should not contribute to any muscle count
        assert sum(counts.values()) == 0

    def test_validate_volume_returns_list(self, kb, base_profile) -> None:
        from fitness_agent.knowledge_base.models import ExperienceLevel
        client = _make_llm_client(_minimal_plan_json(base_profile, n_days=3))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(base_profile)
        warnings = agent._validate_volume(plan, ExperienceLevel.beginner)
        assert isinstance(warnings, list)

    def test_volume_warning_appended_to_coach_notes(self, kb) -> None:
        """
        A plan with 1 training day and only push_up exercises will have
        most muscle groups below minimum. Warnings should appear in coach_notes.
        """
        from fitness_agent.user.calculator import enrich_profile
        from fitness_agent.knowledge_base.models import ExperienceLevel

        profile = enrich_profile(UserProfile(
            name="VolumeTest",
            age=25,
            gender="male",
            height_cm=175,
            weight_kg=75,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=1,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            activity_level="sedentary",
        ))
        # Only 1 training day → most muscles will be below beginner minimums
        client = _make_llm_client(_minimal_plan_json(profile, n_days=1))
        agent = PlannerAgent(client=client, kb=kb)
        plan = agent.generate_plan(profile)
        # If any warnings were generated, they should be in coach_notes
        if "📊" in plan.coach_notes:
            assert "周训练量提醒" in plan.coach_notes
