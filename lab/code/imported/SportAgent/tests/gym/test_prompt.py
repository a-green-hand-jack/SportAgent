"""Tests for gym prompt construction."""
from __future__ import annotations

from pathlib import Path

import pytest

from fitness_agent.gym.prompt import (
    GYM_SYSTEM,
    GYM_PROGRESSION_SYSTEM,
    build_gym_user_message,
    build_gym_progression_message,
)
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


_DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kb() -> KnowledgeBase:
    return KnowledgeBase(
        exercises_path=_DATA_DIR / "exercises.json",
        nutrition_path=_DATA_DIR / "nutrition.json",
        rules_path=_DATA_DIR / "rules.json",
        anatomy_path=_DATA_DIR / "anatomy.json",
    )


@pytest.fixture()
def profile() -> UserProfile:
    return UserProfile(
        name="GymBob",
        age=25,
        gender="male",
        height_cm=175.0,
        weight_kg=72.0,
        goal=GoalType.muscle_gain,
        experience_level=ExperienceLevel.beginner,
        training_days_per_week=3,
        session_duration_minutes=60,
        available_equipment=[Equipment.bodyweight, Equipment.dumbbell, Equipment.barbell],
        strength_assessment="beginner_light",
        preferred_training_time="morning",
    )


@pytest.fixture()
def training_day() -> TrainingDay:
    return TrainingDay(
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
                weight_hint="5-10kg 哑铃",
            ),
        ],
        estimated_duration_minutes=60,
    )


@pytest.fixture()
def weekly_plan(profile: UserProfile) -> WeeklyPlan:
    return WeeklyPlan(
        user_name=profile.name,
        goal=profile.goal,
        experience_level=profile.experience_level.value,
        training_days=[
            TrainingDay(
                day_label="周一 (Day 1)",
                focus="上肢推力",
                exercises=[
                    ExerciseSet(
                        exercise_id="push_up",
                        exercise_name="Push Up",
                        exercise_name_zh="俯卧撑",
                        sets=3,
                        reps="10",
                        rest_seconds=60,
                    ),
                ],
                estimated_duration_minutes=60,
            ),
        ],
        rest_days=["周二", "周三"],
        daily_nutrition=DailyNutrition(
            calorie_target=2500,
            protein_g=150,
            carbs_g=250,
            fat_g=65,
        ),
    )


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_gym_system_mentions_json(self) -> None:
        assert "JSON" in GYM_SYSTEM
        assert "exercise_id" in GYM_SYSTEM

    def test_gym_system_mentions_coaching_tips(self) -> None:
        assert "coaching_tips_zh" in GYM_SYSTEM
        assert "breathing_zh" in GYM_SYSTEM

    def test_gym_system_mentions_strength_assessment(self) -> None:
        assert "strength_assessment" in GYM_SYSTEM
        assert "beginner_no_weights" in GYM_SYSTEM

    def test_gym_system_weight_hint_constraint(self) -> None:
        """GYM_SYSTEM should instruct LLM not to exceed PlanAgent's weight_hint."""
        assert "weight_hint" in GYM_SYSTEM
        assert "不应超过" in GYM_SYSTEM

    def test_progression_system_mentions_4_weeks(self) -> None:
        assert "4" in GYM_PROGRESSION_SYSTEM
        assert "ProgressionWeek" in GYM_PROGRESSION_SYSTEM
        assert "RPE" in GYM_PROGRESSION_SYSTEM

    def test_progression_system_exercise_specific(self) -> None:
        """Progression prompt should require exercise-specific progressions."""
        assert "exercise_specific_zh" in GYM_PROGRESSION_SYSTEM


# ---------------------------------------------------------------------------
# User message builder tests
# ---------------------------------------------------------------------------


class TestBuildGymUserMessage:
    def test_contains_user_profile(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        msg = build_gym_user_message(profile, weekly_plan, training_day, kb)
        assert "GymBob" in msg
        assert "72.0 kg" in msg
        assert "beginner_light" in msg
        assert "morning" in msg

    def test_contains_exercise_list(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        msg = build_gym_user_message(profile, weekly_plan, training_day, kb)
        assert "push_up" in msg
        assert "dumbbell_bench_press" in msg
        assert "俯卧撑" in msg
        assert "哑铃卧推" in msg

    def test_contains_kb_reference(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        msg = build_gym_user_message(profile, weekly_plan, training_day, kb)
        assert "KB 参考数据" in msg
        # push_up should have KB data
        assert "KB Cues" in msg or "器材" in msg

    def test_contains_task_instruction(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        msg = build_gym_user_message(profile, weekly_plan, training_day, kb)
        assert "任务" in msg
        assert "周一 (Day 1)" in msg

    def test_already_generated_context(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        already = '[{"day_label": "周一", "focus": "上肢推力"}]'
        msg = build_gym_user_message(
            profile, weekly_plan, training_day, kb,
            already_generated_json=already,
        )
        assert "已生成训练日历史" in msg
        assert "上肢推力" in msg

    def test_no_already_generated(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        msg = build_gym_user_message(profile, weekly_plan, training_day, kb)
        assert "已生成训练日历史" not in msg

    def test_warmup_notes_included_when_present(
        self, profile: UserProfile, weekly_plan: WeeklyPlan, kb: KnowledgeBase,
    ) -> None:
        """When training_day has warmup_notes, they should appear in prompt."""
        td_with_warmup = TrainingDay(
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
            estimated_duration_minutes=60,
            warmup_notes="① 弹力带肩外旋 → ② 胸椎旋转",
            cooldown_notes="① 胸肌拉伸 30秒 → ② 肩部拉伸 30秒",
        )
        msg = build_gym_user_message(profile, weekly_plan, td_with_warmup, kb)
        assert "PlanAgent 热身方案" in msg
        assert "弹力带肩外旋" in msg
        assert "PlanAgent 拉伸方案" in msg
        assert "胸肌拉伸" in msg

    def test_weight_hint_constraint_in_task(
        self, profile: UserProfile, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        """Task instruction should mention weight_hint constraint."""
        msg = build_gym_user_message(profile, weekly_plan, training_day, kb)
        assert "weight_hint" in msg

    def test_injury_guidance_included(
        self, weekly_plan: WeeklyPlan,
        training_day: TrainingDay, kb: KnowledgeBase,
    ) -> None:
        profile_with_injury = UserProfile(
            name="InjuredBob",
            age=30,
            gender="male",
            height_cm=180.0,
            weight_kg=80.0,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            injuries=[ContraindicationTag.knee_injury],
        )
        msg = build_gym_user_message(
            profile_with_injury, weekly_plan, training_day, kb,
        )
        assert "伤病" in msg


# ---------------------------------------------------------------------------
# Progression message builder tests
# ---------------------------------------------------------------------------


class TestBuildProgressionMessage:
    def test_contains_profile_info(self, profile: UserProfile) -> None:
        msg = build_gym_progression_message(profile, "[]")
        assert "GymBob" in msg
        assert "beginner" in msg

    def test_contains_sessions_json(self, profile: UserProfile) -> None:
        sessions_json = '[{"day_label": "周一", "focus": "上肢推力"}]'
        msg = build_gym_progression_message(profile, sessions_json)
        assert "上肢推力" in msg
        assert "4 周" in msg or "4周" in msg

    def test_contains_task_instruction(self, profile: UserProfile) -> None:
        msg = build_gym_progression_message(profile, "[]")
        assert "ProgressionWeek" in msg
        assert "减量周" in msg

    def test_contains_injury_info(self) -> None:
        """Progression message should include user injury info."""
        profile_injured = UserProfile(
            name="InjuredBob",
            age=30,
            gender="male",
            height_cm=180.0,
            weight_kg=80.0,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.bodyweight],
            injuries=[ContraindicationTag.wrist_injury],
        )
        msg = build_gym_progression_message(profile_injured, "[]")
        assert "wrist_injury" in msg
