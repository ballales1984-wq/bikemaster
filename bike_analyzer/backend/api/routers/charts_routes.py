"""Charts API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ...security import get_current_user
from ..routes import _ensure_ride_access, _current_athlete_id
from ..schemas import MeasurementCreate
from ...analytics.repositories.ride_repository import RideRepository

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/speed/{ride_id}")
async def speed_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate a speed profile chart PNG for a ride."""
    from ...analytics.analytics import create_speed_chart
    from ...models.models import GPSPoint
    from ...processing.processing import build_segments

    ride = await RideRepository().get_by_id(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]

    segments = build_segments(points)
    png = await asyncio.to_thread(create_speed_chart, segments)

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=speed.png"})


@router.get("/duration")
async def duration_chart(current_user: dict = Depends(get_current_user)):
    """Generate a ride duration distribution chart PNG."""
    from ...analytics.analytics import create_duration_chart
    from ...models.models import Ride

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = await RideRepository().list_all(athlete_id=_current_athlete_id(current_user), tenant_id=tenant_id)
    png = await asyncio.to_thread(create_duration_chart, [Ride(**r) for r in rides])

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=duration.png"})


@router.get("/distance/{ride_id}")
async def distance_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate a distance profile chart PNG for a ride."""
    from ...analytics.analytics import create_distance_chart
    from ...models.models import GPSPoint
    from ...processing.processing import build_segments

    ride = await RideRepository().get_by_id(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]

    segments = build_segments(points)
    png = await asyncio.to_thread(create_distance_chart, segments)

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=distance.png"})


@router.get("/elevation/{ride_id}")
async def elevation_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate an elevation profile chart PNG for a ride."""
    from ...analytics.analytics import create_elevation_chart
    from ...models.models import GPSPoint
    from ...processing.processing import build_segments

    ride = await RideRepository().get_by_id(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]

    segments = build_segments(points)
    png = await asyncio.to_thread(create_elevation_chart, segments)

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=elevation.png"})
