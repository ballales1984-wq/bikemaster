"""Metabolism analytics service.

Calcola profili metabolici, riepiloghi giornalieri e integra
dati di tracking reali (rides, GPS) nelle stime TDEE.
"""

from __future__ import annotations

from ...core.calculators.metabolism import (
    AdaptiveWeights,
    MetabolicProfileInput,
    blended_expenditure,
    calculate_bmr,
    calculate_daily_expenditure,
    calibrate_weights,
    estimate_neat_base,
    reference_for_athlete,
)
from ..db.database import (
    get_athlete as _get_athlete_export,
)
from ..db.database import (
    get_food_logs_by_athlete_date,
    get_metabolic_adaptive_weights,
    get_metabolic_profile,
    get_metabolic_reference_value,
    get_rides_by_athlete,
    save_metabolic_adaptive_weights,
    save_metabolic_daily_summary,
    save_metabolic_profile,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


def resolve_reference_value(athlete: dict, profile: dict | None, tenant_id: int = 0) -> dict:
    """Resolve the reference mean (imported if present, else built-in) for the athlete."""
    sex = (profile or {}).get("sex") or athlete.get("sex", "male")
    activity_level = (profile or {}).get("activity_level") or athlete.get("activity_level", "moderate")
    age = int(athlete.get("age") or 30)
    weight = float(athlete.get("weight_kg") or 70.0)
    height = athlete.get("height_cm")
    imported = get_metabolic_reference_value(sex, age, weight, activity_level, tenant_id)
    if imported and imported.get("bmr_kcal") is not None:
        ref_tdee = imported["tdee_kcal"]
        if not ref_tdee:
            ref_tdee = reference_for_athlete(age, sex, weight, activity_level, height)["tdee_kcal"]
        return {
            "bmr_kcal": float(imported["bmr_kcal"]),
            "tdee_kcal": float(ref_tdee),
            "age_bracket": [imported["age_bracket_lo"], imported["age_bracket_hi"]],
            "weight_bracket": [imported["weight_bracket_lo"], imported["weight_bracket_hi"]],
            "source": imported.get("source", "import"),
        }
    return reference_for_athlete(age, sex, weight, activity_level, height)


def get_athlete_weights(athlete_id: int, tenant_id: int = 0) -> AdaptiveWeights:
    """Return the per-athlete adaptive weights (fresh if none stored)."""
    row = get_metabolic_adaptive_weights(athlete_id, tenant_id)
    return AdaptiveWeights.from_dict(row or {})


def calibrate_athlete(
    athlete_id: int,
    sensor_bmr: float | None,
    sensor_tdee: float | None,
    date: str | None = None,
    tenant_id: int = 0,
) -> dict:
    """Compare sensor-derived values with the reference mean and update weights.

    Both the model coefficients and the sensor-confidence weights are refined
    from the difference between the sensor calculation and the general reference
    mean for the athlete's demographic bracket. Returns the updated weights.
    """
    athlete = _get_athlete_export(athlete_id, tenant_id) or {}
    if not athlete:
        athlete = {"sex": "male", "age": 30, "weight_kg": 70.0}
    profile = get_metabolic_profile(athlete_id, tenant_id)
    reference = resolve_reference_value(athlete, profile, tenant_id)

    if sensor_bmr is None or sensor_tdee is None:
        rides = get_rides_by_athlete(athlete_id, tenant_id)
        day_rides = [r for r in rides if r.get("date") == date] if date else rides
        activity_level = (profile or {}).get("activity_level", "moderate") if profile else "moderate"
        profile_input = MetabolicProfileInput(
            weight_kg=athlete.get("weight_kg") or 70.0,
            height_cm=athlete.get("height_cm"),
            age=athlete.get("age") or 30,
            fat_percentage=athlete.get("fat_percentage"),
            sex=(profile or {}).get("sex", "male") if profile else "male",
            bmr_formula=(profile or {}).get("bmr_formula", "mifflin") if profile else "mifflin",
            activity_level=activity_level,
        )
        expenditure = calculate_daily_expenditure(profile_input, day_rides, date or "")
        sensor_bmr = expenditure["bmr_kcal"]
        sensor_tdee = expenditure["tdee_kcal"]

    weights = get_athlete_weights(athlete_id, tenant_id)
    calibrated = calibrate_weights(
        weights,
        float(sensor_bmr),
        float(sensor_tdee),
        float(reference["bmr_kcal"]),
        float(reference["tdee_kcal"]),
    )
    save_metabolic_adaptive_weights(calibrated.to_dict(), athlete_id, tenant_id)
    return {
        "athlete_id": athlete_id,
        "reference": reference,
        "sensor": {"bmr_kcal": round(float(sensor_bmr), 1), "tdee_kcal": round(float(sensor_tdee), 1)},
        "weights": calibrated.to_dict(),
    }


def recalculate_daily_summary_calibrated(athlete_id: int, date: str, tenant_id: int = 0) -> dict:
    """Recalculate the daily summary using reference + adaptive weights."""
    athlete = _get_athlete_export(athlete_id, tenant_id) or {}
    profile = get_metabolic_profile(athlete_id, tenant_id)
    reference = resolve_reference_value(athlete, profile, tenant_id)
    weights = get_athlete_weights(athlete_id, tenant_id)

    rides = get_rides_by_athlete(athlete_id, tenant_id)
    day_rides = [r for r in rides if r.get("date") == date]
    activity_level = (profile or {}).get("activity_level", "moderate") if profile else "moderate"
    profile_input = MetabolicProfileInput(
        weight_kg=athlete.get("weight_kg") or 70.0,
        height_cm=athlete.get("height_cm"),
        age=athlete.get("age") or 30,
        fat_percentage=athlete.get("fat_percentage"),
        sex=(profile or {}).get("sex", "male") if profile else "male",
        bmr_formula=(profile or {}).get("bmr_formula", "mifflin") if profile else "mifflin",
        activity_level=activity_level,
    )
    sensor_expenditure = calculate_daily_expenditure(profile_input, day_rides, date)
    merged = blended_expenditure(weights, reference, sensor_expenditure)

    food_logs = get_food_logs_by_athlete_date(athlete_id, date, tenant_id=tenant_id)
    intake = sum(float(f.get("kcal", 0) or 0) for f in food_logs)
    balance = round(intake - merged["tdee_kcal"], 1)
    summary = {
        "athlete_id": athlete_id,
        "tenant_id": tenant_id,
        "date": date,
        "bmr_kcal": merged["bmr_kcal"],
        "neat_kcal": sensor_expenditure["neat_kcal"],
        "eat_kcal": sensor_expenditure["eat_kcal"],
        "climb_bonus_kcal": round(sensor_expenditure["climb_bonus_kcal"] * weights.climb_bonus_w, 1),
        "tdee_kcal": merged["tdee_kcal"],
        "intake_kcal": round(intake, 1),
        "balance_kcal": balance,
        "rides_count": len(day_rides),
        "gps_neat_kcal": sensor_expenditure["gps_neat_kcal"],
        "notes": None,
    }
    save_metabolic_daily_summary(summary, tenant_id)
    return summary


def compute_metabolic_profile(athlete: dict, *, override: dict | None = None) -> dict:
    """Calcola e restituisce il profilo metabolico per un atleta."""
    data = {
        "weight_kg": athlete.get("weight_kg", 70.0),
        "height_cm": athlete.get("height_cm"),
        "age": athlete.get("age", 30),
        "fat_percentage": athlete.get("fat_percentage"),
        "sex": athlete.get("sex", "male"),
        "bmr_formula": athlete.get("bmr_formula", "mifflin"),
        "activity_level": athlete.get("activity_level", "moderate"),
    }
    if override:
        data.update({k: v for k, v in override.items() if v is not None})
    profile = MetabolicProfileInput(**data)
    bmr = calculate_bmr(profile)
    return {
        "sex": data["sex"],
        "bmr_formula": data["bmr_formula"],
        "activity_level": data["activity_level"],
        "bmr_kcal": round(bmr, 1),
        "tdee_kcal": round(bmr * estimate_neat_base(data["activity_level"]) / 1000 * 1000, 1),
        "notes": data.get("notes"),
    }


def ensure_metabolic_profile(athlete_id: int, tenant_id: int = 0) -> dict:
    """Garantisce che esista un profilo metabolico per l'atleta."""
    existing = get_metabolic_profile(athlete_id, tenant_id)
    if existing:
        return existing
    return {}


def recalculate_daily_summary(athlete_id: int, date: str, tenant_id: int = 0) -> dict:
    """Ricalcola e salva il riepilogo metabolico giornaliero per una data."""
    profile = get_metabolic_profile(athlete_id, tenant_id)
    if not profile:
        profile = ensure_metabolic_profile(athlete_id, tenant_id)
    athlete = {}
    try:
        from ..db.database import get_athlete as _get_athlete
        athlete = _get_athlete(athlete_id, tenant_id) or {}
    except Exception:
        pass
    if not profile and athlete:
        profile = compute_metabolic_profile(athlete)
        save_metabolic_profile(profile, athlete_id, tenant_id)
        profile = get_metabolic_profile(athlete_id, tenant_id) or profile
    rides = get_rides_by_athlete(athlete_id, tenant_id)
    day_rides = [r for r in rides if r.get("date") == date]
    activity_level = profile.get("activity_level", "moderate") if profile else "moderate"
    weight = athlete.get("weight_kg") or 70.0
    height = athlete.get("height_cm")
    age = athlete.get("age") or 30
    fat = athlete.get("fat_percentage")
    sex = profile.get("sex", "male") if profile else "male"
    bmr_formula = profile.get("bmr_formula", "mifflin") if profile else "mifflin"
    profile_input = MetabolicProfileInput(
        weight_kg=weight,
        height_cm=height,
        age=age,
        fat_percentage=fat,
        sex=sex,
        bmr_formula=bmr_formula,
        activity_level=activity_level,
    )
    expenditure = calculate_daily_expenditure(profile_input, day_rides, date)
    food_logs = get_food_logs_by_athlete_date(athlete_id, date, tenant_id=tenant_id)
    intake = sum(float(f.get("kcal", 0) or 0) for f in food_logs)
    balance = round(intake - expenditure["tdee_kcal"], 1)
    summary = {
        "athlete_id": athlete_id,
        "tenant_id": tenant_id,
        "date": date,
        **expenditure,
        "intake_kcal": round(intake, 1),
        "balance_kcal": balance,
        "rides_count": len(day_rides),
        "notes": None,
    }
    if day_rides:
        total_elev = sum(float(r.get("elevation_gain_m") or 0) for r in day_rides)
        if total_elev > 0:
            summary["elevation_gain_estimated_m"] = round(total_elev, 1)
    save_metabolic_daily_summary(summary, tenant_id)
    return summary


def recalculate_range(athlete_id: int, start_date: str, end_date: str, tenant_id: int = 0) -> list[dict]:
    """Ricalcola i riepiloghi per un intervallo di date."""
    results = []
    from datetime import datetime as dt
    from datetime import timedelta
    try:
        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return results
    current = start
    while current <= end:
        ds = current.isoformat()
        results.append(recalculate_daily_summary(athlete_id, ds, tenant_id))
        current += timedelta(days=1)
    return results
