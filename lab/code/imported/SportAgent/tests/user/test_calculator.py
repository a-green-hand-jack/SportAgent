"""Tests for BMR / TDEE / nutrition target calculator."""
import pytest
from fitness_agent.knowledge_base.models import ExperienceLevel, GoalType, Equipment
from fitness_agent.user.calculator import (
    calculate_bmr,
    calculate_calorie_target,
    calculate_protein_target,
    calculate_tdee,
    enrich_profile,
)
from fitness_agent.user.models import UserProfile


# ---------------------------------------------------------------------------
# BMR
# ---------------------------------------------------------------------------

class TestCalculateBMR:
    def test_male_reference(self) -> None:
        # 75 kg, 175 cm, 28 yo male
        # 10*75 + 6.25*175 - 5*28 + 5 = 750 + 1093.75 - 140 + 5 = 1708.75
        bmr = calculate_bmr(weight_kg=75, height_cm=175, age=28, gender="male")
        assert bmr == pytest.approx(1708.75, abs=0.5)

    def test_female_reference(self) -> None:
        # 60 kg, 163 cm, 30 yo female
        # 10*60 + 6.25*163 - 5*30 - 161 = 600 + 1018.75 - 150 - 161 = 1307.75
        bmr = calculate_bmr(weight_kg=60, height_cm=163, age=30, gender="female")
        assert bmr == pytest.approx(1307.75, abs=0.5)

    def test_other_gender_is_midpoint(self) -> None:
        male_bmr = calculate_bmr(75, 175, 28, "male")
        female_bmr = calculate_bmr(75, 175, 28, "female")
        other_bmr = calculate_bmr(75, 175, 28, "other")
        # midpoint offset: male +5, female -161, other -78 (midpoint)
        assert female_bmr < other_bmr < male_bmr

    def test_heavier_person_has_higher_bmr(self) -> None:
        light = calculate_bmr(60, 175, 28, "male")
        heavy = calculate_bmr(90, 175, 28, "male")
        assert heavy > light

    def test_taller_person_has_higher_bmr(self) -> None:
        short = calculate_bmr(75, 160, 28, "male")
        tall = calculate_bmr(75, 190, 28, "male")
        assert tall > short

    def test_older_person_has_lower_bmr(self) -> None:
        young = calculate_bmr(75, 175, 20, "male")
        old = calculate_bmr(75, 175, 60, "male")
        assert old < young


# ---------------------------------------------------------------------------
# TDEE
# ---------------------------------------------------------------------------

class TestCalculateTDEE:
    def test_sedentary_is_lower_than_active(self) -> None:
        bmr = 1700.0
        sedentary = calculate_tdee(bmr, "sedentary", 3, 60)
        active = calculate_tdee(bmr, "very_active", 3, 60)
        assert active > sedentary

    def test_more_training_days_increases_tdee(self) -> None:
        bmr = 1700.0
        few = calculate_tdee(bmr, "lightly_active", 2, 60)
        many = calculate_tdee(bmr, "lightly_active", 5, 60)
        assert many > few

    def test_longer_sessions_increase_tdee(self) -> None:
        bmr = 1700.0
        short = calculate_tdee(bmr, "lightly_active", 3, 30)
        long_ = calculate_tdee(bmr, "lightly_active", 3, 90)
        assert long_ > short

    def test_tdee_always_greater_than_bmr(self) -> None:
        for activity in ["sedentary", "lightly_active", "moderately_active", "very_active"]:
            tdee = calculate_tdee(1600.0, activity, 3, 60)
            assert tdee > 1600.0, f"TDEE should exceed BMR for activity={activity}"

    def test_unknown_activity_level_uses_default(self) -> None:
        # Falls back to lightly_active (1.375)
        tdee = calculate_tdee(1700.0, "unknown_level", 3, 60)
        assert tdee > 1700.0


# ---------------------------------------------------------------------------
# Calorie target
# ---------------------------------------------------------------------------

class TestCalculateCalorieTarget:
    def test_fat_loss_is_deficit(self) -> None:
        tdee = 2500.0
        target = calculate_calorie_target(tdee, GoalType.fat_loss)
        assert target < tdee

    def test_muscle_gain_is_surplus(self) -> None:
        tdee = 2500.0
        target = calculate_calorie_target(tdee, GoalType.muscle_gain)
        assert target > tdee

    def test_recomposition_is_maintenance(self) -> None:
        tdee = 2500.0
        target = calculate_calorie_target(tdee, GoalType.body_recomposition)
        assert target == pytest.approx(tdee, abs=1)

    def test_general_fitness_is_maintenance(self) -> None:
        tdee = 2200.0
        target = calculate_calorie_target(tdee, GoalType.general_fitness)
        assert target == pytest.approx(tdee, abs=1)


# ---------------------------------------------------------------------------
# Protein target
# ---------------------------------------------------------------------------

class TestCalculateProteinTarget:
    def test_fat_loss_high_protein(self) -> None:
        # 75 kg × 2.0 g/kg = 150 g
        p = calculate_protein_target(75.0, GoalType.fat_loss)
        assert p == pytest.approx(150.0, abs=1)

    def test_recomposition_highest_protein(self) -> None:
        w = 80.0
        fat_loss = calculate_protein_target(w, GoalType.fat_loss)
        recomp = calculate_protein_target(w, GoalType.body_recomposition)
        general = calculate_protein_target(w, GoalType.general_fitness)
        # recomposition should be highest (2.2 g/kg)
        assert recomp >= fat_loss
        assert recomp > general

    def test_heavier_person_needs_more_protein(self) -> None:
        light = calculate_protein_target(60.0, GoalType.muscle_gain)
        heavy = calculate_protein_target(90.0, GoalType.muscle_gain)
        assert heavy > light


# ---------------------------------------------------------------------------
# enrich_profile
# ---------------------------------------------------------------------------

class TestEnrichProfile:
    def _base_profile(self, **kw) -> UserProfile:
        defaults = dict(
            name="Test",
            age=28,
            gender="male",
            height_cm=175.0,
            weight_kg=75.0,
            goal=GoalType.muscle_gain,
            experience_level=ExperienceLevel.beginner,
            training_days_per_week=3,
            session_duration_minutes=60,
            available_equipment=[Equipment.dumbbell],
            activity_level="lightly_active",
        )
        defaults.update(kw)
        return UserProfile(**defaults)

    def test_fills_all_computed_fields(self) -> None:
        profile = enrich_profile(self._base_profile())
        assert profile.bmr is not None
        assert profile.tdee is not None
        assert profile.daily_calorie_target is not None
        assert profile.daily_protein_target_g is not None

    def test_does_not_mutate_original(self) -> None:
        original = self._base_profile()
        enriched = enrich_profile(original)
        assert original.bmr is None       # original unchanged
        assert enriched.bmr is not None   # enriched copy has value

    def test_fat_loss_calorie_below_tdee(self) -> None:
        profile = enrich_profile(self._base_profile(goal=GoalType.fat_loss))
        assert profile.daily_calorie_target < profile.tdee

    def test_muscle_gain_calorie_above_tdee(self) -> None:
        profile = enrich_profile(self._base_profile(goal=GoalType.muscle_gain))
        assert profile.daily_calorie_target > profile.tdee

    def test_female_has_lower_bmr_than_male(self) -> None:
        male = enrich_profile(self._base_profile(gender="male"))
        female = enrich_profile(self._base_profile(gender="female"))
        assert female.bmr < male.bmr

    def test_protein_target_scales_with_weight(self) -> None:
        light = enrich_profile(self._base_profile(weight_kg=60))
        heavy = enrich_profile(self._base_profile(weight_kg=90))
        assert heavy.daily_protein_target_g > light.daily_protein_target_g
