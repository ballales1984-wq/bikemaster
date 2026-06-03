"""Core domain models for bike analysis."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass
class GPSPoint:
    lat: float
    lon: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None

    def distance_to(self, other: GPSPoint) -> float:
        import math
        R = 6_371_000
        phi1, phi2 = math.radians(self.lat), math.radians(other.lat)
        dphi, dlambda = math.radians(other.lat - self.lat), math.radians(other.lon - self.lon)
        return 2 * R * math.asin(math.sqrt(math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2))

@dataclass
class Segment:
    start: GPSPoint
    end: GPSPoint
    distance_m: float
    duration_s: float
    avg_speed_km_h: float
    elevation_gain_m: float = 0.0
    elevation_loss_m: float = 0.0

@dataclass
class Pause:
    start: datetime
    end: datetime
    duration_s: float

@dataclass
class RouteStatistics:
    total_distance_m: float
    total_duration_s: float
    total_pause_duration_s: float
    avg_speed_km_h: float
    max_speed_km_h: float
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    segment_count: int
    pause_count: int

@dataclass
class Ride:
    id: Optional[int] = None
    date: str = ""
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    avg_speed_kmh: float = 0.0
    weight_kg: float = 70.0
    calories: float = 0.0
    heart_rate_avg: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    gps_points: Optional[list[GPSPoint]] = None

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0

    def to_dict(self) -> dict:
        return {"id": self.id, "date": self.date, "distance_km": self.distance_km, "duration_minutes": self.duration_minutes, "avg_speed_kmh": self.avg_speed_kmh, "weight_kg": self.weight_kg, "calories": self.calories, "heart_rate_avg": self.heart_rate_avg, "elevation_gain_m": self.elevation_gain_m}