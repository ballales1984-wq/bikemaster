"""Core domain models for BikeMaster.

This module contains the pure domain entities independent of any
infrastructure concern (DB, API, serialization).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    return (
        2
        * EARTH_RADIUS_M
        * math.asin(
            math.sqrt(
                math.sin(dphi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
            )
        )
    )


@dataclass(frozen=True)
class GPSPoint:
    lat: float
    lon: float
    timestamp: datetime
    altitude: float | None = None
    speed: float | None = None
    power: float | None = None
    heart_rate: float | None = None
    cadence: float | None = None

    def distance_to(self, other: GPSPoint) -> float:
        return haversine_distance_m(self.lat, self.lon, other.lat, other.lon)


@dataclass
class Segment:
    start: GPSPoint
    end: GPSPoint
    distance_m: float = 0.0
    duration_s: float = 0.0
    avg_speed_km_h: float = 0.0
    elevation_gain_m: float = 0.0
    elevation_loss_m: float = 0.0


@dataclass
class Pause:
    start: datetime
    end: datetime
    duration_s: float = 0.0


@dataclass
class RouteStatistics:
    total_distance_m: float = 0.0
    total_duration_s: float = 0.0
    total_pause_duration_s: float = 0.0
    avg_speed_km_h: float = 0.0
    max_speed_km_h: float = 0.0
    total_elevation_gain_m: float = 0.0
    total_elevation_loss_m: float = 0.0
    segment_count: int = 0
    pause_count: int = 0


@dataclass
class Ride:
    id: int | None = None
    athlete_id: int | None = None
    date: str = ""
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    avg_speed_kmh: float = 0.0
    weight_kg: float = 70.0
    calories: float = 0.0
    heart_rate_avg: float | None = None
    elevation_gain_m: float | None = None
    external_source: str | None = None
    external_id: str | None = None
    title: str | None = None
    gps_points: list[GPSPoint] | None = None
    created_at: str | None = None

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "athlete_id": self.athlete_id,
            "date": self.date,
            "distance_km": self.distance_km,
            "duration_minutes": self.duration_minutes,
            "avg_speed_kmh": self.avg_speed_kmh,
            "weight_kg": self.weight_kg,
            "calories": self.calories,
            "heart_rate_avg": self.heart_rate_avg,
            "elevation_gain_m": self.elevation_gain_m,
            "created_at": self.created_at,
        }
        if self.gps_points:
            result["gps_points"] = [
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "timestamp": p.timestamp.isoformat(),
                    "altitude": p.altitude,
                    "speed": p.speed,
                    "power": p.power,
                    "heart_rate": p.heart_rate,
                    "cadence": p.cadence,
                }
                for p in self.gps_points
            ]
        return result


@dataclass
class AthleteProfile:
    id: int | None = None
    name: str = ""
    age: int = 30
    weight_kg: float = 70.0
    height_cm: float | None = None
    fat_percentage: float | None = None
    years_active: int = 1
    weekly_sessions: int = 3
    monthly_hours: float = 0.0
    annual_hours: float = 0.0
    experience_level: str = "Beginner"
    goals: str | None = None
    preferred_terrain: str | None = None
    weekly_volume_km: float = 0.0
    best_segments: str | None = None
    medical_notes: str | None = None
    equipment: str | None = None
    ftp_watts: float | None = None
    created_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "fat_percentage": self.fat_percentage,
            "years_active": self.years_active,
            "weekly_sessions": self.weekly_sessions,
            "monthly_hours": self.monthly_hours,
            "annual_hours": self.annual_hours,
            "experience_level": self.experience_level,
            "goals": self.goals,
            "preferred_terrain": self.preferred_terrain,
            "weekly_volume_km": self.weekly_volume_km,
            "best_segments": self.best_segments,
            "medical_notes": self.medical_notes,
            "equipment": self.equipment,
            "ftp_watts": self.ftp_watts,
            "created_at": self.created_at,
        }


@dataclass
class CalendarEvent:
    id: int | None = None
    athlete_id: int | None = None
    title: str = ""
    event_type: str = "training"
    date: str = ""
    duration_minutes: int = 0
    description: str | None = None
    completed: bool = False
    created_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "athlete_id": self.athlete_id,
            "title": self.title,
            "event_type": self.event_type,
            "date": self.date,
            "duration_minutes": self.duration_minutes,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at,
        }
