"""Ride management REST API."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rides"])


class RideCreate(BaseModel):
    athlete_id: int | None = None
    date: str
    distance_km: float = 0
    duration_minutes: float = 0
    avg_speed_kmh: float = 0
    weight_kg: float = 70
    calories: float = 0
    heart_rate_avg: float | None = None
    elevation_gain_m: float | None = None
    gps_points: list[dict] | None = None
    title: str | None = None
    external_source: str | None = None
    external_id: str | None = None
    activity_type: str | None = None
    is_official: bool | None = None
    source: str | None = None


class RideUpdate(BaseModel):
    date: str | None = None
    distance_km: float | None = None
    duration_minutes: float | None = None
    avg_speed_kmh: float | None = None
    weight_kg: float | None = None
    calories: float | None = None
    heart_rate_avg: float | None = None
    elevation_gain_m: float | None = None
    gps_points: list[dict] | None = None
    title: str | None = None
    external_source: str | None = None
    external_id: str | None = None
    activity_type: str | None = None
    is_official: bool | None = None
    source: str | None = None


def _current_athlete_id(current_user: dict) -> int:
    try:
        return int(current_user.get("athlete_id") or current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


@router.get("/rides")
async def list_rides(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    sort: str = Query("date"),
    current_user: dict = Depends(get_current_user),
):
    """List rides for the current athlete."""
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    repo = RideRepository()
    rides = await repo.list_all(athlete_id=athlete_id, tenant_id=tenant_id)
    start = (page - 1) * page_size
    end = start + page_size
    page_rides = rides[start:end]
    for r in page_rides:
        if r.get("gps_points") and isinstance(r["gps_points"], str):
            r["gps_points"] = json.loads(r["gps_points"])
    return {"rides": page_rides, "total": len(rides)}


@router.get("/rides/count")
async def count_rides(current_user: dict = Depends(get_current_user)):
    """Return total ride count for the current athlete."""
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    repo = RideRepository()
    rides = await repo.list_all(athlete_id=athlete_id, tenant_id=tenant_id)
    return {"count": len(rides)}


@router.post("/rides")
async def create_ride(payload: RideCreate, current_user: dict = Depends(get_current_user)):
    """Create a new ride."""
    athlete_id = payload.athlete_id or _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    repo = RideRepository()
    data = payload.model_dump(exclude_none=True)
    data["athlete_id"] = athlete_id
    data["tenant_id"] = tenant_id
    if data.get("gps_points"):
        data["gps_points"] = json.dumps(data["gps_points"])
    ride_id = await repo.save(data)
    ride = await repo.get_by_id(ride_id, tenant_id=tenant_id)
    if ride and ride.get("gps_points") and isinstance(ride["gps_points"], str):
        ride["gps_points"] = json.loads(ride["gps_points"])
    return ride or {}


@router.get("/rides/{ride_id}")
async def get_ride(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Get a ride by ID."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    repo = RideRepository()
    ride = await repo.get_by_id(ride_id, tenant_id=tenant_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.get("gps_points") and isinstance(ride["gps_points"], str):
        ride["gps_points"] = json.loads(ride["gps_points"])
    return ride


@router.put("/rides/{ride_id}")
async def update_ride(
    ride_id: int,
    payload: RideUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a ride."""
    from bike_analyzer.backend.db.database import get_ride, update_ride

    tenant_id = current_user.get("tenant_id", current_user["id"])
    existing = get_ride(ride_id, tenant_id=tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ride not found")
    data = payload.model_dump(exclude_none=True)
    if data.get("gps_points"):
        data["gps_points"] = json.dumps(data["gps_points"])
    update_ride(ride_id, data)
    ride = get_ride(ride_id, tenant_id=tenant_id)
    if ride and ride.get("gps_points") and isinstance(ride["gps_points"], str):
        ride["gps_points"] = json.loads(ride["gps_points"])
    return ride or {}


@router.delete("/rides/{ride_id}")
async def delete_ride(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a ride."""
    from bike_analyzer.backend.db.database import delete_ride, get_ride

    tenant_id = current_user.get("tenant_id", current_user["id"])
    existing = get_ride(ride_id, tenant_id=tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ride not found")
    delete_ride(ride_id)
    return None
