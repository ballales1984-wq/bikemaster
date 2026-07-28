from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from aethermap.twin.world import DigitalTwin, Environment
except ImportError as exc:
    raise RuntimeError(
        "AetherMap package is required for terrain twin. "
        "Install with: pip install -e \".[maps]\""
    ) from exc


@dataclass
class RideContext:
    ride_id: str | None = None
    terrain_features: list[dict] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    h3_summary: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ride_id": self.ride_id,
            "terrain_features": self.terrain_features,
            "environment": self.environment,
            "h3_summary": self.h3_summary,
        }


@dataclass
class SurfaceProfile:
    surface_type: str
    slope_pct_avg: float
    slope_pct_max: float
    shade_fraction: float
    traffic_level_avg: float | None


class TerrainTwin:
    def __init__(
        self,
        *,
        temp_c: float = 15.0,
        solar_elev_deg: float = 45.0,
        ora: str = "12:00",
    ) -> None:
        self.twin = DigitalTwin()
        self.env = Environment(
            temp_c=temp_c,
            solar_elev_deg=solar_elev_deg,
            ora=ora,
        )

    def add_ride_points(self, points: list[Any]) -> None:
        from aethermap.twin.objects import make_strada

        if not points:
            return
        pts = []
        for p in points:
            pts.append(
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "ele": p.altitude or 0.0,
                }
            )
        self.twin.add(make_strada("ride_track", points[0].lat, points[0].lon, pts))

    def step(self) -> None:
        self.twin.step(self.env)

    def get_context(self) -> RideContext:
        snapshot = self.twin.snapshot()
        features = [item for item in snapshot if item.get("tipo") == "strada"]
        h3 = self.twin.h3_summary()
        return RideContext(
            terrain_features=features,
            environment={
                "temp_c": self.env.temp_c,
                "solar_elev_deg": self.env.solar_elev_deg,
                "ora": self.env.ora,
            },
            h3_summary=h3,
        )

    def get_surface_profile(self) -> SurfaceProfile | None:
        snapshot = self.twin.snapshot()
        roads = [item for item in snapshot if item.get("tipo") == "strada"]
        if not roads:
            return None
        slopes = [r.get("pendenza_%", 0.0) for r in roads if "pendenza_%" in r]
        traffic = [r.get("traffico") for r in roads if "traffico" in r]
        shade_vals = [r.get("ombrata") for r in roads if "ombrata" in r]
        return SurfaceProfile(
            surface_type="asfalto",
            slope_pct_avg=round(sum(slopes) / len(slopes), 2) if slopes else 0.0,
            slope_pct_max=max(slopes) if slopes else 0.0,
            shade_fraction=sum(1 for s in shade_vals if s) / len(shade_vals) if shade_vals else 0.0,
            traffic_level_avg=round(sum(traffic) / len(traffic), 1) if traffic else None,
        )