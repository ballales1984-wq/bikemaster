"""Athlete profile management REST API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from bike_analyzer.backend.api.routes import _athlete_profile_data, _current_athlete_id, _ensure_int_user_id
from bike_analyzer.backend.api.schemas import AthleteCreate, AthleteUpdate
from bike_analyzer.backend.db.database import (
    delete_athlete,
    get_athlete,
    get_athlete_history,
    get_athlete_metric_log,
    get_athletes_by_user,
    log_athlete_metric,
    save_athlete,
    update_athlete,
)
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["athletes"])


class MetricLogCreate(BaseModel):
    metric_type: str
    value: float
    unit: str | None = None
    note: str | None = None
    source: str = "manual"


def _profile_complete(athlete: dict | None) -> bool:
    if not athlete:
        return False
    return (
        athlete.get("age") is not None
        and athlete.get("weight_kg") is not None
        and (athlete.get("experience_level") or "").strip() != ""
    )


@router.get("/athletes/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    athlete_id = _current_athlete_id(current_user)
    athlete = get_athlete(athlete_id)
    if not athlete:
        athlete = _auto_create_athlete(athlete_id, current_user)
    return {
        "athlete": athlete,
        "profile_complete": _profile_complete(athlete),
    }


@router.put("/athletes/me")
async def update_my_profile(
    updates: AthleteUpdate,
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    athlete = get_athlete(athlete_id)
    if not athlete:
        athlete = _auto_create_athlete(athlete_id, current_user, updates.model_dump(exclude_unset=True))
        return {
            "athlete": athlete,
            "profile_complete": _profile_complete(athlete),
        }
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        return {
            "athlete": athlete,
            "profile_complete": _profile_complete(athlete),
        }
    ok = update_athlete(athlete_id, update_data)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update athlete")
    athlete = get_athlete(athlete_id)
    return {
        "athlete": athlete,
        "profile_complete": _profile_complete(athlete),
    }


@router.get("/athletes/me/history")
async def get_my_history(
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    history = get_athlete_history(athlete_id, limit=limit)
    return {"history": history}


@router.get("/athletes/me/metric-log")
async def get_my_metric_log(
    metric_type: str = Query(...),
    days: int = Query(365, ge=1, le=3650),
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    series = get_athlete_metric_log(athlete_id, metric_type, days=days)
    return {"series": series}


@router.get("/athletes/mine")
async def list_my_athletes(current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["id"])
    athletes = get_athletes_by_user(user_id)
    return {
        "athletes": [{"id": a["id"], "name": a.get("name"), "email": a.get("email")} for a in athletes],
    }


@router.post("/athletes/mine")
async def create_my_athlete(
    data: AthleteCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    athlete_data = data.model_dump()
    athlete_id = save_athlete(athlete_data, user_id=user_id)
    return {"athlete_id": athlete_id}


@router.delete("/athletes/mine/{athlete_id}")
async def delete_my_athlete(
    athlete_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    ok = delete_athlete(athlete_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return {"status": "deleted"}


def _assert_athlete_ownership(athlete_id: int, current_user: dict) -> dict:
    """Fetch an athlete and enforce that it belongs to ``current_user``.

    Raises 404 if the athlete doesn't exist and 403 if it belongs to another user.
    Admins bypass ownership checks.
    """
    user_id = _ensure_int_user_id(current_user)
    if current_user.get("is_admin"):
        athlete = get_athlete(athlete_id)
        if not athlete:
            raise HTTPException(status_code=404, detail="Athlete not found")
        return athlete
    athlete = get_athlete(athlete_id, tenant_id=user_id)
    if athlete is None:
        athlete_fallback = get_athlete(athlete_id)
        if athlete_fallback is None:
            raise HTTPException(status_code=404, detail="Athlete not found")
        if athlete_fallback.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Accesso riservato al proprietario")
        athlete = athlete_fallback
    return athlete


@router.get("/athletes")
async def list_athletes(current_user: dict = Depends(get_current_user)):
    user_id = _ensure_int_user_id(current_user)
    athletes = get_athletes_by_user(user_id)
    return {"athletes": athletes}


@router.post("/athletes")
async def create_athlete(
    data: AthleteCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    athlete_data = data.model_dump()
    if not athlete_data.get("age") or not athlete_data.get("weight_kg") or not athlete_data.get("experience_level"):
        raise HTTPException(status_code=422, detail="age, weight_kg and experience_level are required")
    athlete_id = save_athlete(athlete_data, user_id=user_id)
    athlete = get_athlete(athlete_id)
    return {"id": athlete_id, "athlete": athlete}


@router.get("/athletes/{athlete_id}")
async def get_athlete_by_id(
    athlete_id: int,
    current_user: dict = Depends(get_current_user),
):
    athlete = _assert_athlete_ownership(athlete_id, current_user)
    return athlete


@router.put("/athletes/{athlete_id}")
async def update_athlete_by_id(
    athlete_id: int,
    updates: AthleteUpdate,
    current_user: dict = Depends(get_current_user),
):
    athlete = _assert_athlete_ownership(athlete_id, current_user)
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        return athlete
    ok = update_athlete(athlete_id, update_data)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update athlete")
    athlete = get_athlete(athlete_id)
    return athlete


@router.post("/athletes/{athlete_id}/metrics")
async def log_athlete_metric_endpoint(
    athlete_id: int,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
):
    _assert_athlete_ownership(athlete_id, current_user)
    metric_type = str(data.get("metric_type") or next(iter(data.keys()), "manual"))
    value = data.get("value")
    if value is None:
        for k, v in data.items():
            if isinstance(v, (int, float)):
                value = float(v)
                metric_type = k
                break
    if metric_type is None or value is None:
        raise HTTPException(status_code=422, detail="metric_type and value required")
    metric_id = log_athlete_metric(
        athlete_id,
        metric_type,
        float(value),
        unit=data.get("unit"),
        note=data.get("note"),
        source=data.get("source", "manual"),
    )
    return {"id": metric_id}


def _auto_create_athlete(athlete_id: int, current_user: dict, updates: dict | None = None) -> dict:
    user_id = int(current_user["id"])
    data: dict[str, Any] = {"name": current_user.get("username") or f"Athlete {athlete_id}"}
    if updates:
        data.update(updates)
    new_id = save_athlete(data, athlete_id=athlete_id, user_id=user_id)
    return get_athlete(new_id) or data


@router.get("/athlete/state")
async def get_athlete_state(current_user: dict = Depends(get_current_user)):
    athlete_id = _current_athlete_id(current_user)
    from ...analytics.athlete_state.service import AthleteStateService
    from ...analytics.repositories.athlete_repository import AthleteRepository
    from ...analytics.repositories.ride_repository import RideRepository
    from ...models.models import AthleteProfile, Ride

    rides_data = await RideRepository().list_all(athlete_id=athlete_id)
    rides = [Ride(**r) for r in rides_data]
    athlete_data = await AthleteRepository().get_by_id(athlete_id)
    athlete_profile = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else None
    service = AthleteStateService()
    state = await service.calculate_current_state(athlete_id=athlete_id, rides=rides, athlete_profile=athlete_profile)
    return state.to_dict()
