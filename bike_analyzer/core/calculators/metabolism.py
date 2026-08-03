"""Metabolism calculators: BMR, TDEE, NEAT, EAT and daily expenditure.

Integrates with existing tracking data (rides, GPS) to provide realistic
energy expenditure estimates. Falls back to baseline BMR when tracking
data is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    prev_ts = None
    walk_seconds = 0.0
    for pt in gps_points:
        ts = pt.timestamp if hasattr(pt, "timestamp") else pt.get("timestamp")
        spd = pt.speed if hasattr(pt, "speed") else pt.get("speed")
        pt.altitude if hasattr(pt, "altitude") else pt.get("altitude")
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


AGE_BRACKETS = [(18, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 120)]
WEIGHT_BRACKETS = [(40, 59), (60, 74), (75, 89), (90, 110), (111, 200)]


def age_bracket(age: int) -> tuple[int, int]:
    """Return the (min, max) age bracket containing the given age."""
    for lo, hi in AGE_BRACKETS:
        if lo <= age <= hi:
            return (lo, hi)
    return AGE_BRACKETS[-1]


def weight_bracket(weight_kg: float) -> tuple[int, int]:
    """Return the (min, max) weight bracket containing the given weight."""
    for lo, hi in WEIGHT_BRACKETS:
        if lo <= weight_kg <= hi:
            return (lo, hi)
    return WEIGHT_BRACKETS[0] if weight_kg < WEIGHT_BRACKETS[0][0] else WEIGHT_BRACKETS[-1]


def _bracket_mid_age(bracket: tuple[int, int]) -> int:
    lo, hi = bracket
    return (lo + hi) // 2


def _bracket_mid_weight(bracket: tuple[int, int]) -> float:
    lo, hi = bracket
    return float(lo + hi) / 2.0


def reference_bmr(age: int, sex: str, weight_kg: float, height_cm: float | None = None) -> float:
    """Built-in mean BMR for an age/sex/weight bracket (Mifflin-St Jeor)."""
    a = _bracket_mid_age(age_bracket(age))
    w = _bracket_mid_weight(weight_bracket(weight_kg))
    h = height_cm if height_cm is not None else 170.0
    return calculate_bmr_mifflin(w, h, a, sex)


def reference_tdee(age: int, sex: str, weight_kg: float, activity_level: str, height_cm: float | None = None) -> float:
    """Built-in mean TDEE for an age/sex/weight bracket and activity level."""
    return calculate_tdee(reference_bmr(age, sex, weight_kg, height_cm), activity_level)


def reference_for_athlete(
    age: int, sex: str, weight_kg: float, activity_level: str, height_cm: float | None = None
) -> dict[str, Any]:
    """Return the built-in reference means (BMR/TDEE) for the athlete's bracket."""
    return {
        "age_bracket": list(age_bracket(age)),
        "weight_bracket": list(weight_bracket(weight_kg)),
        "bmr_kcal": round(reference_bmr(age, sex, weight_kg, height_cm), 1),
        "tdee_kcal": round(reference_tdee(age, sex, weight_kg, activity_level, height_cm), 1),
        "source": "builtin",
    }


def clamp_weight(value: float, lo: float = 0.0, hi: float = 4.0) -> float:
    """Clamp a multiplicative weight/coefficient to a safe range."""
    return max(lo, min(hi, value))


def adapt_weights_from_delta(
    sensor_value: float,
    reference_value: float,
    *,
    current_weight: float = 1.0,
    learning_rate: float = 0.1,
    confidence: float = 1.0,
) -> float:
    """Adapt a model coefficient (weight) toward the ratio sensor/reference.

    When the sensor-derived value diverges from the reference average, the
    weight moves toward sensor/reference so that weight*reference approaches
    the sensor value. The move is damped by the learning rate and by the
    sensor confidence (noisy sensors adapt slowly).
    """
    if reference_value <= 0 or sensor_value <= 0:
        return clamp_weight(current_weight)
    target = sensor_value / reference_value
    delta = (target - current_weight) * learning_rate * confidence
    return clamp_weight(current_weight + delta)


def sensor_confidence(
    sensor_value: float,
    reference_value: float,
    *,
    prior_confidence: float = 1.0,
    learning_rate: float = 0.05,
) -> float:
    """Update sensor-confidence weight toward 1 - relative deviation from reference.

    A sensor that tracks the reference mean closely earns high confidence; a
    sensor that systematically diverges (noisy / miscalibrated) earns low
    confidence and therefore contributes less to the blended estimate.
    """
    if reference_value <= 0 or sensor_value <= 0:
        return clamp_weight(prior_confidence, 0.0, 1.0)
    rel = abs(sensor_value - reference_value) / reference_value
    target = clamp_weight(1.0 / (1.0 + rel), 0.0, 1.0)
    delta = (target - prior_confidence) * learning_rate
    return clamp_weight(prior_confidence + delta, 0.0, 1.0)


@dataclass
class AdaptiveWeights:
    """Per-athlete adaptive model weights and sensor confidence.

    Coefficient weights scale the built-in reference means; sensor confidence
    weights scale how much each sensor-derived component contributes to the
    final blended estimate for the athlete.
    """

    activity_multiplier_w: float = 1.0
    neat_w: float = 1.0
    climb_bonus_w: float = 1.0
    sensor_bmr_conf: float = 1.0
    sensor_tdee_conf: float = 1.0
    learning_rate: float = 0.1
    confidence_lr: float = 0.05
    n_updates: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_multiplier_w": self.activity_multiplier_w,
            "neat_w": self.neat_w,
            "climb_bonus_w": self.climb_bonus_w,
            "sensor_bmr_conf": self.sensor_bmr_conf,
            "sensor_tdee_conf": self.sensor_tdee_conf,
            "learning_rate": self.learning_rate,
            "confidence_lr": self.confidence_lr,
            "n_updates": self.n_updates,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdaptiveWeights:
        if not data:
            return cls()
        return cls(
            activity_multiplier_w=float(data.get("activity_multiplier_w", 1.0)),
            neat_w=float(data.get("neat_w", 1.0)),
            climb_bonus_w=float(data.get("climb_bonus_w", 1.0)),
            sensor_bmr_conf=float(data.get("sensor_bmr_conf", 1.0)),
            sensor_tdee_conf=float(data.get("sensor_tdee_conf", 1.0)),
            learning_rate=float(data.get("learning_rate", 0.1)),
            confidence_lr=float(data.get("confidence_lr", 0.05)),
            n_updates=int(data.get("n_updates", 0) or 0),
        )


def calibrate_weights(
    weights: AdaptiveWeights,
    sensor_bmr: float,
    sensor_tdee: float,
    ref_bmr: float,
    ref_tdee: float,
) -> AdaptiveWeights:
    """Update a per-athlete AdaptiveWeights from one sensor-vs-reference sample.

    Both the model coefficients and the sensor-confidence weights are refined
    using the difference between the sensor-derived calculation and the general
    reference mean for the athlete's demographic bracket.
    """
    lr = weights.learning_rate
    clr = weights.confidence_lr

    weights.activity_multiplier_w = adapt_weights_from_delta(
        sensor_tdee,
        ref_tdee,
        current_weight=weights.activity_multiplier_w,
        learning_rate=lr,
        confidence=weights.sensor_tdee_conf,
    )
    weights.neat_w = adapt_weights_from_delta(
        sensor_tdee,
        ref_tdee,
        current_weight=weights.neat_w,
        learning_rate=lr,
        confidence=weights.sensor_tdee_conf,
    )
    weights.climb_bonus_w = adapt_weights_from_delta(
        sensor_tdee,
        ref_tdee,
        current_weight=weights.climb_bonus_w,
        learning_rate=lr,
        confidence=weights.sensor_tdee_conf,
    )
    weights.sensor_bmr_conf = sensor_confidence(
        sensor_bmr,
        ref_bmr,
        prior_confidence=weights.sensor_bmr_conf,
        learning_rate=clr,
    )
    weights.sensor_tdee_conf = sensor_confidence(
        sensor_tdee,
        ref_tdee,
        prior_confidence=weights.sensor_tdee_conf,
        learning_rate=clr,
    )
    weights.n_updates += 1
    return weights


def blended_expenditure(
    weights: AdaptiveWeights,
    reference: dict[str, Any],
    sensor: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Blend the reference mean with sensor-derived values using the weights.

    The reference component is adjusted by the coefficient weights; the sensor
    component is weighted by its confidence. Returns the final BMR/TDEE used
    for the athlete.
    """
    ref_bmr = float(reference.get("bmr_kcal", 0.0))
    ref_tdee = float(reference.get("tdee_kcal", 0.0))
    adj_ref_bmr = ref_bmr * weights.activity_multiplier_w
    adj_ref_tdee = ref_tdee * weights.activity_multiplier_w * weights.neat_w

    if sensor:
        s_bmr = float(sensor.get("bmr_kcal", 0.0) or 0.0)
        s_tdee = float(sensor.get("tdee_kcal", 0.0) or 0.0)
        if s_bmr > 0:
            bmr = weights.sensor_bmr_conf * s_bmr + (1.0 - weights.sensor_bmr_conf) * adj_ref_bmr
        else:
            bmr = adj_ref_bmr
        if s_tdee > 0:
            tdee = weights.sensor_tdee_conf * s_tdee + (1.0 - weights.sensor_tdee_conf) * adj_ref_tdee
        else:
            tdee = adj_ref_tdee
    else:
        bmr = adj_ref_bmr
        tdee = adj_ref_tdee

    return {
        "bmr_kcal": round(bmr, 1),
        "tdee_kcal": round(tdee, 1),
        "activity_multiplier_w": round(weights.activity_multiplier_w, 4),
        "neat_w": round(weights.neat_w, 4),
        "climb_bonus_w": round(weights.climb_bonus_w, 4),
        "sensor_bmr_conf": round(weights.sensor_bmr_conf, 4),
        "sensor_tdee_conf": round(weights.sensor_tdee_conf, 4),
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
