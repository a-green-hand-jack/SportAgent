"""Tests for KnowledgeBase loader and all query methods."""
import json
import pytest
from pathlib import Path

from fitness_agent.knowledge_base.loader import KnowledgeBase
from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    ExperienceLevel,
    GoalType,
    MovementPattern,
    MuscleGroup,
    RuleType,
)

TEST_DATA = Path(__file__).parent.parent / "data"


@pytest.fixture
def kb() -> KnowledgeBase:
    """KnowledgeBase backed by the small fixture data files in tests/data/."""
    return KnowledgeBase(
        exercises_path=TEST_DATA / "exercises.json",
        nutrition_path=TEST_DATA / "nutrition.json",
        rules_path=TEST_DATA / "rules.json",
        anatomy_path=TEST_DATA / "anatomy.json",
        nutrition_principles_path=TEST_DATA / "nutrition_principles.json",
    )


@pytest.fixture
def empty_kb(tmp_path: Path) -> KnowledgeBase:
    """KnowledgeBase pointing at non-existent files — should return empty lists."""
    return KnowledgeBase(
        exercises_path=tmp_path / "no_exercises.json",
        nutrition_path=tmp_path / "no_nutrition.json",
        rules_path=tmp_path / "no_rules.json",
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestLoading:
    def test_loads_exercises(self, kb: KnowledgeBase) -> None:
        assert len(kb.exercises) == 7

    def test_loads_foods(self, kb: KnowledgeBase) -> None:
        assert len(kb.foods) == 5

    def test_loads_rules(self, kb: KnowledgeBase) -> None:
        assert len(kb.rules) == 7

    def test_stats(self, kb: KnowledgeBase) -> None:
        stats = kb.stats()
        assert stats["exercises"] == 7
        assert stats["foods"] == 5
        assert stats["rules"] >= 7          # rules.json may grow over time
        assert stats["muscle_groups"] >= 1  # anatomy.json loaded

    def test_missing_files_return_empty(self, empty_kb: KnowledgeBase) -> None:
        assert empty_kb.exercises == []
        assert empty_kb.foods == []
        assert empty_kb.rules == []

    def test_skips_invalid_entries(self, tmp_path: Path) -> None:
        """Malformed entries are skipped; valid ones are loaded."""
        data = [
            {
                "id": "valid_exercise",
                "name": "Valid",
                "name_zh": "有效",
                "category": "strength",
                "equipment": ["bodyweight"],
                "primary_muscles": ["chest"],
                "difficulty": "beginner",
                "movement_pattern": "push",
            },
            {"id": "bad_entry", "name": "Missing required fields"},
        ]
        path = tmp_path / "exercises.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        kb = KnowledgeBase(exercises_path=path, nutrition_path=tmp_path / "x.json",
                           rules_path=tmp_path / "y.json")
        assert len(kb.exercises) == 1
        assert kb.exercises[0].id == "valid_exercise"


# ---------------------------------------------------------------------------
# Exercise queries
# ---------------------------------------------------------------------------

class TestExerciseQueries:
    def test_get_safe_exercises_excludes_contraindicated(
        self, kb: KnowledgeBase
    ) -> None:
        # User has knee injury — barbell_squat and running must be excluded
        safe = kb.get_safe_exercises(
            contraindications=[ContraindicationTag.knee_injury],
            available_equipment=[Equipment.barbell, Equipment.bodyweight,
                                 Equipment.pull_up_bar, Equipment.dumbbell,
                                 Equipment.bench, Equipment.cable_machine],
        )
        ids = [ex.id for ex in safe]
        assert "barbell_squat" not in ids
        assert "running" not in ids
        # push_up is safe for knee injury
        assert "push_up" in ids

    def test_get_safe_exercises_requires_equipment(
        self, kb: KnowledgeBase
    ) -> None:
        # User only has bodyweight — barbell exercises must be excluded
        safe = kb.get_safe_exercises(
            contraindications=[],
            available_equipment=[Equipment.bodyweight],
        )
        ids = [ex.id for ex in safe]
        assert "barbell_squat" not in ids
        assert "deadlift" not in ids
        assert "push_up" in ids
        assert "running" in ids

    def test_get_safe_exercises_no_injuries_all_equipment(
        self, kb: KnowledgeBase
    ) -> None:
        all_equipment = list(Equipment)
        safe = kb.get_safe_exercises(contraindications=[], available_equipment=all_equipment)
        # All 7 exercises should be available
        assert len(safe) == 7

    def test_filter_by_muscle_group(self, kb: KnowledgeBase) -> None:
        chest_exercises = kb.filter_exercises(
            kb.exercises, muscle_groups=[MuscleGroup.chest]
        )
        ids = [ex.id for ex in chest_exercises]
        assert "push_up" in ids
        assert "dumbbell_bench_press" in ids
        # Deadlift targets hamstrings/glutes/lower_back, not chest
        assert "deadlift" not in ids

    def test_filter_by_movement_pattern(self, kb: KnowledgeBase) -> None:
        push_exercises = kb.filter_exercises(
            kb.exercises, movement_patterns=[MovementPattern.push]
        )
        ids = [ex.id for ex in push_exercises]
        assert "push_up" in ids
        assert "dumbbell_bench_press" in ids
        assert "pull_up" not in ids
        assert "deadlift" not in ids

    def test_filter_by_difficulty(self, kb: KnowledgeBase) -> None:
        beginner = kb.filter_exercises(kb.exercises, difficulty=["beginner"])
        assert all(ex.difficulty.value == "beginner" for ex in beginner)

    def test_filter_by_equipment(self, kb: KnowledgeBase) -> None:
        barbell_only = kb.filter_exercises(
            kb.exercises, equipment=[Equipment.barbell]
        )
        ids = [ex.id for ex in barbell_only]
        assert "barbell_squat" in ids
        assert "deadlift" in ids
        assert "push_up" not in ids

    def test_filter_combined(self, kb: KnowledgeBase) -> None:
        result = kb.filter_exercises(
            kb.exercises,
            muscle_groups=[MuscleGroup.chest],
            difficulty=["beginner"],
        )
        assert all(ex.difficulty.value == "beginner" for ex in result)
        assert all(
            MuscleGroup.chest in ex.primary_muscles
            or MuscleGroup.chest in ex.secondary_muscles
            for ex in result
        )

    def test_get_exercise_by_id_found(self, kb: KnowledgeBase) -> None:
        ex = kb.get_exercise_by_id("pull_up")
        assert ex is not None
        assert ex.name_zh == "引体向上"

    def test_get_exercise_by_id_not_found(self, kb: KnowledgeBase) -> None:
        assert kb.get_exercise_by_id("nonexistent") is None


# ---------------------------------------------------------------------------
# Nutrition queries
# ---------------------------------------------------------------------------

class TestNutritionQueries:
    def test_get_food_by_english_name(self, kb: KnowledgeBase) -> None:
        food = kb.get_food_by_name("Chicken Breast")
        assert food is not None
        assert food.id == "chicken_breast"

    def test_get_food_by_name_case_insensitive(self, kb: KnowledgeBase) -> None:
        food = kb.get_food_by_name("chicken breast")
        assert food is not None

    def test_get_food_by_chinese_name(self, kb: KnowledgeBase) -> None:
        food = kb.get_food_by_name("鸡蛋")
        assert food is not None
        assert food.id == "egg_whole"

    def test_get_food_not_found(self, kb: KnowledgeBase) -> None:
        assert kb.get_food_by_name("nonexistent food") is None

    def test_search_foods_substring(self, kb: KnowledgeBase) -> None:
        results = kb.search_foods("chicken")
        assert len(results) == 1
        assert results[0].id == "chicken_breast"

    def test_search_foods_chinese_substring(self, kb: KnowledgeBase) -> None:
        results = kb.search_foods("蛋白")
        assert any(f.id == "whey_protein" for f in results)

    def test_search_foods_no_match(self, kb: KnowledgeBase) -> None:
        assert kb.search_foods("zzz_no_match") == []


# ---------------------------------------------------------------------------
# Rules queries
# ---------------------------------------------------------------------------

class TestRulesQueries:
    def test_get_rules_for_fat_loss_beginner(self, kb: KnowledgeBase) -> None:
        rules = kb.get_rules_for_context(GoalType.fat_loss, ExperienceLevel.beginner)
        ids = [r.id for r in rules]
        # fat_loss-specific rule
        assert "rule_calorie_deficit" in ids
        # applies_to_goals=[] means all goals
        assert "rule_protein_intake" in ids
        assert "rule_sleep" in ids
        # beginner-specific
        assert "rule_beginner_volume" in ids
        assert "rule_beginner_no_1rm" in ids
        # muscle_gain rule should NOT appear
        assert "rule_calorie_surplus" not in ids
        # intermediate rule should NOT appear
        assert "rule_intermediate_volume" not in ids

    def test_get_rules_for_muscle_gain_intermediate(self, kb: KnowledgeBase) -> None:
        rules = kb.get_rules_for_context(GoalType.muscle_gain, ExperienceLevel.intermediate)
        ids = [r.id for r in rules]
        assert "rule_calorie_surplus" in ids
        assert "rule_intermediate_volume" in ids
        assert "rule_calorie_deficit" not in ids
        assert "rule_beginner_volume" not in ids

    def test_universal_rules_appear_for_all_contexts(self, kb: KnowledgeBase) -> None:
        for goal in GoalType:
            for level in ExperienceLevel:
                rules = kb.get_rules_for_context(goal, level)
                ids = [r.id for r in rules]
                assert "rule_protein_intake" in ids, f"Missing universal rule for {goal}/{level}"
                assert "rule_sleep" in ids

    def test_get_constraint_rules_only_constraints(self, kb: KnowledgeBase) -> None:
        constraints = kb.get_constraint_rules(GoalType.fat_loss, ExperienceLevel.beginner)
        assert all(r.rule_type == RuleType.constraint for r in constraints)
        ids = [r.id for r in constraints]
        # rule_sleep is a recommendation, must not appear
        assert "rule_sleep" not in ids

    def test_format_rules_for_prompt_contains_descriptions(
        self, kb: KnowledgeBase
    ) -> None:
        text = kb.format_rules_for_prompt(GoalType.fat_loss, ExperienceLevel.beginner)
        assert "热量缺口" in text
        assert "[硬约束]" in text
        assert "[建议]" in text

    def test_format_rules_for_prompt_empty_kb(self, empty_kb: KnowledgeBase) -> None:
        text = empty_kb.format_rules_for_prompt(GoalType.general_fitness, ExperienceLevel.beginner)
        assert text == "（无特定规则约束）"


# ---------------------------------------------------------------------------
# Volume targets
# ---------------------------------------------------------------------------

class TestGetVolumeTargets:
    def test_returns_dict(self, kb: KnowledgeBase) -> None:
        targets = kb.get_volume_targets(ExperienceLevel.beginner)
        assert isinstance(targets, dict)
        assert len(targets) > 0

    def test_keys_are_muscle_id_strings(self, kb: KnowledgeBase) -> None:
        targets = kb.get_volume_targets(ExperienceLevel.beginner)
        for key in targets:
            assert isinstance(key, str)
            assert len(key) > 0

    def test_values_are_min_max_tuples(self, kb: KnowledgeBase) -> None:
        targets = kb.get_volume_targets(ExperienceLevel.beginner)
        for muscle_id, (min_sets, max_sets) in targets.items():
            assert isinstance(min_sets, int), f"{muscle_id}: min_sets should be int"
            assert isinstance(max_sets, int), f"{muscle_id}: max_sets should be int"
            assert min_sets > 0, f"{muscle_id}: min_sets should be positive"
            assert max_sets >= min_sets, f"{muscle_id}: max_sets should be >= min_sets"

    def test_beginner_volume_lower_than_intermediate(self, kb: KnowledgeBase) -> None:
        beginner = kb.get_volume_targets(ExperienceLevel.beginner)
        intermediate = kb.get_volume_targets(ExperienceLevel.intermediate)
        # At least some muscles should have higher targets for intermediate
        common = set(beginner.keys()) & set(intermediate.keys())
        assert len(common) > 0
        upgrades = sum(
            1 for m in common if intermediate[m][0] >= beginner[m][0]
        )
        assert upgrades > 0, "Intermediate targets should be >= beginner for most muscles"

    def test_chest_has_volume_target(self, kb: KnowledgeBase) -> None:
        targets = kb.get_volume_targets(ExperienceLevel.beginner)
        # chest is a key muscle group and should always be present
        assert "chest" in targets
        min_sets, max_sets = targets["chest"]
        assert min_sets >= 8  # beginner minimum should be substantial

    def test_empty_kb_returns_empty_dict(self, tmp_path: Path) -> None:
        # Need to pass all paths to non-existent files so nothing is loaded
        kb_empty = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            anatomy_path=tmp_path / "no_anatomy.json",
        )
        targets = kb_empty.get_volume_targets(ExperienceLevel.beginner)
        assert targets == {}


# ---------------------------------------------------------------------------
# WarmupTemplate queries
# ---------------------------------------------------------------------------

@pytest.fixture
def kb_with_warmup() -> KnowledgeBase:
    """KnowledgeBase with warmup templates + injury profiles from test fixtures."""
    return KnowledgeBase(
        exercises_path=TEST_DATA / "exercises.json",
        nutrition_path=TEST_DATA / "nutrition.json",
        rules_path=TEST_DATA / "rules.json",
        anatomy_path=TEST_DATA / "anatomy.json",
        nutrition_principles_path=TEST_DATA / "nutrition_principles.json",
        warmup_templates_path=TEST_DATA / "warmup_templates.json",
        injury_profiles_path=TEST_DATA / "injury_profiles.json",
    )


class TestWarmupTemplates:
    def test_loads_warmup_templates(self, kb_with_warmup: KnowledgeBase) -> None:
        """Should load all 3 templates from the test fixture."""
        assert len(kb_with_warmup.warmup_templates) == 3

    def test_template_ids_are_correct(self, kb_with_warmup: KnowledgeBase) -> None:
        ids = {t.id for t in kb_with_warmup.warmup_templates}
        assert "lower_body" in ids
        assert "upper_push" in ids
        assert "full_body" in ids

    def test_get_warmup_template_by_squat_pattern(self, kb_with_warmup: KnowledgeBase) -> None:
        """squat pattern should match lower_body template (highest overlap score)."""
        tmpl = kb_with_warmup.get_warmup_template(["squat"])
        assert tmpl is not None
        assert tmpl.id == "lower_body"

    def test_get_warmup_template_by_push_pattern(self, kb_with_warmup: KnowledgeBase) -> None:
        """push pattern should match upper_push template."""
        tmpl = kb_with_warmup.get_warmup_template(["push"])
        assert tmpl is not None
        assert tmpl.id == "upper_push"

    def test_get_warmup_template_returns_best_match(self, kb_with_warmup: KnowledgeBase) -> None:
        """When multiple patterns given, the template with most overlap wins."""
        # full_body covers squat+push+pull+hinge+core; lower_body covers squat+hinge
        # Providing [squat, push, pull, hinge, core] should score full_body highest
        tmpl = kb_with_warmup.get_warmup_template(["squat", "push", "pull", "hinge", "core"])
        assert tmpl is not None
        assert tmpl.id == "full_body"

    def test_get_warmup_template_returns_none_when_no_templates(
        self, tmp_path: Path
    ) -> None:
        """No templates loaded → returns None."""
        kb_empty = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            warmup_templates_path=None,
        )
        assert kb_empty.get_warmup_template(["squat"]) is None

    def test_warmup_templates_empty_when_path_none(self, tmp_path: Path) -> None:
        """warmup_templates_path=None → empty list (no crash)."""
        kb = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            warmup_templates_path=None,
        )
        assert kb.warmup_templates == []

    def test_format_warmup_templates_for_prompt_contains_sequence_marker(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """The formatted text must include the ① step marker."""
        text = kb_with_warmup.format_warmup_templates_for_prompt()
        assert "①" in text

    def test_format_warmup_templates_for_prompt_contains_template_names(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """All template names (Chinese) should appear in the formatted block."""
        text = kb_with_warmup.format_warmup_templates_for_prompt()
        assert "下肢训练热身" in text
        assert "上肢推力训练热身" in text
        assert "全身综合训练热身" in text

    def test_format_warmup_templates_empty_when_no_templates(
        self, tmp_path: Path
    ) -> None:
        """No templates → empty string."""
        kb = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            warmup_templates_path=None,
        )
        assert kb.format_warmup_templates_for_prompt() == ""


# ---------------------------------------------------------------------------
# InjuryProfile queries
# ---------------------------------------------------------------------------

class TestInjuryProfiles:
    def test_loads_injury_profiles(self, kb_with_warmup: KnowledgeBase) -> None:
        """Should load all 3 profiles from the test fixture."""
        assert len(kb_with_warmup.injury_profiles) == 3

    def test_get_injury_profile_by_tag(self, kb_with_warmup: KnowledgeBase) -> None:
        """knee_injury tag should return the knee profile."""
        profile = kb_with_warmup.get_injury_profile(ContraindicationTag.knee_injury)
        assert profile is not None
        assert profile.name_zh == "膝关节损伤"

    def test_get_injury_profile_returns_none_for_unknown_tag(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """A tag not in the fixture returns None."""
        # elbow_injury is not in the 3-entry test fixture
        profile = kb_with_warmup.get_injury_profile(ContraindicationTag.elbow_injury)
        assert profile is None

    def test_format_injury_guidance_empty_when_no_injuries(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """Empty injury list → empty string."""
        text = kb_with_warmup.format_injury_guidance_for_prompt([])
        assert text == ""

    def test_format_injury_guidance_contains_knee_injury_name(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """knee_injury tag → formatted text contains Chinese name."""
        text = kb_with_warmup.format_injury_guidance_for_prompt(
            [ContraindicationTag.knee_injury]
        )
        assert "膝关节损伤" in text

    def test_format_injury_guidance_contains_avoid_patterns(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """knee_injury avoids squat → text must mention squat."""
        text = kb_with_warmup.format_injury_guidance_for_prompt(
            [ContraindicationTag.knee_injury]
        )
        assert "squat" in text

    def test_format_injury_guidance_multiple_injuries(
        self, kb_with_warmup: KnowledgeBase
    ) -> None:
        """Multiple injuries → all names appear."""
        text = kb_with_warmup.format_injury_guidance_for_prompt(
            [ContraindicationTag.knee_injury, ContraindicationTag.wrist_injury]
        )
        assert "膝关节损伤" in text
        assert "手腕损伤" in text

    def test_format_injury_guidance_empty_when_profiles_not_loaded(
        self, tmp_path: Path
    ) -> None:
        """No profiles loaded → empty string even with valid tag."""
        kb = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            injury_profiles_path=None,
        )
        text = kb.format_injury_guidance_for_prompt([ContraindicationTag.knee_injury])
        assert text == ""


# ---------------------------------------------------------------------------
# Recipe queries
# ---------------------------------------------------------------------------

@pytest.fixture
def kb_with_recipes() -> KnowledgeBase:
    """KnowledgeBase with recipe templates from test fixtures."""
    return KnowledgeBase(
        exercises_path=TEST_DATA / "exercises.json",
        nutrition_path=TEST_DATA / "nutrition.json",
        rules_path=TEST_DATA / "rules.json",
        anatomy_path=TEST_DATA / "anatomy.json",
        nutrition_principles_path=TEST_DATA / "nutrition_principles.json",
        recipes_path=TEST_DATA / "recipes.json",
    )


class TestRecipeLoading:
    def test_load_recipes(self, kb_with_recipes: KnowledgeBase) -> None:
        """Should load all 8 recipes from the test fixture."""
        assert len(kb_with_recipes.recipes) == 8

    def test_recipe_ids_unique(self, kb_with_recipes: KnowledgeBase) -> None:
        ids = [r.id for r in kb_with_recipes.recipes]
        assert len(ids) == len(set(ids))

    def test_recipes_empty_when_path_none(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            recipes_path=None,
        )
        assert kb.recipes == []


class TestGetFoodById:
    def test_found(self, kb_with_recipes: KnowledgeBase) -> None:
        food = kb_with_recipes.get_food_by_id("chicken_breast")
        assert food is not None
        assert food.name_zh == "鸡胸肉"

    def test_not_found(self, kb_with_recipes: KnowledgeBase) -> None:
        assert kb_with_recipes.get_food_by_id("nonexistent_food") is None


class TestRecipeQueries:
    def test_get_recipes_by_meal_type(self, kb_with_recipes: KnowledgeBase) -> None:
        breakfasts = kb_with_recipes.get_recipes_by_meal_type("breakfast")
        assert len(breakfasts) == 2
        assert all(r.meal_type == "breakfast" for r in breakfasts)

    def test_get_recipes_by_meal_type_lunch(self, kb_with_recipes: KnowledgeBase) -> None:
        lunches = kb_with_recipes.get_recipes_by_meal_type("lunch")
        assert len(lunches) == 2

    def test_get_compatible_recipes_no_restriction(
        self, kb_with_recipes: KnowledgeBase
    ) -> None:
        """No restrictions → all recipes returned."""
        result = kb_with_recipes.get_compatible_recipes([])
        assert len(result) == 8

    def test_get_compatible_recipes_vegetarian(
        self, kb_with_recipes: KnowledgeBase
    ) -> None:
        """vegetarian → only recipes with dietary_flags or substitution_groups."""
        result = kb_with_recipes.get_compatible_recipes(["vegetarian"])
        # Recipes that natively satisfy OR have substitution for vegetarian
        assert len(result) > 0
        for r in result:
            assert (
                "vegetarian" in r.dietary_flags
                or "vegetarian" in r.substitution_groups
            ), f"Recipe {r.id} should be vegetarian-compatible"

    def test_get_compatible_recipes_vegan(
        self, kb_with_recipes: KnowledgeBase
    ) -> None:
        result = kb_with_recipes.get_compatible_recipes(["vegan"])
        assert len(result) > 0
        for r in result:
            assert "vegan" in r.dietary_flags or "vegan" in r.substitution_groups

    def test_compute_recipe_macros(self, kb_with_recipes: KnowledgeBase) -> None:
        """Deterministic macro computation from ingredients."""
        recipe = kb_with_recipes.get_recipes_by_meal_type("lunch")[0]
        # Should be chicken_rice_broccoli
        macros = kb_with_recipes.compute_recipe_macros(recipe)
        assert macros["calories"] > 0
        assert macros["protein_g"] > 0
        # Chicken 150g: 165*1.5=247.5 cal, Rice 200g: 130*2=260 cal, Broccoli 100g: 34 cal
        # Total ≈ 541.5 cal
        assert abs(macros["calories"] - 541.5) < 1.0

    def test_compute_recipe_macros_unknown_food_skipped(
        self, kb_with_recipes: KnowledgeBase
    ) -> None:
        """Unknown food_ids are silently skipped."""
        from fitness_agent.knowledge_base.models import RecipeIngredientTemplate, RecipeTemplate
        recipe = RecipeTemplate(
            id="test_unknown",
            name="Test",
            name_zh="测试",
            meal_type="lunch",
            ingredients=[
                RecipeIngredientTemplate(food_id="nonexistent", amount_g=100),
            ],
            steps_zh=["步骤1"],
        )
        macros = kb_with_recipes.compute_recipe_macros(recipe)
        assert macros["calories"] == 0.0

    def test_format_recipes_for_prompt(self, kb_with_recipes: KnowledgeBase) -> None:
        text = kb_with_recipes.format_recipes_for_prompt()
        assert "食谱参考库" in text
        # At least one recipe name should appear
        assert "燕麦鸡蛋香蕉碗" in text or "鸡胸肉西兰花饭" in text

    def test_format_recipes_for_prompt_with_subset(
        self, kb_with_recipes: KnowledgeBase
    ) -> None:
        breakfasts = kb_with_recipes.get_recipes_by_meal_type("breakfast")
        text = kb_with_recipes.format_recipes_for_prompt(breakfasts)
        assert "breakfast" in text
        # Lunch recipes should NOT appear
        assert "chicken_rice_broccoli" not in text

    def test_format_recipes_for_prompt_empty(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(
            exercises_path=tmp_path / "no_exercises.json",
            nutrition_path=tmp_path / "no_nutrition.json",
            rules_path=tmp_path / "no_rules.json",
            recipes_path=None,
        )
        assert kb.format_recipes_for_prompt() == ""
