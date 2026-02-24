"""
BMR / TDEE / nutrition target calculator.

All logic here is deterministic — no LLM involved.
Formulas:
  BMR  — Mifflin-St Jeor equation (most validated for general population)
  TDEE — BMR × activity multiplier
  Calorie target — TDEE ± goal adjustment
  Protein target — body-weight-based standard
"""
from __future__ import annotations

from fitness_agent.knowledge_base.models import ExperienceLevel, GoalType
from fitness_agent.user.models import UserProfile

# ---------------------------------------------------------------------------
# Activity level multipliers (TDEE = BMR × multiplier)
# ---------------------------------------------------------------------------
_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary":          1.2,   # desk job, little/no exercise
    "lightly_active":     1.375, # light exercise 1-3 days/week
    "moderately_active":  1.55,  # moderate exercise 3-5 days/week
    "very_active":        1.725, # hard exercise 6-7 days/week
    "extra_active":       1.9,   # physical job + hard exercise
}

# Training-day addition: accounts for structured sessions in the plan
# Added on top of activity multiplier to avoid double-counting
_SESSION_KCAL_PER_HOUR = 300.0   # conservative average for resistance training

# ---------------------------------------------------------------------------
# Calorie adjustment by goal (kcal/day relative to TDEE)
# ---------------------------------------------------------------------------
_GOAL_CALORIE_DELTA: dict[GoalType, int] = {
    GoalType.fat_loss:            -400,   # moderate deficit
    GoalType.muscle_gain:         +300,   # lean bulk surplus
    GoalType.body_recomposition:     0,   # maintenance
    GoalType.general_fitness:        0,   # maintenance
}

# ---------------------------------------------------------------------------
# Protein targets (g per kg body weight)
# ---------------------------------------------------------------------------
_PROTEIN_PER_KG: dict[GoalType, float] = {
    GoalType.fat_loss:            2.0,   # higher protein preserves muscle in deficit
    GoalType.muscle_gain:         2.0,   # supports hypertrophy
    GoalType.body_recomposition:  2.2,   # highest demand: simultaneous goals
    GoalType.general_fitness:     1.6,   # minimum effective dose
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
) -> float:
    """
    Mifflin-St Jeor BMR (kcal/day).

    Male:   10 × weight(kg) + 6.25 × height(cm) − 5 × age + 5
    Female: 10 × weight(kg) + 6.25 × height(cm) − 5 × age − 161
    Other:  average of male/female
    """
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender == "male":
        return round(base + 5, 1)
    elif gender == "female":
        return round(base - 161, 1)
    else:
        return round(base - 78, 1)   # midpoint


def calculate_tdee(
    bmr: float,
    activity_level: str,
    training_days_per_week: int,
    session_duration_minutes: int,
) -> float:
    """
    TDEE = BMR × activity_multiplier + training_session_expenditure.

    Training expenditure is added separately to avoid over-counting
    when the user's stated activity level already partially reflects workouts.
    """
    multiplier = _ACTIVITY_MULTIPLIERS.get(activity_level, 1.375)
    base_tdee = bmr * multiplier

    # Extra kcal from planned training sessions
    session_hours = session_duration_minutes / 60
    weekly_training_kcal = training_days_per_week * session_hours * _SESSION_KCAL_PER_HOUR
    daily_training_kcal = weekly_training_kcal / 7

    return round(base_tdee + daily_training_kcal, 1)


def calculate_calorie_target(tdee: float, goal: GoalType) -> float:
    """Daily calorie target adjusted for the user's goal."""
    return round(tdee + _GOAL_CALORIE_DELTA[goal], 1)


def calculate_protein_target(weight_kg: float, goal: GoalType) -> float:
    """Daily protein target in grams."""
    return round(weight_kg * _PROTEIN_PER_KG[goal], 1)


def enrich_profile(profile: UserProfile) -> UserProfile:
    """
    Compute and fill all calculated fields on a UserProfile in-place.

    Returns the same (mutated) profile for convenience.
    """
    bmr = calculate_bmr(
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        gender=profile.gender,
    )
    tdee = calculate_tdee(
        bmr=bmr,
        activity_level=profile.activity_level,
        training_days_per_week=profile.training_days_per_week,
        session_duration_minutes=profile.session_duration_minutes,
    )
    calorie_target = calculate_calorie_target(tdee, profile.goal)
    protein_target = calculate_protein_target(profile.weight_kg, profile.goal)

    # Pydantic v2: use model_copy to return updated instance
    return profile.model_copy(update=dict(
        bmr=bmr,
        tdee=tdee,
        daily_calorie_target=calorie_target,
        daily_protein_target_g=protein_target,
    ))
