from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..models.models import GPSPoint

logger = logging.getLogger(__name__)

try:
    from aethermap.ai.ingest import RawPoint
    from aethermap.ai.pipeline import Pipeline, WorldStore
    from aethermap.twin.objects import make_albero, make_montagna, make_strada
    from aethermap.twin.world import DigitalTwin, Environment
except ImportError as exc:
    raise RuntimeError(
        "AetherMap package is required for terrain enrichment. "
        "Install with: pip install -e \".[maps]\""
    ) from exc


@dataclass
class EnrichedGPSPoint:
    lat: float
    lon: float
    altitude: float | None
    speed: float | None
    slope_pct: float | None = None
    surface_type: str | None = None
    shade: bool | None = None
    traffic_level: float | None = None
    terrain_confidence: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "altitude": self.altitude,
            "speed": self.speed,
            "slope_pct": self.slope_pct,
            "surface_type": self.surface_type,
            "shade": self.shade,
            "traffic_level": self.traffic_level,
            "terrain_confidence": self.terrain_confidence,
            "extra": self.extra,
        }


def _gps_point_to_raw(point: GPSPoint) -> RawPoint:
    return RawPoint(lat=point.lat, lon=point.lon, ele=point.altitude or 0.0)


def _slope_from_points(points: list[GPSPoint], idx: int) -> float | None:
    if len(points) < 2:
        return None
    if idx <= 0 or idx >= len(points) - 1:
        prev = points[max(0, idx - 1)]
        nxt = points[min(len(points) - 1, idx + 1)]
    else:
        prev = points[idx - 1]
        nxt = points[idx + 1]
    dh = (nxt.altitude or 0.0) - (prev.altitude or 0.0)
    dist = prev.distance_to(nxt)
    if dist < 1e-6:
        return None
    return round(dh / dist * 100.0, 2)


def _shade_from_solar(solar_elev_deg: float) -> bool:
    return solar_elev_deg < 12.0


class TerrainEnricher:
    def __init__(
        self,
        *,
        temp_c: float = 15.0,
        solar_elev_deg: float = 45.0,
        ora: str = "12:00",
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.store = WorldStore()
        self.pipeline = Pipeline(self.store)
        self.twin = DigitalTwin()
        self.env = Environment(
            temp_c=temp_c,
            solar_elev_deg=solar_elev_deg,
            ora=ora,
        )

    def enrich_ride(self, points: list[GPSPoint]) -> list[EnrichedGPSPoint]:
        if not self.enabled or not points:
            return [
                EnrichedGPSPoint(
                    lat=p.lat,
                    lon=p.lon,
                    altitude=p.altitude,
                    speed=p.speed,
                )
                for p in points
            ]

        raw_points = [_gps_point_to_raw(p) for p in points]
        proposals = self.pipeline.research_gpx(raw_points)
        for prop in proposals:
            self.pipeline.submit(prop)
        self.pipeline.flush()

        self.twin.step(self.env)

        snapshot = self.twin.snapshot()
        slope_map = self._build_slope_map(snapshot, points)

        enriched: list[EnrichedGPSPoint] = []
        for i, pt in enumerate(points):
            slope = _slope_from_points(points, i)
            traffic = None
            confidence = None
            surface_type = None
            shade = None

            if snapshot:
                traffic = self._estimate_traffic(pt, snapshot)
                confidence = self._estimate_confidence(pt, snapshot)
                surface_type = self._estimate_surface(pt, snapshot)
                shade = _shade_from_solar(self.env.solar_elev_deg)

            enriched.append(
                EnrichedGPSPoint(
                    lat=pt.lat,
                    lon=pt.lon,
                    altitude=pt.altitude,
                    speed=pt.speed,
                    slope_pct=slope,
                    surface_type=surface_type,
                    shade=shade,
                    traffic_level=traffic,
                    terrain_confidence=confidence,
                )
            )
        return enriched

    def _build_slope_map(
        self, snapshot: list[dict], points: list[GPSPoint]
    ) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for item in snapshot:
            if item.get("tipo") == "strada" and "pendenza_%" in item:
                result[item["id"]] = item["pendenza_%"]
        return result

    def _estimate_traffic(
        self, point: GPSPoint, snapshot: list[dict]
    ) -> float | None:
        for item in snapshot:
            if item.get("tipo") == "strada" and "traffico" in item:
                return item["traffico"]
        return None

    def _estimate_confidence(
        self, point: GPSPoint, snapshot: list[dict]
    ) -> float | None:
        best_conf: float | None = None
        for item in snapshot:
            if item.get("tipo") == "strada":
                props = item.get("proprieta", {})
                c = props.get("traffico")
                if c is not None:
                    best_conf = 0.7
        return best_conf

    def _estimate_surface(
        self, point: GPSPoint, snapshot: list[dict]
    ) -> str | None:
        for item in snapshot:
            if item.get("tipo") == "strada":
                return "asfalto"
        return None

    def snapshot(self) -> list[dict]:
        return self.twin.snapshot()

    def h3_summary(self, resolution: int = 9) -> dict[str, dict[str, int]]:
        return self.twin.h3_summary(resolution)