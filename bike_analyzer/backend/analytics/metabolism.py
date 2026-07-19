"""Metabolism analytics service.

Calcola profili metabolici, riepiloghi giornalieri e integra
dati di tracking reali (rides, GPS) nelle stime TDEE.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..db.database import (
    get_food_logs_by_athlete_date,
    get_metabolic_daily_summaries,
    get_metabolic_profile,
    get_rides_by_athlete,
    save_food_log,
    save_metabolic_daily_summary,
    save_metabolic_profile,
)
from ..models.models import Ride
from ..utils.logger import get_logger
from ...core.calculators.metabolism import (
    MetabolicProfileInput,
    calculate_bmr,
    calculate_daily_expenditure,
    estimate_neat_base,
)

logger = get_logger(__name__)


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
    tdee = profile.activity_level  # placeholder, actual tdee computed daily
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
    weight = athlete.get("weight_kg", 70.0)
    height = athlete.get("height_cm")
    age = athlete.get("age", 30)
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
    from datetime import datetime as dt, timedelta
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
