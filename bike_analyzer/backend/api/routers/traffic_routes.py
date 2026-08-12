"""Traffic API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/traffic", tags=["traffic"])


@router.get("/road-types")
async def get_road_types(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(2.0),
):
    """Get road type distribution for an area using OSM Overpass."""
    from ...traffic.overpass_client import get_road_type_summary

    points = [{"lat": lat, "lon": lon}]
    summary = get_road_type_summary(points)
    return {"lat": lat, "lon": lon, "radius_km": radius_km, "road_types": summary}


@router.get("/bike-infrastructure")
async def get_bike_infrastructure(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(2.0),
):
    """Get bike lanes and cycleways for an area using OSM Overpass."""
    from ...traffic.overpass_client import fetch_bike_lanes

    points = [{"lat": lat, "lon": lon}]
    data = fetch_bike_lanes(points, include_geometry=False)
    count = len(data.get("elements", [])) if data else 0
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
        "bike_lanes_count": count,
        "elements": data.get("elements", []) if data else [],
    }


@router.get("/incidents")
async def get_traffic_incidents(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(5.0),
    days: int = Query(90, ge=1, le=365),
):
    """Get traffic incidents near coordinates."""
    from ...settings import get_settings
    from ...traffic.incident_fetcher import fetch_incidents, get_incident_stats

    _s = get_settings()
    radius = radius_km if radius_km > 0 else _s.incident_radius_km
    lookback = days if days > 0 else _s.incident_days
    incidents = fetch_incidents(lat, lon, radius_km=radius, days=lookback)
    stats = get_incident_stats(incidents)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius,
        "days": lookback,
        "incidents": incidents,
        "stats": stats,
    }
