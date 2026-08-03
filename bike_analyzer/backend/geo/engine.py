from __future__ import annotations

import logging
import math
from typing import Any

from ..maps.aethermap_adapter import RouteStatistics
from ..models.models import GPSPoint
from .osm import enrich_osm
from .route_builder import build_aethermap_worldstore, save_aethermap_geojson
from .terrain import sample_elevation_profile
from .types import GeoEnrichedPoint, RouteEnrichmentResult

logger = logging.getLogger(__name__)


async def run_geo_pipeline(
    points: list[GPSPoint],
    statistics: RouteStatistics | None = None,
    *,
    enrich_osm_data: bool = True,
    sample_dem: bool = True,
    build_3d: bool = True,
    output_path: str | None = None,
    extra_layers: dict[str, Any] | None = None,
) -> RouteEnrichmentResult:
    if not points:
        return RouteEnrichmentResult(points=[], segments=[])

    raw_pts = [{"lat": p.lat, "lon": p.lon} for p in points]
    osm_info = await enrich_osm(raw_pts) if enrich_osm_data else None

    surface_default: str | None = None
    highway_default: str | None = None
    if osm_info:
        surface_default = osm_info.get("dominant_surface")
        highways = osm_info.get("highways") or []
        highway_default = highways[0] if highways else None

    dem_elevations: list[float] = []
    if sample_dem:
        try:
            dem_elevations = sample_elevation_profile(
                [(p.lat, p.lon) for p in points],
                resolution=64,
                source="auto",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("DEM sampling failed, using original elevations: %s", exc)
            dem_elevations = []

    enriched: list[GeoEnrichedPoint] = []
    for i, p in enumerate(points):
        alt = dem_elevations[i] if i < len(dem_elevations) else (p.altitude or 0.0)
        slope = None
        if dem_elevations and i > 0:
            prev_alt = dem_elevations[i - 1]
            dist_m = _haversine_distance_m(
                points[i - 1].lat, points[i - 1].lon, p.lat, p.lon
            )
            if dist_m > 0:
                slope = (alt - prev_alt) / dist_m * 100.0
        enriched.append(GeoEnrichedPoint(
            lat=p.lat,
            lon=p.lon,
            ele=alt,
            slope_percent=slope,
            surface=getattr(p, "surface", None) or surface_default,
            highway=getattr(p, "highway", None) or highway_default,
            tags=getattr(p, "tags", None) or {},
        ))

    segments = _build_segments(enriched)

    meta: dict[str, Any] = {}
    if osm_info:
        meta["osm"] = osm_info
    if dem_elevations:
        meta["dem_sampled"] = True

    if build_3d and output_path:
        store, geo_meta = build_aethermap_worldstore(
            _to_gps_like(enriched),
            statistics=statistics,
            extra_layers=extra_layers or {},
        )
        meta.update(geo_meta)
        save_aethermap_geojson(store, meta, output_path=output_path)

    return RouteEnrichmentResult(
        points=enriched,
        segments=segments,
        bbox=_bbox(enriched),
        metadata=meta,
    )


def _build_segments(points: list[GeoEnrichedPoint]) -> list[Any]:
    segs = []
    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        dist = _haversine_distance_m(a.lat, a.lon, b.lat, b.lon)
        elev_gain = max(0.0, (b.ele or 0.0) - (a.ele or 0.0))
        elev_loss = max(0.0, (a.ele or 0.0) - (b.ele or 0.0))
        avg_slope = ((b.ele or 0.0) - (a.ele or 0.0)) / dist * 100.0 if dist > 0 else 0.0
        segs.append({
            "start_idx": i - 1,
            "end_idx": i,
            "distance_m": dist,
            "elevation_gain_m": elev_gain,
            "elevation_loss_m": elev_loss,
            "avg_slope_percent": avg_slope,
            "max_slope_percent": abs(avg_slope),
            "surface": b.surface,
            "highway": b.highway,
            "tags": b.tags,
        })
    return segs


def _bbox(points: list[GeoEnrichedPoint]) -> tuple[float, float, float, float] | None:
    if not points:
        return None
    lats = [p.lat for p in points]
    lons = [p.lon for p in points]
    return (min(lats), min(lons), max(lats), max(lons))


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _to_gps_like(points: list[GeoEnrichedPoint]) -> list[GPSPoint]:
    out: list[GPSPoint] = []
    for p in points:
        out.append(GPSPoint(
            lat=p.lat,
            lon=p.lon,
            altitude=p.ele,
            timestamp=None,
            speed=None,
        ))
    return out
