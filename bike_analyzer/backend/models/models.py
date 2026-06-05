"""Core domain models for bike analysis."""

from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2))


@dataclass
class GPSPoint:
    lat: float
    lon: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None

    def distance_to(self, other: GPSPoint) -> float:
        return haversine_distance_m(self.lat, self.lon, other.lat, other.lon)

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
    athlete_id: Optional[int] = None
    date: str = ""
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    avg_speed_kmh: float = 0.0
    weight_kg: float = 70.0
    calories: float = 0.0
    heart_rate_avg: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    gps_points: Optional[list[GPSPoint]] = None
    created_at: Optional[str] = None

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0

    def to_dict(self) -> dict:
        return {"id": self.id, "athlete_id": self.athlete_id, "date": self.date, "distance_km": self.distance_km, "duration_minutes": self.duration_minutes, "avg_speed_kmh": self.avg_speed_kmh, "weight_kg": self.weight_kg, "calories": self.calories, "heart_rate_avg": self.heart_rate_avg, "elevation_gain_m": self.elevation_gain_m, "created_at": self.created_at}

@dataclass
class AthleteProfile:
    id: Optional[int] = None
    name: str = ""
    age: int = 30
    weight_kg: float = 70.0
    height_cm: Optional[float] = None
    fat_percentage: Optional[float] = None
    years_active: int = 1
    weekly_sessions: int = 3
    monthly_hours: float = 0.0
    annual_hours: float = 0.0
    experience_level: str = "Beginner"  # Beginner, Amateur, Intermediate, Advanced, Elite

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "age": self.age, "weight_kg": self.weight_kg, "height_cm": self.height_cm, "fat_percentage": self.fat_percentage, "years_active": self.years_active, "weekly_sessions": self.weekly_sessions, "monthly_hours": self.monthly_hours, "annual_hours": self.annual_hours, "experience_level": self.experience_level}