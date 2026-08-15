"""Ride management REST API."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
from bike_analyzer.backend.analytics.terrain_enrichment import TerrainEnricher
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rides"])


def _terrain_enrichment_enabled() -> bool:
    try:
        from bike_analyzer.backend.settings import get_settings

        return get_settings().terrain_enrichment_enabled
    except Exception:
        return False


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


@router.get("/rides/{ride_id}/terrain")
async def get_ride_terrain(
    ride_id: int,
    enabled: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    """Return terrain-enriched GPS points for a ride.

    Requires the global ``terrain_enrichment_enabled`` setting to be True.
    """
    if not _terrain_enrichment_enabled():
        raise HTTPException(
            status_code=403,
            detail="Terrain enrichment is not enabled on this server",
        )
    tenant_id = current_user.get("tenant_id", current_user["id"])
    repo = RideRepository()
    ride = await repo.get_by_id(ride_id, tenant_id=tenant_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    if isinstance(gps_points, str):
        gps_points = json.loads(gps_points)

    from bike_analyzer.core.models import GPSPoint

    points = []
    for p in gps_points:
        if isinstance(p, str):
            p = json.loads(p)
        points.append(GPSPoint(**p))

    enricher = TerrainEnricher(enabled=True)
    try:
        enriched = enricher.enrich_ride(points)
    except Exception as exc:
        logger.exception("Terrain enrichment failed for ride %s", ride_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    terrain_features = []
    if hasattr(enricher, "snapshot"):
        terrain_features = enricher.snapshot()

    h3_summary = {}
    if hasattr(enricher, "h3_summary"):
        h3_summary = enricher.h3_summary()

    return {
        "ride_id": ride_id,
        "enriched": [pt.to_dict() for pt in enriched],
        "terrain_features": terrain_features,
        "h3_summary": h3_summary,
    }


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


@router.get("/rides/{ride_id}/map")
async def generate_ride_map(
    ride_id: int,
    provider: str = Query("folium", description="Map provider: folium or aethermap"),
    current_user: dict = Depends(get_current_user),
):
    """Generate an interactive map for a ride's GPS track.

    Supports the built-in Folium renderer and the AetherMap provider.
    GPS points are normalized (elevation -> altitude) before rendering.
    """
    from pathlib import Path

    from bike_analyzer.backend.db.database import get_ride as _get_ride
    from bike_analyzer.core.models import GPSPoint, RouteStatistics

    tenant_id = current_user.get("tenant_id", current_user["id"])
    ride = _get_ride(ride_id, tenant_id=tenant_id)
    print(f"DEBUG map endpoint: ride_id={ride_id}, get_ride={_get_ride}, gps_points type={type(ride.get('gps_points'))}, len={len(ride.get('gps_points') or [])}")
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    normalized = []
    for p in gps_points:
        if isinstance(p, str):
            p = json.loads(p)
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]

    if provider == "aethermap":
        stats = None
        if ride.get("distance_km") and ride.get("duration_minutes"):
            stats = RouteStatistics(
                total_distance_m=ride.get("distance_km", 0.0) * 1000.0,
                total_duration_s=ride.get("duration_minutes", 0.0) * 60.0,
                avg_speed_km_h=ride.get("avg_speed_kmh", 0.0),
                max_speed_km_h=ride.get("max_speed_kmh", 0.0),
                total_elevation_gain_m=ride.get("elevation_gain_m", 0.0),
            )
        return {
            "map_url": f"/api/v1/aethermap/ride/{ride_id}",
            "engine": "aethermap",
        }

    from ..maps.map_renderer import create_route_map

    base_dir = Path(__file__).resolve().parent.parent.parent / "static"
    safe_id = "".join(c if c.isalnum() or c == "_" else "_" for c in str(ride_id))
    path = base_dir / f"ride_{safe_id}_map.html"
    resolved = path.resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    try:
        create_route_map(points, output_path=str(resolved))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Map generation failed: {exc}") from exc
    return {"map_url": f"/static/{resolved.name}", "engine": "folium"}
