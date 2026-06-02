from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class GPSPoint:
    lat: float
    lon: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None

    def __post_init__(self) -> None:
        if not -90 <= self.lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.lat}")
        if not -180 <= self.lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.lon}")


@dataclass
class GPSRoute:
    points: List[GPSPoint] = field(default_factory=list)

    def add_point(self, point: GPSPoint) -> None:
        self.points.append(point)

    def sort_by_time(self) -> None:
        self.points.sort(key=lambda p: p.timestamp)

    @property
    def is_sorted(self) -> bool:
        return all(
            self.points[i].timestamp <= self.points[i + 1].timestamp
            for i in range(len(self.points) - 1)
        )
