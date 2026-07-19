"""Metabolism calculators: BMR, TDEE, NEAT, EAT and daily expenditure.

Integrates with existing tracking data (rides, GPS) to provide realistic
energy expenditure estimates. Falls back to baseline BMR when tracking
data is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..models import GPSPoint, Ride


@dataclass
class MetabolicProfileInput:
    """Input data for metabolic calculations."""
    weight_kg: float = 70.0
    height_cm: float | None = None
    age: int = 30
    fat_percentage: float | None = None
    sex: str = "male"
    bmr_formula: str = "mifflin"
    activity_level: str = "moderate"


SEX_MAP = {"male": "M", "female": "F"}
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
NEAT_DEFAULTS = {
    "sedentary": 200.0,
    "light": 300.0,
    "moderate": 400.0,
    "active": 550.0,
    "very_active": 750.0,
}
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack", "other"]


def calculate_bmr_mifflin(weight_kg: float, height_cm: float | None, age: int, sex: str) -> float:
    """Mifflin-St Jeor equation for Basal Metabolic Rate.

    Male: BMR = 10 * weight + 6.25 * height - 5 * age + 5
    Female: BMR = 10 * weight + 6.25 * height - 5 * age - 161
    """
    h = height_cm if height_cm is not None else 170.0
    base = 10.0 * weight_kg + 6.25 * h - 5.0 * age
    return base + (5.0 if sex == "male" else -161.0)


def calculate_bmr_cunningham(weight_kg: float, fat_percentage: float | None) -> float:
    """Cunningham equation using lean body mass.

    BMR = 500 + 22 * lean_mass_kg
    lean_mass = weight * (1 - fat_percentage / 100)
    """
    fat = fat_percentage if fat_percentage is not None else 20.0
    lean_mass = weight_kg * (1.0 - fat / 100.0)
    return 500.0 + 22.0 * lean_mass


def calculate_bmr(profile: MetabolicProfileInput) -> float:
    """Return BMR in kcal/day using the selected formula."""
    if profile.bmr_formula == "cunningham" and profile.fat_percentage is not None:
        return calculate_bmr_cunningham(profile.weight_kg, profile.fat_percentage)
    return calculate_bmr_mifflin(profile.weight_kg, profile.height_cm, profile.age, profile.sex)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Return Total Daily Energy Expenditure from BMR and activity level."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return max(bmr * multiplier, bmr)


def estimate_neat_base(activity_level: str) -> float:
    """Baseline Non-Exercise Activity Thermogenesis for the activity level."""
    return NEAT_DEFAULTS.get(activity_level, 400.0)


def _climb_bonus_kcal(elevation_gain_m: float | None) -> float:
    """Extra kcal from elevation gain (climbing is metabolically expensive)."""
    if elevation_gain_m is None or elevation_gain_m <= 0:
        return 0.0
    return float(elevation_gain_m) * 0.15


def _estimate_neat_from_gps(gps_points: list[dict[str, Any]] | list[GPSPoint]) -> float:
    """Estimate NEAT calories from low-speed GPS segments (walking, stairs)."""
    if not gps_points:
        return 0.0
    total = 0.0
    prev_ts = None
    prev_alt = None
    walk_seconds = 0.0
    for pt in gps_points:
        ts = pt.timestamp if hasattr(pt, "timestamp") else pt.get("timestamp")
        spd = pt.speed if hasattr(pt, "speed") else pt.get("speed")
        alt = pt.altitude if hasattr(pt, "altitude") else pt.get("altitude")
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
        if prev_ts is not None:
            dt = (ts - prev_ts).total_seconds()
            if dt > 0 and spd is not None and spd < 5.0:
                walk_seconds += dt
        prev_ts = ts
        prev_alt = alt
    if walk_seconds > 300:
        steps = int(walk_seconds * (1.2 / 0.9))
        return float(steps * 0.04)
    return 0.0


def calculate_ride_calories(ride: Ride) -> float:
    """Return calories for a ride using the existing physics/MET estimators."""
    from ..calculators.calories import estimate as _estimate

    if ride.calories and ride.calories > 0:
        return float(ride.calories)
    return _estimate(ride)


def calculate_daily_expenditure(
    profile: MetabolicProfileInput,
    rides: list[Ride] | list[dict[str, Any]],
    date: str,
) -> dict[str, Any]:
    """Compute full daily energy expenditure from profile and tracking data.

    Returns dict with bmr, neat, eat, climb_bonus, tdee, rides_count.
    """
    bmr = calculate_bmr(profile)
    neat = estimate_neat_base(profile.activity_level)
    eat = 0.0
    climb_bonus = 0.0
    rides_count = 0
    gps_neat = 0.0
    for r in rides:
        rc = calculate_ride_calories(r) if not isinstance(r, dict) else r.get("calories", 0.0) or 0.0
        eat += rc
        rides_count += 1
        cb = _climb_bonus_kcal(r.elevation_gain_m if not isinstance(r, dict) else r.get("elevation_gain_m"))
        climb_bonus += cb
        gps = r.gps_points if not isinstance(r, dict) else r.get("gps_points")
        gps_neat += _estimate_neat_from_gps(gps or [])
    neat = max(neat, gps_neat)
    tdee = max(bmr + neat + eat + climb_bonus, bmr)
    return {
        "bmr_kcal": round(bmr, 1),
        "neat_kcal": round(neat, 1),
        "eat_kcal": round(eat, 1),
        "climb_bonus_kcal": round(climb_bonus, 1),
        "tdee_kcal": round(tdee, 1),
        "rides_count": rides_count,
        "gps_neat_kcal": round(gps_neat, 1),
    }


@dataclass
class DailySummary:
    date: str
    bmr_kcal: float = 0.0
    neat_kcal: float = 0.0
    eat_kcal: float = 0.0
    climb_bonus_kcal: float = 0.0
    tdee_kcal: float = 0.0
    intake_kcal: float = 0.0
    balance_kcal: float = 0.0
    steps_estimated: int | None = None
    elevation_gain_estimated_m: float | None = None
    rides_count: int = 0
    gps_neat_kcal: float = 0.0
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
