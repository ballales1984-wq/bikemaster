"""Maps API routes (POI and Places)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..routes import _place_cache_get, _place_cache_set, get_current_user, logger
from ..schemas import POICreate, POIResponse
from ...models.models import GPSPoint
from ...settings import get_settings

router = APIRouter(prefix="/maps", tags=["maps"])


@router.get("/pois/nearby")
async def get_nearby_pois(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the search center"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the search center"),
    radius: float = Query(5.0, ge=0.1, le=200, description="Search radius in km"),
    current_user: dict = Depends(get_current_user),
):
    """Return Points of Interest within ``radius`` km of (lat, lon).

    Only POIs belonging to the current user's tenant are returned.
    """
    from ...analytics.repositories.poi_repository import POIRepository
    from ...db.async_db import get_session_factory

    tenant_id = current_user.get("tenant_id", current_user["id"])
    try:
        repo = POIRepository(session_factory=get_session_factory())
    except RuntimeError:
        repo = POIRepository()
    pois = await repo.get_nearby(lat, lon, radius, tenant_id=tenant_id)
    return {"pois": pois}


@router.get("/pois")
async def list_pois_endpoint(
    itinerary_id: int | None = None, current_user: dict = Depends(get_current_user)
):
    """List POIs, optionally filtered by itinerary_id.

    Only POIs belonging to the current user's tenant are returned.
    """
    from ...db.database import list_pois

    tenant_id = current_user.get("tenant_id", current_user["id"])
    return {"pois": list_pois(itinerary_id, tenant_id=tenant_id)}


@router.post("/pois", response_model=POIResponse)
async def create_poi(poi: POICreate, current_user: dict = Depends(get_current_user)):
    """Create a Point of Interest owned by the current user."""
    from ...db.database import get_poi, save_poi

    data = poi.model_dump()
    data["created_by"] = current_user["id"]
    data["tenant_id"] = current_user.get("tenant_id", current_user["id"])
    poi_id = save_poi(data)
    created = get_poi(poi_id)
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create POI")
    return created


@router.get("/pois/{poi_id}", response_model=POIResponse)
async def get_poi_endpoint(poi_id: int, current_user: dict = Depends(get_current_user)):
    """Retrieve a Point of Interest by ID.

    Only POIs belonging to the current user's tenant are accessible
    (admins can access any).
    """
    from ...db.database import get_poi

    tenant_id = current_user.get("tenant_id", current_user["id"])
    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    if not current_user.get("is_admin") and poi.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this POI")
    return poi


@router.delete("/pois/{poi_id}")
async def delete_poi_endpoint(
    poi_id: int, current_user: dict = Depends(get_current_user)
):
    """Delete a POI if the current user is the owner or an admin."""
    from ...db.database import delete_poi, get_poi

    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    if not current_user.get("is_admin") and poi["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this POI")
    delete_poi(poi_id)
    return {"deleted": True}


@router.get("/places/nearby")
async def nearby_places(
    ride_id: int,
    query: str = Query(..., description="e.g.: cafe, bakery, restaurant"),
    use_osm: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    """Find nearby places for a ride using OSM or SerpApi.

    Results are cached in-memory for 10 minutes.
    """
    from ...db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    center_lat = round(sum(p.lat for p in points) / len(points), 3)
    center_lon = round(sum(p.lon for p in points) / len(points), 3)
    cache_key_str = f"places:nearby:{use_osm}:{query}:{center_lat}:{center_lon}"
    cached_result = _place_cache_get(cache_key_str)
    if cached_result is not None:
        logger.debug("Place search cache hit: nearby %s", query)
        return cached_result
    if use_osm:
        from ...maps.osm_maps import get_local_results as osm_search

        results = await osm_search(points, query=query)
    else:
        from ...maps.osm_maps import get_local_results

        results = await get_local_results(points, query=query)
    if results is None:
        raise HTTPException(status_code=502, detail="Place search request failed")
    resp = {"query": query, "count": len(results), "results": results}
    _place_cache_set(cache_key_str, resp)
    logger.debug("Place search cached: nearby %s (%d results)", query, len(results))
    return resp


@router.get("/places/osm-search")
async def osm_places_search(
    lat: float = Query(...),
    lon: float = Query(...),
    query: str = Query(...),
    limit: int = Query(10),
):
    """OpenStreetMap Nominatim search for places. No API key required."""
    cache_key_str = f"places:osm:{query}:{round(lat, 3)}:{round(lon, 3)}:{limit}"
    cached_result = _place_cache_get(cache_key_str)
    if cached_result is not None:
        logger.debug("Place search cache hit: osm %s", query)
        return cached_result
    result = await search_places(query, lat=lat, lon=lon, limit=limit)
    resp = {"query": query, "results": result.get("results", []) if result else []}
    _place_cache_set(cache_key_str, resp)
    logger.debug("Place search cached: osm %s", query)
    return resp


@router.get("/places/search")
async def search_places_endpoint(
    ride_id: int,
    query: str = Query(..., description="Place search query"),
    current_user: dict = Depends(get_current_user),
):
    """Search for places near a ride using SerpApi (requires API key)."""
    """Search places using SerpApi for a ride - user must own the ride."""
    from ...db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    _s = get_settings()
    if not _s.serpapi_api_key:
        raise HTTPException(status_code=500, detail="SERPAPI_API_KEY not configured")
    from ...maps.osm_maps import search_nearby

    data = await search_nearby(points, query=query)
    if data is None:
        raise HTTPException(status_code=502, detail="SerpApi request failed")
    return data
