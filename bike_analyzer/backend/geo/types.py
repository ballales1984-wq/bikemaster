from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class GeoEnrichedPoint:
    lat: float
    lon: float
    ele: float | None = None
    slope_percent: float | None = None
    surface: str | None = None
    highway: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class SegmentEnrichment:
    start_idx: int
    end_idx: int
    distance_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    avg_slope_percent: float
    max_slope_percent: float
    surface: str | None
    highway: str | None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class RouteEnrichmentResult:
    points: list[GeoEnrichedPoint]
    segments: list[SegmentEnrichment]
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
