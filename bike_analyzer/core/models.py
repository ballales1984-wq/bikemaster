"""Core domain models for BikeMaster.

This module contains the pure domain entities independent of any
infrastructure concern (DB, API, serialization).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in meters between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    return (
        2
        * EARTH_RADIUS_M
        * math.asin(math.sqrt(math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2))
    )


@dataclass(frozen=True)
class GPSPoint:
    """Single GPS sample recorded during a ride.

    Attributes:
        lat: WGS84 latitude in decimal degrees.
        lon: WGS84 longitude in decimal degrees.
        timestamp: UTC timestamp of the sample.
        altitude: Elevation above sea level in meters.
        speed: Instantaneous speed in km/h.
        power: Instantaneous power in watts.
        heart_rate: Heart rate in bpm.
        cadence: Cadence in rpm.
    """

    lat: float
    lon: float
    timestamp: datetime
    altitude: float | None = None
    speed: float | None = None
    power: float | None = None
    heart_rate: float | None = None
    cadence: float | None = None

    def __post_init__(self) -> None:
        """Normalize timestamps to naive UTC datetimes."""
        ts = self.timestamp
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return
        if isinstance(ts, datetime) and ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        object.__setattr__(self, "timestamp", ts)

    def distance_to(self, other: GPSPoint) -> float:
        """Return the haversine distance in meters to ``other``."""
        return haversine_distance_m(self.lat, self.lon, other.lat, other.lon)


@dataclass
class Segment:
    """Road segment between two GPS points.

    Attributes:
        start: Start GPS point.
        end: End GPS point.
        distance_m: Segment length in meters.
        duration_s: Segment duration in seconds.
        avg_speed_km_h: Average speed over the segment in km/h.
        elevation_gain_m: Elevation gained within the segment in meters.
        elevation_loss_m: Elevation lost within the segment in meters.
    """
    start: GPSPoint
    end: GPSPoint
    distance_m: float = 0.0
    duration_s: float = 0.0
    avg_speed_km_h: float = 0.0
    elevation_gain_m: float = 0.0
    elevation_loss_m: float = 0.0


@dataclass
class Pause:
    """Detected stop/pause during a ride.

    Attributes:
        start: Pause start timestamp.
        end: Pause end timestamp.
        duration_s: Pause duration in seconds.
    """
    start: datetime
    end: datetime
    duration_s: float = 0.0


@dataclass
class RouteStatistics:
    """Aggregated statistics for a processed route.

    Attributes:
        total_distance_m: Total route distance in meters.
        total_duration_s: Total moving time in seconds.
        total_pause_duration_s: Total paused time in seconds.
        avg_speed_km_h: Average moving speed in km/h.
        max_speed_km_h: Maximum recorded speed in km/h.
        total_elevation_gain_m: Total ascent in meters.
        total_elevation_loss_m: Total descent in meters.
        segment_count: Number of valid segments.
        pause_count: Number of detected pauses.
    """
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
    """Cycling activity recorded by the athlete or imported from a provider.

    Attributes:
        id: Local database id.
        athlete_id: Owner athlete id.
        tenant_id: Tenant id for multi-tenant isolation.
        date: ISO-8601 date string (YYYY-MM-DD).
        distance_km: Total distance in kilometers.
        duration_minutes: Total duration in minutes.
        avg_speed_kmh: Average speed in km/h.
        weight_kg: Athlete + bike weight in kg.
        calories: Estimated calories burned.
        heart_rate_avg: Average heart rate in bpm.
        elevation_gain_m: Total ascent in meters.
        external_source: Import source (e.g. ``strava``, ``garmin``).
        external_id: External provider activity id.
        title: User-defined ride title.
        gps_points: Raw/cleaned GPS track.
        created_at: ISO-8601 creation timestamp.
        activity_type: Activity type (``ride``, ``run``, etc.).
        is_official: Whether the ride is official or manual/demo.
        source: ``manual`` or ``imported``.
    """
    id: int | None = None
    athlete_id: int | None = None
    tenant_id: int = 0
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
    activity_type: str = "ride"
    is_official: bool = True
    source: str = "manual"

    @property
    def duration_hours(self) -> float:
        """Duration expressed in hours."""
        return self.duration_minutes / 60.0

    def to_dict(self) -> dict:
        """Serialize the ride to a JSON-compatible dict."""
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
            "activity_type": self.activity_type,
            "is_official": self.is_official,
            "source": self.source,
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
    """Athlete profile with training history and preferences.

    Attributes:
        id: Local database id.
        name: Display name.
        age: Age in years.
        weight_kg: Body mass in kg.
        height_cm: Height in cm.
        fat_percentage: Body fat percentage.
        years_active: Years since first regular training.
        weekly_sessions: Average weekly training sessions.
        monthly_hours: Average monthly training hours.
        annual_hours: Average annual training hours.
        experience_level: ``Beginner``, ``Amateur``, ``Intermediate``, ``Advanced``, ``Elite``.
        goals: Free-text training goals.
        preferred_terrain: Preferred terrain (e.g. ``mixed``, ``mountain``, ``flat``).
        weekly_volume_km: Average weekly distance in km.
        best_segments: Favorite or personal-best segments.
        medical_notes: Health notes relevant to training.
        equipment: Available bikes/equipment.
        ftp_watts: Functional Threshold Power in watts.
        created_at: ISO-8601 creation timestamp.
    """
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
        """Serialize the athlete profile to a JSON-compatible dict."""
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
    """Training or race event scheduled on the athlete's calendar.

    Attributes:
        id: Local database id.
        athlete_id: Owner athlete id.
        title: Event title.
        event_type: ``training``, ``race``, or ``recovery``.
        date: ISO-8601 date string (YYYY-MM-DD).
        duration_minutes: Event duration in minutes.
        description: Optional event notes.
        completed: Whether the event has been completed.
        created_at: ISO-8601 creation timestamp.
    """
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
        """Serialize the calendar event to a JSON-compatible dict."""
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
