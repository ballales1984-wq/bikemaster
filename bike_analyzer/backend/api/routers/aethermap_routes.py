"""AetherMap terrain and geo REST API."""

from __future__ import annotations

import json
import logging

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
        raise HTTPException(status_code=500, detail=str(exc)) from None


@router.get("/world")
async def get_world(current_user: dict = Depends(get_current_user)):
    """Return the current AetherMap world state."""
    try:
        import numpy as np
        from aethermap import Oggetto, Posizione, Geometria, WorldStore
        from aethermap.render.terrain_enhancer import build_enhanced_heightfield
        from aethermap.render.webgl_exporter import _terrain_mesh_from_hf

        store = WorldStore()
        if not store.objects:
            for i in range(3):
                pos = Posizione.from_latlon(lat=float(i), lon=0.0, alt=0.0)
                geom = Geometria(tipo="punto", dati={"tipo": "punto"})
                store.add(Oggetto(
                    id=f"default_{i}",
                    tipo="point",
                    posizione=pos,
                    geometria=geom,
                    proprieta={"color": "#ffffff"},
                ))

        hf = build_enhanced_heightfield(n=32, base_alt=0.0, height_scale=0.04)
        terrain = _terrain_mesh_from_hf(hf, 32)

        entities = []
        for obj in store.all():
            pos = obj.posizione
            ecef = pos.ecef_relative or (0.0, 0.0, 0.0)
            dist = (ecef[0] ** 2 + ecef[1] ** 2 + ecef[2] ** 2) ** 0.5
            if dist > 1e-12:
                px, py, pz = ecef[0] / dist, ecef[1] / dist, ecef[2] / dist
            else:
                px = py = pz = 0.0
            entities.append({
                "id": obj.id,
                "tipo": obj.tipo,
                "kind": obj.geometria.tipo if obj.geometria else "unknown",
                "color": obj.proprieta.get("color", "#ffffff") if obj.proprieta else "#ffffff",
                "position": [px, py, pz],
            })

        return {
            "version": "aethermap-webgl-1.0",
            "terrain": terrain,
            "entities": entities,
            "relations": [],
            "camera": {"yaw": 0.0, "pitch": 0.0},
            "earth_r": 1.0,
        }
    except Exception as exc:
        logger.exception("World state fetch failed")
        raise HTTPException(status_code=500, detail=str(exc)) from None


@router.get("/terrain-tile")
async def get_terrain_tile(
    face: int = Query(..., ge=0, le=5),
    resolution: int = Query(..., ge=8, le=256),
    current_user: dict = Depends(get_current_user),
):
    """Return a terrain tile for a cube-sphere face."""
    try:
        import numpy as np
        from aethermap.render.terrain_enhancer import build_enhanced_heightfield
        from aethermap.render.webgl_exporter import _terrain_mesh_from_hf

        hf = build_enhanced_heightfield(n=resolution, base_alt=0.0, height_scale=0.04)
        tile = _terrain_mesh_from_hf(hf, resolution, with_skirt=False)

        n = resolution
        face_start = face * n * n
        positions = tile["positions"][face_start : face_start + n * n]
        normals = tile["normals"][face_start : face_start + n * n]
        face_indices = []
        for idx in tile["indices"]:
            v = idx - face_start
            if face_start <= idx < face_start + n * n:
                face_indices.append(v)
        indices = face_indices

        return {
            "positions": positions,
            "normals": normals,
            "indices": indices,
            "grid_size": n,
            "face": face,
            "resolution": resolution,
            "source": "aethermap",
        }
    except Exception as exc:
        logger.exception("Terrain tile fetch failed")
        raise HTTPException(status_code=500, detail=str(exc)) from None


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
        raise HTTPException(status_code=500, detail=str(exc)) from None


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
        raise HTTPException(status_code=500, detail=str(exc)) from None


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
        raise HTTPException(status_code=500, detail=str(exc)) from None


@router.get("/geo/natural-earth")
async def get_natural_earth(
    resolution: str = Query("110"),
    current_user: dict = Depends(get_current_user),
):
    """Return Natural Earth vector data."""
    try:

        import asyncio

        import httpx

        from bike_analyzer.backend.maps.terrain import _DEM_CACHE_DIR

        cache_file = _DEM_CACHE_DIR / f"natural-earth-{resolution}.geojson"
        if not cache_file.exists():
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            url = (
                f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
                f"ne_{resolution}m_land.geojson"
            )
            last_exc: Exception | None = None
            for attempt in range(4):
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        cache_file.write_bytes(resp.content)
                        break
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    last_exc = exc
                    if attempt < 3:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    logger.warning("Natural Earth download failed after retries: %s", exc)
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
        raise HTTPException(status_code=500, detail=str(exc)) from None


@router.get("/ride/{ride_id}")
async def get_aethermap_ride(
    ride_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Return AetherMap GeoJSON for a single ride."""
    try:
        from bike_analyzer.backend.db.database import get_ride
        from bike_analyzer.backend.maps.aethermap_adapter import create_route_map
        from bike_analyzer.core.models import GPSPoint, RouteStatistics
        from tempfile import TemporaryDirectory

        tenant_id = current_user.get("tenant_id", current_user["id"])
        ride = get_ride(ride_id, tenant_id=tenant_id)
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

        stats = None
        if ride.get("distance_km") and ride.get("duration_minutes"):
            stats = RouteStatistics(
                total_distance_m=ride.get("distance_km", 0.0) * 1000.0,
                total_duration_s=ride.get("duration_minutes", 0.0) * 60.0,
                avg_speed_km_h=ride.get("avg_speed_kmh", 0.0),
                max_speed_km_h=ride.get("max_speed_kmh", 0.0),
                total_elevation_gain_m=ride.get("elevation_gain_m", 0.0),
            )

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / f"ride_{ride_id}_map.json"
            create_route_map(points, statistics=stats, output_path=str(output_path))
            data = json.loads(output_path.read_text(encoding="utf-8"))
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("AetherMap ride fetch failed")
        raise HTTPException(status_code=500, detail=str(exc)) from None
