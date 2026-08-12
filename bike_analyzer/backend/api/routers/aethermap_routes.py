"""AetherMap terrain and geo REST API."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aethermap", tags=["aethermap"])


@router.get("/terrain")
async def get_terrain(
    min_lat: float = Query(...),
    max_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lon: float = Query(...),
    resolution: int = Query(64, ge=2, le=256),
    source: str = Query("auto"),
    current_user: dict = Depends(get_current_user),
):
    """Return a heightfield for a lat/lon bounding box."""
    try:
        from bike_analyzer.backend.maps.terrain import get_tile

        tile = get_tile(min_lat, max_lat, min_lon, max_lon, resolution=resolution, source=source)
        return {"heights": tile.heights.flatten().tolist()}
    except Exception as exc:
        logger.exception("Terrain lookup failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/world")
async def get_world(current_user: dict = Depends(get_current_user)):
    """Return the current AetherMap world state."""
    try:
        from aethermap.twin.world import WorldStore

        store = WorldStore()
        return store.to_dict()
    except Exception as exc:
        logger.exception("World state fetch failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/terrain-tile")
async def get_terrain_tile(
    x: int = Query(...),
    y: int = Query(...),
    z: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Return a terrain tile."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/geo/roads")
async def get_geo_roads(
    bbox: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Return road network data within a bounding box."""
    try:
        from ..maps.osm_maps import get_local_results

        results = get_local_results(bbox)
        return {"features": results}
    except Exception as exc:
        logger.exception("Roads lookup failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/geo/cities")
async def get_geo_cities(
    bbox: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Return cities within a bounding box."""
    try:
        from ..maps.osm_maps import search_places

        results = search_places(bbox, category="city")
        return {"features": results}
    except Exception as exc:
        logger.exception("Cities lookup failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/geo/peaks")
async def get_geo_peaks(
    bbox: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Return peaks within a bounding box."""
    try:
        from ..maps.osm_maps import search_places

        results = search_places(bbox, category="peak")
        return {"features": results}
    except Exception as exc:
        logger.exception("Peaks lookup failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/geo/natural-earth")
async def get_natural_earth(
    resolution: str = Query("110m"),
    current_user: dict = Depends(get_current_user),
):
    """Return Natural Earth vector data."""
    try:
        import os

        from bike_analyzer.backend.maps.terrain import _DEM_CACHE_DIR

        cache_file = _DEM_CACHE_DIR / f"natural-earth-{resolution}.geojson"
        if not cache_file.exists():
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            import urllib.request

            url = (
                f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
                f"ne_{resolution}m_land.geojson"
            )
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    cache_file.write_bytes(resp.read())
            except Exception as exc:
                logger.warning("Natural Earth download failed: %s", exc)
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Natural Earth data unavailable"},
                )
        raw = cache_file.read_text(encoding="utf-8")
        return JSONResponse(content=json.loads(raw))
    except json.JSONDecodeError as exc:
        logger.warning("Natural Earth cache corrupted: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "Natural Earth data unavailable"},
        )
    except Exception as exc:
        logger.exception("Natural Earth fetch failed")
        raise HTTPException(status_code=500, detail=str(exc))
