"""Terrain enrichment module for BikeMaster.

Integrates AetherMap terrain intelligence into BikeMaster rides.
Enriches GPS points with terrain attributes:
  - slope_pct
  - surface_type
  - shade
  - traffic_level
  - terrain_confidence
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from aethermap.ai.ingest import RawPoint
    from aethermap.ai.pipeline import WorldStore as AIWorldStore, Pipeline
    from aethermap.twin.world import DigitalTwin, Environment
except ImportError as exc:
    raise RuntimeError("AetherMap package is required for terrain enrichment") from exc

from bike_analyzer.core.models import GPSPoint

logger = logging.getLogger(__name__)


@dataclass
class EnrichedGPSPoint:
    """GPS point enriched with terrain attributes from AetherMap."""

    lat: float
    lon: float
    timestamp: datetime | None = None
    altitude: float | None = None
    speed: float | None = None
    power: float | None = None
    heart_rate: float | None = None
    cadence: float | None = None
    slope_pct: float = 0.0
    surface_type: str = "asphalt"
    shade: bool | None = None
    traffic_level: float = 0.0
    terrain_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "altitude": self.altitude,
            "speed": self.speed,
            "power": self.power,
            "heart_rate": self.heart_rate,
            "cadence": self.cadence,
            "slope_pct": self.slope_pct,
            "surface_type": self.surface_type,
            "shade": self.shade,
            "traffic_level": self.traffic_level,
            "terrain_confidence": self.terrain_confidence,
        }


class TerrainEnricher:
    """Enrich GPS points with terrain data from AetherMap engine.

    Uses the AetherMap AI researcher pipeline to derive terrain features
    from a GPX-like track, then maps the resulting world state onto each
    GPS point.
    """

    def __init__(
        self,
        temp_c: float = 15.0,
        solar_elev_deg: float = 45.0,
        ora: str = "12:00",
        enabled: bool = False,
    ) -> None:
        self.store = AIWorldStore()
        self.pipeline = Pipeline(self.store)
        self.twin = DigitalTwin()
        self.temp_c = temp_c
        self.solar_elev_deg = solar_elev_deg
        self.ora = ora
        self.enabled = enabled

    def enrich_ride(self, points: list[GPSPoint]) -> list[EnrichedGPSPoint]:
        """Enrich GPS points with terrain data from AetherMap engine."""
        if not points:
            return []

        raw_points = [RawPoint(lat=p.lat, lon=p.lon, ele=p.altitude, t=p.timestamp) for p in points]

        proposals = self.pipeline.research_gpx(raw_points)
        for proposta in proposals:
            self.pipeline.submit(proposta)
        self.pipeline.flush()

        env = Environment(temp_c=self.temp_c, solar_elev_deg=self.solar_elev_deg, ora=self.ora)
        self.twin.step(env)

        return self._build_enriched(points, env)

    def snapshot(self) -> list[dict]:
        """Return current digital twin state snapshot."""
        return self.twin.snapshot()

    def h3_summary(self, resolution: int = 9) -> dict[str, dict[str, int]]:
        """Return H3 aggregation summary."""
        return self.twin.h3_summary(resolution=resolution)

    @staticmethod
    def _calc_slope(p1: GPSPoint, p2: GPSPoint) -> float:
        if p1.altitude is None or p2.altitude is None:
            return 0.0
        d = p1.distance_to(p2)
        if d == 0:
            return 0.0
        return (p2.altitude - p1.altitude) / d * 100

    def _build_enriched(self, points: list[GPSPoint], env: Environment) -> list[EnrichedGPSPoint]:
        road = next((o for o in self.twin.store.all() if o.tipo == "strada"), None)

        traffic = 0.0
        surface = "asphalt"
        confidence = 0.0
        if road is not None:
            if hasattr(road, "traffico"):
                t = road.traffico()
                if t is not None:
                    traffic = float(t)
            surface = road.proprieta.get("asfalto", "asphalt")
            confidence = float(road.affidabilita.valore)

        shade = env.solar_elev_deg < 12.0

        enriched: list[EnrichedGPSPoint] = []
        for i, p in enumerate(points):
            slope = 0.0
            if i > 0:
                slope = self._calc_slope(points[i - 1], p)
            elif i + 1 < len(points):
                slope = self._calc_slope(p, points[i + 1])

            enriched.append(EnrichedGPSPoint(
                lat=p.lat,
                lon=p.lon,
                timestamp=p.timestamp,
                altitude=p.altitude,
                speed=p.speed,
                power=p.power,
                heart_rate=p.heart_rate,
                cadence=p.cadence,
                slope_pct=round(slope, 2),
                surface_type=surface,
                shade=shade,
                traffic_level=round(traffic, 2),
                terrain_confidence=round(confidence, 2),
            ))
        return enriched
