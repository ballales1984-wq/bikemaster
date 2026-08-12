"""Dashboard API routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from bike_analyzer.backend.analytics.dashboard import create_score_dashboard
from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
from bike_analyzer.backend.analytics.training_load import (
    calculate_atl_ctl_tsb,
    get_current_training_status,
)
from bike_analyzer.backend.models.models import Ride
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


def _current_athlete_id(current_user: dict) -> int:
    try:
        return int(current_user.get("athlete_id") or current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])

    repo = RideRepository()
    rides = await repo.list_all(athlete_id=athlete_id, tenant_id=tenant_id)
    ride_objects = [Ride(**r) for r in rides]

    from bike_analyzer.backend.db.database import get_athlete

    athlete = get_athlete(athlete_id, tenant_id) or {}

    total_rides = len(ride_objects)
    total_km = round(sum(r.distance_km for r in ride_objects), 1)
    total_hours = round(sum((r.duration_minutes or 0) for r in ride_objects) / 60.0, 1)
    total_calories = round(sum(r.calories or 0 for r in ride_objects), 0)

    summary = {
        "total_rides": total_rides,
        "total_km": total_km,
        "total_hours": total_hours,
        "total_calories": total_calories,
    }

    fitness = {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "status": "no_data"}
    if ride_objects:
        loads = calculate_atl_ctl_tsb(ride_objects)
        if loads:
            current = loads[-1]
            fitness = {
                "atl": round(current.atl, 1),
                "ctl": round(current.ctl, 1),
                "tsb": round(current.tsb, 1),
                "status": get_current_training_status(ride_objects)["status"],
            }

    weekly_progress = [0.0] * 7
    if ride_objects:
        today = datetime.now(UTC).date()
        day_km: dict[str, float] = {}
        for r in ride_objects:
            if r.date:
                d = datetime.fromisoformat(r.date).date()
                day_km[d.isoformat()] = day_km.get(d.isoformat(), 0.0) + (r.distance_km or 0.0)
        for i in range(7):
            d = today - timedelta(days=6 - i)
            weekly_progress[i] = round(day_km.get(d.isoformat(), 0.0), 1)

    trends = {"weekly_progress": weekly_progress}

    recent_rides = sorted(ride_objects, key=lambda r: r.date or "", reverse=True)[:10]
    recent_rides_list = [
        {
            "id": r.id,
            "date": r.date,
            "distance_km": r.distance_km,
            "duration_minutes": r.duration_minutes,
            "avg_speed_kmh": r.avg_speed_kmh,
            "elevation_gain_m": r.elevation_gain_m,
        }
        for r in recent_rides
    ]

    scores = create_score_dashboard(ride_objects, None)
    score_fields = {
        "performance": scores.get("performance", 0),
        "endurance": scores.get("endurance", 0),
        "recovery": scores.get("recovery", 0),
        "efficiency": scores.get("efficiency", 0),
    }

    return {
        "athlete": athlete,
        "summary": summary,
        "fitness": fitness,
        "trends": trends,
        "recent_rides": recent_rides_list,
        "scores": score_fields,
        "rides_count": total_rides,
    }
