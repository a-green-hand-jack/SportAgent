"""
Tests for GYMAgent.

Strategy: mock the LLM client so no real API calls are made.
All KB operations run against real fixture data in tests/data/.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fitness_agent.gym.agent import GYMAgent
from fitness_agent.gym.models import WeeklyGymPlan
from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    ExperienceLevel,
    GoalType,
)
from fitness_agent.planner.models import (
    DailyNutrition,
    ExerciseSet,
    TrainingDay,
    WeeklyPlan,
)
from fitness_agent.user.models import UserProfile
from fitness_agent.utils.llm_client import LLMResponse


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
        warmup_templates_path=_DATA_DIR / "warmup_templates.json",
        injury_profiles_path=_DATA_DIR / "injury_profiles.json",
    )


@pytest.fixture()
def profile() -> UserProfile:
    return UserProfile(
        name="GymTestUser",
        age=28,
        gender="male",
        height_cm=178.0,
        weight_kg=78.0,
        goal=GoalType.muscle_gain,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=60,
        available_equipment=[Equipment.bodyweight, Equipment.dumbbell, Equipment.barbell],
        strength_assessment="beginner_light",
    )


@pytest.fixture()
def weekly_plan(profile: UserProfile) -> WeeklyPlan:
    days = [
        TrainingDay(
            day_label="周一 (Day 1)",
            focus="上肢推力",
            exercises=[
                ExerciseSet(
                    exercise_id="push_up",
                    exercise_name="Push Up",
                    exercise_name_zh="俯卧撑",
                    sets=3,
                    reps="10-15",
                    rest_seconds=60,
                ),
                ExerciseSet(
                    exercise_id="dumbbell_bench_press",
                    exercise_name="Dumbbell Bench Press",
                    exercise_name_zh="哑铃卧推",
                    sets=4,
                    reps="8-12",
                    rest_seconds=90,
                ),
            ],
            estimated_duration_minutes=60,
        ),
        TrainingDay(
            day_label="周三 (Day 3)",
            focus="下肢",
            exercises=[
                ExerciseSet(
                    exercise_id="barbell_squat",
                    exercise_name="Barbell Back Squat",
                    exercise_name_zh="杠铃深蹲",
                    sets=3,
                    reps="8-12",
                    rest_seconds=90,
                ),
            ],
            estimated_duration_minutes=45,
        ),
    ]
    return WeeklyPlan(
        user_name=profile.name,
        goal=profile.goal,
        experience_level=profile.experience_level.value,
        training_days=days,
        rest_days=["周二", "周四", "周五", "周六", "周日"],
        daily_nutrition=DailyNutrition(
            calorie_target=2500,
            protein_g=150,
            carbs_g=250,
            fat_g=65,
        ),
    )


# ---------------------------------------------------------------------------
# Mock LLM helpers
# ---------------------------------------------------------------------------


def _make_session_json(
    day_label: str,
    focus: str,
    exercises: list[dict],
) -> str:
    """Build a valid GymSessionPlan JSON string (as the LLM would return)."""
    data = {
        "day_label": day_label,
        "focus": focus,
        "is_training_day": True,
        "estimated_duration_minutes": 55,
        "exercises": exercises,
        "session_flow_notes_zh": "先做复合动作，再做孤立动作。",
        "equipment_needed": ["哑铃", "卧推凳"],
    }
    return json.dumps(data, ensure_ascii=False)


def _make_exercise_json(
    exercise_id: str,
    name_zh: str,
    name: str,
    sets: int = 3,
    reps: str = "10-12",
) -> dict:
    return {
        "exercise_id": exercise_id,
        "exercise_name_zh": name_zh,
        "exercise_name": name,
        "sets": sets,
        "reps": reps,
        "rest_seconds": 60,
        "coaching_tips_zh": ["保持核心收紧", "控制动作速度"],
        "starting_weight_zh": "从空杆(20kg)开始",
        "breathing_zh": "下降吸气，推起呼气",
        "common_mistakes_zh": ["动作过快失去控制"],
        "tempo_zh": "3-1-2",
    }


def _make_progression_json() -> str:
    """Build a valid 4-week progression JSON string."""
    weeks = []
    themes = ["适应期", "渐进期", "强化期", "减量周"]
    for i, theme in enumerate(themes, 1):
        weeks.append({
            "week_number": i,
            "theme_zh": theme,
            "volume_change_zh": "按计划执行" if i == 1 else f"+{i-1} 组",
            "intensity_change_zh": "维持" if i == 1 else f"+{(i-1)*2.5}kg",
            "rpe_target": f"RPE {5+i}",
            "notes_zh": f"第{i}周注意事项",
        })
    return json.dumps(weeks, ensure_ascii=False)


def _make_mock_client(weekly_plan: WeeklyPlan) -> MagicMock:
    """Create a mock LLM client that returns valid gym session + progression."""
    call_count = [0]
    n_training_days = len(weekly_plan.training_days)

    def _side_effect(messages, **kwargs):
        call_count[0] += 1

        # First N calls are session generation, last call is progression
        if call_count[0] <= n_training_days:
            day_idx = call_count[0] - 1
            td = weekly_plan.training_days[day_idx]
            exercises = [
                _make_exercise_json(
                    ex.exercise_id, ex.exercise_name_zh, ex.exercise_name,
                    ex.sets, ex.reps,
                )
                for ex in td.exercises
            ]
            content = _make_session_json(td.day_label, td.focus, exercises)
        else:
            content = _make_progression_json()

        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            input_tokens=1000,
            output_tokens=500,
        )

    client = MagicMock()
    client.provider = "mock"
    client.model = "mock-model"
    client.chat = MagicMock(side_effect=_side_effect)
    return client


# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------


class TestGYMAgent:
    def test_generate_gym_plan_structure(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """Test that the full pipeline produces a valid WeeklyGymPlan."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        assert isinstance(plan, WeeklyGymPlan)
        assert plan.user_name == "GymTestUser"
        assert len(plan.sessions) == 2
        assert len(plan.four_week_progression) == 4

    def test_llm_call_count(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """Should make N+1 LLM calls: N sessions + 1 progression."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        agent.generate_gym_plan(weekly_plan, profile)

        n_days = len(weekly_plan.training_days)
        assert client.chat.call_count == n_days + 1  # sessions + progression

    def test_equipment_checklist_aggregated(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """Equipment should be aggregated across all sessions."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        assert isinstance(plan.equipment_checklist, list)
        assert "哑铃" in plan.equipment_checklist

    def test_general_tips_present(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """General tips should be non-empty."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        assert plan.general_tips_zh != ""
        assert "初学者" in plan.general_tips_zh

    def test_empty_training_days_raises(
        self, kb: KnowledgeBase, profile: UserProfile,
    ) -> None:
        """WeeklyPlan with empty training_days should raise ValidationError
        at model construction (min_length=1)."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            WeeklyPlan(
                user_name="Test",
                goal=GoalType.muscle_gain,
                experience_level="beginner",
                training_days=[],
                daily_nutrition=DailyNutrition(
                    calorie_target=2500, protein_g=150, carbs_g=250, fat_g=65,
                ),
            )


# ---------------------------------------------------------------------------
# KB injection tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PlanAgent warmup priority tests
# ---------------------------------------------------------------------------


class TestWarmupPriority:
    def test_planagent_warmup_used_over_kb_template(
        self, kb: KnowledgeBase, profile: UserProfile,
    ) -> None:
        """When PlanAgent provides warmup_notes, those should be used instead
        of KB templates."""
        plan = WeeklyPlan(
            user_name="Test",
            goal=GoalType.muscle_gain,
            experience_level="beginner",
            training_days=[
                TrainingDay(
                    day_label="周一 (Day 1)",
                    focus="上肢拉力",
                    exercises=[
                        ExerciseSet(
                            exercise_id="pull_up",
                            exercise_name="Pull Up",
                            exercise_name_zh="引体向上",
                            sets=3, reps="6-8", rest_seconds=90,
                        ),
                    ],
                    estimated_duration_minutes=45,
                    warmup_notes="① 弹力带直臂下拉 15次 → ② 肩胛骨下压 10次 → ③ 轻划船 10次",
                    cooldown_notes="① 背阔肌拉伸 每侧30秒 → ② 菱形肌拉伸 30秒",
                ),
            ],
            daily_nutrition=DailyNutrition(
                calorie_target=2500, protein_g=150, carbs_g=250, fat_g=65,
            ),
        )

        client = _make_mock_client(plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        result = agent.generate_gym_plan(plan, profile)

        session = result.sessions[0]
        # Should use PlanAgent's targeted warmup, not KB template
        warmup_text = " ".join(session.warmup_sequence)
        assert "直臂下拉" in warmup_text
        assert "肩胛骨下压" in warmup_text

        cooldown_text = " ".join(session.cooldown_sequence)
        assert "背阔肌" in cooldown_text

    def test_kb_template_fallback_when_no_notes(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """When PlanAgent doesn't provide warmup_notes, KB template should be used."""
        # weekly_plan fixture has no warmup_notes
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        result = agent.generate_gym_plan(weekly_plan, profile)

        # Should still have warmup (from KB template fallback)
        for session in result.sessions:
            assert len(session.warmup_sequence) > 0


# ---------------------------------------------------------------------------
# Parse notes to sequence tests
# ---------------------------------------------------------------------------


class TestParseNotesToSequence:
    def test_arrow_separator(self) -> None:
        notes = "① 弹力带肩外旋 → ② 胸椎旋转 → ③ 轻侧平举"
        result = GYMAgent._parse_notes_to_sequence(notes)
        assert len(result) == 3
        assert "弹力带肩外旋" in result[0]

    def test_circled_number_separator(self) -> None:
        notes = "①开合跳30秒②髋关节绕环③弓步走④徒手深蹲"
        result = GYMAgent._parse_notes_to_sequence(notes)
        assert len(result) == 4

    def test_newline_separator(self) -> None:
        notes = "弹力带直臂下拉 15次\n肩胛骨下压 10次\n轻划船 10次"
        result = GYMAgent._parse_notes_to_sequence(notes)
        assert len(result) == 3

    def test_empty_string(self) -> None:
        assert GYMAgent._parse_notes_to_sequence("") == []
        assert GYMAgent._parse_notes_to_sequence("  ") == []

    def test_single_item(self) -> None:
        result = GYMAgent._parse_notes_to_sequence("热身5分钟")
        assert result == ["热身5分钟"]


# ---------------------------------------------------------------------------
# KB injection tests
# ---------------------------------------------------------------------------


class TestKBInjection:
    def test_kb_cues_injected(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """KB cues should be injected into exercises."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        # push_up should have KB cues from exercises.json
        push_up_ex = None
        for session in plan.sessions:
            for ex in session.exercises:
                if ex.exercise_id == "push_up":
                    push_up_ex = ex
                    break

        assert push_up_ex is not None
        assert len(push_up_ex.kb_cues) > 0
        assert len(push_up_ex.primary_muscles) > 0

    def test_muscles_injected(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """Primary and secondary muscles should be injected from KB."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        for session in plan.sessions:
            for ex in session.exercises:
                kb_ex = kb.get_exercise_by_id(ex.exercise_id)
                if kb_ex is not None:
                    assert len(ex.primary_muscles) > 0
                    assert ex.equipment != []

    def test_warmup_cooldown_injected(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """Warmup and cooldown sequences should be injected from templates."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        for session in plan.sessions:
            # Should have warmup from KB templates
            assert len(session.warmup_sequence) > 0
            assert len(session.cooldown_sequence) > 0


# ---------------------------------------------------------------------------
# Injury adaptation tests
# ---------------------------------------------------------------------------


class TestInjuryAdaptation:
    def test_injury_adaptations_injected(self, kb: KnowledgeBase) -> None:
        """When user has injuries matching exercise contraindications,
        adaptations should be injected."""
        profile_injured = UserProfile(
            name="InjuredUser",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=75.0,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight, Equipment.dumbbell],
            injuries=[ContraindicationTag.knee_injury],
        )

        # Create a plan with barbell_squat (which has knee_injury contraindication)
        plan = WeeklyPlan(
            user_name="InjuredUser",
            goal=GoalType.muscle_gain,
            experience_level="beginner",
            training_days=[
                TrainingDay(
                    day_label="周一 (Day 1)",
                    focus="下肢",
                    exercises=[
                        ExerciseSet(
                            exercise_id="barbell_squat",
                            exercise_name="Barbell Back Squat",
                            exercise_name_zh="杠铃深蹲",
                            sets=3,
                            reps="8-12",
                            rest_seconds=90,
                        ),
                    ],
                    estimated_duration_minutes=45,
                ),
            ],
            daily_nutrition=DailyNutrition(
                calorie_target=2500, protein_g=150, carbs_g=250, fat_g=65,
            ),
        )

        client = _make_mock_client(plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        result = agent.generate_gym_plan(plan, profile_injured)

        # Check warmup injury modifications
        session = result.sessions[0]
        assert session.warmup_injury_modifications != {}

    def test_injury_warmup_routine_prepended(self, kb: KnowledgeBase) -> None:
        """Injury-specific warmup routine should be prepended to warmup_sequence."""
        profile_injured = UserProfile(
            name="WristUser",
            age=28,
            gender="male",
            height_cm=178.0,
            weight_kg=78.0,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight, Equipment.dumbbell],
            injuries=[ContraindicationTag.wrist_injury],
        )

        plan = WeeklyPlan(
            user_name="WristUser",
            goal=GoalType.muscle_gain,
            experience_level="beginner",
            training_days=[
                TrainingDay(
                    day_label="周一 (Day 1)",
                    focus="上肢推力",
                    exercises=[
                        ExerciseSet(
                            exercise_id="push_up",
                            exercise_name="Push Up",
                            exercise_name_zh="俯卧撑",
                            sets=3, reps="10", rest_seconds=60,
                        ),
                    ],
                    estimated_duration_minutes=45,
                ),
            ],
            daily_nutrition=DailyNutrition(
                calorie_target=2500, protein_g=150, carbs_g=250, fat_g=65,
            ),
        )

        client = _make_mock_client(plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        result = agent.generate_gym_plan(plan, profile_injured)

        session = result.sessions[0]
        # First item should be the injury warmup header
        assert len(session.warmup_sequence) > 0
        assert "手腕损伤" in session.warmup_sequence[0]
        assert "专项热身" in session.warmup_sequence[0]
        # Should contain separator before regular warmup
        assert "---" in session.warmup_sequence


# ---------------------------------------------------------------------------
# Exercise ID validation tests
# ---------------------------------------------------------------------------


class TestExerciseIdValidation:
    def test_valid_ids_pass(
        self, kb: KnowledgeBase, profile: UserProfile, weekly_plan: WeeklyPlan,
    ) -> None:
        """All exercise_ids in the mock response are valid KB ids."""
        client = _make_mock_client(weekly_plan)
        agent = GYMAgent(client=client, kb=kb, max_retries=0)
        plan = agent.generate_gym_plan(weekly_plan, profile)

        for session in plan.sessions:
            for ex in session.exercises:
                assert kb.get_exercise_by_id(ex.exercise_id) is not None

    def test_invalid_id_triggers_retry(self, kb: KnowledgeBase, profile: UserProfile) -> None:
        """Invalid exercise_id should trigger retry when max_retries > 0."""
        plan = WeeklyPlan(
            user_name="Test",
            goal=GoalType.muscle_gain,
            experience_level="beginner",
            training_days=[
                TrainingDay(
                    day_label="周一 (Day 1)",
                    focus="Test",
                    exercises=[
                        ExerciseSet(
                            exercise_id="push_up",
                            exercise_name="Push Up",
                            exercise_name_zh="俯卧撑",
                            sets=3, reps="10", rest_seconds=60,
                        ),
                    ],
                    estimated_duration_minutes=45,
                ),
            ],
            daily_nutrition=DailyNutrition(
                calorie_target=2500, protein_g=150, carbs_g=250, fat_g=65,
            ),
        )

        call_count = [0]

        def _side_effect(messages, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: return invalid exercise_id
                content = _make_session_json(
                    "周一 (Day 1)", "Test",
                    [_make_exercise_json("INVALID_ID", "无效动作", "Invalid")],
                )
            elif call_count[0] == 2:
                # Retry: return valid exercise_id
                content = _make_session_json(
                    "周一 (Day 1)", "Test",
                    [_make_exercise_json("push_up", "俯卧撑", "Push Up")],
                )
            else:
                # Progression call
                content = _make_progression_json()
            return LLMResponse(
                content=content, provider="mock", model="m",
                input_tokens=100, output_tokens=100,
            )

        client = MagicMock()
        client.provider = "mock"
        client.model = "mock-model"
        client.chat = MagicMock(side_effect=_side_effect)

        agent = GYMAgent(client=client, kb=kb, max_retries=1)
        result = agent.generate_gym_plan(plan, profile)

        # Should have retried (2 session calls + 1 progression = 3 total)
        assert client.chat.call_count == 3
        assert result.sessions[0].exercises[0].exercise_id == "push_up"


# ---------------------------------------------------------------------------
# Duration validation tests
# ---------------------------------------------------------------------------


class TestDurationValidation:
    def test_duration_estimation(self, kb: KnowledgeBase) -> None:
        """Test the duration estimation logic."""
        from fitness_agent.gym.models import ExerciseGuidance, GymSessionPlan

        session = GymSessionPlan(
            day_label="Test",
            focus="Test",
            estimated_duration_minutes=60,
            exercises=[
                ExerciseGuidance(
                    exercise_id="push_up",
                    exercise_name_zh="俯卧撑",
                    exercise_name="Push Up",
                    sets=3, reps="10", rest_seconds=60,
                    coaching_tips_zh=["tip"],
                    starting_weight_zh="徒手",
                    breathing_zh="正常呼吸",
                    common_mistakes_zh=["错误"],
                ),
            ],
        )

        agent = GYMAgent(client=MagicMock(), kb=kb)
        warnings = agent._validate_duration(session, target_minutes=60)
        # 3 sets × 90s/set avg = 4.5 min + 15 min warmup = ~19.5 min
        # That's well below 60*0.7=42 min, so should warn
        assert len(warnings) > 0


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------


class TestResponseParsing:
    def test_parse_session_response_valid(self) -> None:
        raw = _make_session_json(
            "周一 (Day 1)", "Test",
            [_make_exercise_json("push_up", "俯卧撑", "Push Up")],
        )
        session = GYMAgent._parse_session_response(raw, "周一 (Day 1)")
        assert session.day_label == "周一 (Day 1)"
        assert len(session.exercises) == 1

    def test_parse_session_strips_markdown(self) -> None:
        inner = _make_session_json(
            "周一", "Test",
            [_make_exercise_json("push_up", "俯卧撑", "Push Up")],
        )
        raw = f"```json\n{inner}\n```"
        session = GYMAgent._parse_session_response(raw, "周一")
        assert session.day_label == "周一"

    def test_parse_progression_response_valid(self) -> None:
        raw = _make_progression_json()
        weeks = GYMAgent._parse_progression_response(raw)
        assert len(weeks) == 4
        assert weeks[0].theme_zh == "适应期"
        assert weeks[3].theme_zh == "减量周"

    def test_parse_session_invalid_json_raises(self) -> None:
        with pytest.raises(RuntimeError, match="not valid JSON"):
            GYMAgent._parse_session_response("not json", "周一")

    def test_parse_progression_invalid_json_raises(self) -> None:
        with pytest.raises(RuntimeError, match="not valid JSON"):
            GYMAgent._parse_progression_response("not json")
