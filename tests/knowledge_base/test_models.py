"""Tests for knowledge base Pydantic models."""
import pytest
from pydantic import ValidationError

from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Difficulty,
    Equipment,
    Exercise,
    ExerciseCategory,
    FoodCategory,
    FoodItem,
    GoalType,
    MovementPattern,
    MuscleGroup,
    RuleCategory,
    RuleType,
    TrainingRule,
    ExperienceLevel,
)


class TestExercise:
    def test_valid_exercise(self) -> None:
        ex = Exercise(
            id="barbell_squat",
            name="Barbell Back Squat",
            name_zh="杠铃深蹲",
            category=ExerciseCategory.strength,
            equipment=[Equipment.barbell, Equipment.bench],
            primary_muscles=[MuscleGroup.quads, MuscleGroup.glutes],
            secondary_muscles=[MuscleGroup.hamstrings, MuscleGroup.core],
            difficulty=Difficulty.intermediate,
            movement_pattern=MovementPattern.squat,
            contraindications=[ContraindicationTag.knee_injury],
            cues=["挺胸收腹", "膝盖与脚尖方向一致", "下蹲到大腿平行于地面"],
        )
        assert ex.id == "barbell_squat"
        assert Equipment.barbell in ex.equipment
        assert MuscleGroup.quads in ex.primary_muscles
        assert ContraindicationTag.knee_injury in ex.contraindications

    def test_exercise_optional_fields(self) -> None:
        ex = Exercise(
            id="push_up",
            name="Push Up",
            name_zh="俯卧撑",
            category=ExerciseCategory.strength,
            equipment=[Equipment.bodyweight],
            primary_muscles=[MuscleGroup.chest],
            difficulty=Difficulty.beginner,
            movement_pattern=MovementPattern.push,
        )
        assert ex.secondary_muscles == []
        assert ex.contraindications == []
        assert ex.cues == []
        assert ex.met_value is None

    def test_exercise_cardio_with_met(self) -> None:
        ex = Exercise(
            id="jumping_jacks",
            name="Jumping Jacks",
            name_zh="开合跳",
            category=ExerciseCategory.cardio,
            equipment=[Equipment.bodyweight],
            primary_muscles=[MuscleGroup.full_body],
            difficulty=Difficulty.beginner,
            movement_pattern=MovementPattern.cardio,
            met_value=8.0,
        )
        assert ex.met_value == 8.0


class TestFoodItem:
    def test_valid_food(self) -> None:
        food = FoodItem(
            id="chicken_breast",
            name="Chicken Breast",
            name_zh="鸡胸肉",
            category=FoodCategory.poultry,
            serving_size_g=100,
            calories=165,
            protein_g=31,
            carbs_g=0,
            fat_g=3.6,
            fiber_g=0,
        )
        assert food.protein_g == 31
        assert food.calories == 165

    def test_food_fiber_default(self) -> None:
        food = FoodItem(
            id="white_rice",
            name="White Rice (cooked)",
            name_zh="白米饭",
            category=FoodCategory.grain,
            serving_size_g=100,
            calories=130,
            protein_g=2.7,
            carbs_g=28.2,
            fat_g=0.3,
        )
        assert food.fiber_g == 0.0


class TestExerciseValidation:
    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValidationError):
            Exercise(
                id="bad",
                name="Bad",
                name_zh="错误",
                category="not_a_category",
                equipment=[Equipment.bodyweight],
                primary_muscles=[MuscleGroup.chest],
                difficulty=Difficulty.beginner,
                movement_pattern=MovementPattern.push,
            )

    def test_invalid_equipment_raises(self) -> None:
        with pytest.raises(ValidationError):
            Exercise(
                id="bad",
                name="Bad",
                name_zh="错误",
                category=ExerciseCategory.strength,
                equipment=["treadmill"],          # not a valid Equipment enum value
                primary_muscles=[MuscleGroup.chest],
                difficulty=Difficulty.beginner,
                movement_pattern=MovementPattern.push,
            )

    def test_invalid_muscle_group_raises(self) -> None:
        with pytest.raises(ValidationError):
            Exercise(
                id="bad",
                name="Bad",
                name_zh="错误",
                category=ExerciseCategory.strength,
                equipment=[Equipment.bodyweight],
                primary_muscles=["not_a_muscle"],
                difficulty=Difficulty.beginner,
                movement_pattern=MovementPattern.push,
            )

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            # Missing 'name_zh'
            Exercise(
                id="missing_field",
                name="Missing",
                category=ExerciseCategory.strength,
                equipment=[Equipment.bodyweight],
                primary_muscles=[MuscleGroup.chest],
                difficulty=Difficulty.beginner,
                movement_pattern=MovementPattern.push,
            )


class TestTrainingRule:
    def test_constraint_rule(self) -> None:
        rule = TrainingRule(
            id="rule_beginner_max_frequency",
            category=RuleCategory.frequency,
            applies_to_goals=[],
            applies_to_levels=[ExperienceLevel.beginner],
            rule_type=RuleType.constraint,
            description="初学者每个肌群每周训练频率不超过 3 次，两次训练间至少间隔 48 小时",
            parameters={"max_frequency_per_muscle": 3, "min_rest_hours": 48},
        )
        assert rule.rule_type == RuleType.constraint
        assert rule.parameters is not None
        assert rule.parameters["max_frequency_per_muscle"] == 3

    def test_rule_applies_to_all_goals(self) -> None:
        rule = TrainingRule(
            id="rule_sleep",
            category=RuleCategory.recovery,
            applies_to_goals=[],
            applies_to_levels=[],
            rule_type=RuleType.recommendation,
            description="每晚保持 7-9 小时睡眠，以支持肌肉恢复和激素水平",
        )
        # Empty lists mean "applies to all"
        assert rule.applies_to_goals == []
        assert rule.applies_to_levels == []
