"""SQLAlchemy models for PostgreSQL migration."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List
from dataclasses import dataclass
import math

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
    gps_points: Optional[List[dict]] = None
    created_at: Optional[str] = None

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0

    @property
    def intensity_factor(self) -> float:
        """Calculate training intensity factor (0-1 scale for ATL/CTL)."""
        if not self.heart_rate_avg:
            return 0.5
        return min(self.heart_rate_avg / 190.0, 1.0)

    @property
    def training_load(self) -> float:
        """Training Stress Score (TSS)-like metric for ATL/CTL calculation."""
        duration_h = self.duration_hours
        intensity = self.intensity_factor
        ascent_ratio = (self.elevation_gain_m / self.distance_km / 1000.0) if self.elevation_gain_m and self.distance_km > 0 else 0
        return min((duration_h * (intensity + ascent_ratio) * 50.0), 200.0)


@dataclass
class TrainingLoadPoint:
    date: str
    atl: float  # Acute Training Load
    ctl: float  # Chronic Training Load
    tsb: float  # Training Stress Balance


@dataclass
class TrainingGoal:
    id: Optional[int] = None
    athlete_id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    goal_type: str = "granfondo"
    target_date: Optional[str] = None
    target_distance_km: Optional[float] = None
    target_elevation_m: Optional[float] = None
    status: str = "active"
    created_at: Optional[str] = None


@dataclass
class PlannedWorkout:
    id: Optional[int] = None
    athlete_id: Optional[int] = None
    goal_id: Optional[int] = None
    date: str = ""
    title: str = ""
    workout_type: str = "endurance"
    duration_minutes: int = 60
    target_intensity: float = 0.5
    completed: bool = False
    completed_at: Optional[str] = None


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
    experience_level: str = "Beginner"
    goals: Optional[str] = None
    preferred_terrain: Optional[str] = None
    weekly_volume_km: float = 0.0
    best_segments: Optional[str] = None
    medical_notes: Optional[str] = None
    equipment: Optional[str] = None
    ftp_watts: Optional[float] = None
    created_at: Optional[str] = None


@dataclass
class CalendarEvent:
    id: Optional[int] = None
    athlete_id: Optional[int] = None
    title: str = ""
    event_type: str = "training"
    date: str = ""
    duration_minutes: int = 0
    description: Optional[str] = None
    completed: bool = False
    created_at: Optional[str] = None