"""Core calculators - domain-level calculation functions."""

from .metabolism import (
    MEAL_TYPES,
    ACTIVITY_MULTIPLIERS,
    NEAT_DEFAULTS,
    MetabolicProfileInput,
    calculate_bmr,
    calculate_bmr_cunningham,
    calculate_bmr_mifflin,
    calculate_daily_expenditure,
    calculate_ride_calories,
    calculate_tdee,
    estimate_neat_base,
    _climb_bonus_kcal,
    _estimate_neat_from_gps,
    DailySummary,
)
from .power import intensity_factor, normalized_power_approx, training_stress_score
from .stress import ewma

__all__ = [
    "normalized_power_approx",
    "training_stress_score",
    "intensity_factor",
    "ewma",
    "MEAL_TYPES",
    "ACTIVITY_MULTIPLIERS",
    "NEAT_DEFAULTS",
    "MetabolicProfileInput",
    "calculate_bmr",
    "calculate_bmr_cunningham",
    "calculate_bmr_mifflin",
    "calculate_daily_expenditure",
    "calculate_ride_calories",
    "calculate_tdee",
    "estimate_neat_base",
    "_climb_bonus_kcal",
    "_estimate_neat_from_gps",
    "DailySummary",
]
