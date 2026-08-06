"""Core domain models for BikeMaster.

This module contains the pure domain entities independent of any
infrastructure concern (DB, API, serialization).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in meters between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    sin_dphi = math.sin(dphi / 2)
    sin_dlambda = math.sin(dlambda / 2)
    arg = sin_dphi**2 + math.cos(phi1) * math.cos(phi2) * sin_dlambda**2
    arg = min(1.0, max(0.0, arg))
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(arg))


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
    timestamp: datetime | None = None
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
                logger.warning("Invalid GPS timestamp format: %r", ts)
                return
        if isinstance(ts, datetime) and ts.tzinfo is not None:
            ts = ts.astimezone(UTC).replace(tzinfo=None)
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

    def __post_init__(self) -> None:
        if self.gps_points and any(isinstance(p, dict) for p in self.gps_points):
            base_ts = self.date if self.date else None
            converted: list[GPSPoint] = []
            for p in self.gps_points:
                if isinstance(p, dict):
                    p = dict(p)
                    if "timestamp" not in p and base_ts:
                        p["timestamp"] = base_ts
                    try:
                        converted.append(GPSPoint(**p))
                    except Exception as exc:
                        logger.warning("Dropping invalid GPS point during Ride init: %s (%s)", p, exc)
                        converted.append(p)
                else:
                    converted.append(p)
            object.__setattr__(self, "gps_points", converted)

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
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
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
        body_water_percentage: Total body water percentage.
        muscle_mass_percentage: Skeletal muscle mass percentage.
        bmr_kcal: Basal metabolic rate in kcal.
        fat_mass_kg: Total body fat mass in kg.
        subcutaneous_fat_kg: Subcutaneous fat mass in kg.
        subcutaneous_fat_percentage: Subcutaneous fat percentage.
        visceral_fat_level: Visceral fat level.
        visceral_fat_percentage: Visceral fat percentage.
        visceral_fat_kg: Visceral fat mass in kg.
        muscle_mass_kg: Skeletal muscle mass in kg.
        bone_mass_kg: Bone mass in kg.
        protein_percentage: Protein percentage.
        protein_kg: Protein mass in kg.
        body_age: Metabolic body age.
        apparent_age: Apparent age vs chronological age.
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
    body_water_percentage: float | None = None
    muscle_mass_percentage: float | None = None
    bmr_kcal: float | None = None
    fat_mass_kg: float | None = None
    subcutaneous_fat_kg: float | None = None
    subcutaneous_fat_percentage: float | None = None
    visceral_fat_level: float | None = None
    visceral_fat_percentage: float | None = None
    visceral_fat_kg: float | None = None
    muscle_mass_kg: float | None = None
    bone_mass_kg: float | None = None
    protein_percentage: float | None = None
    protein_kg: float | None = None
    body_age: int | None = None
    apparent_age: int | None = None
    bmi: float | None = None
    lean_body_mass_kg: float | None = None
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
            "body_water_percentage": self.body_water_percentage,
            "muscle_mass_percentage": self.muscle_mass_percentage,
            "bmr_kcal": self.bmr_kcal,
            "fat_mass_kg": self.fat_mass_kg,
            "subcutaneous_fat_kg": self.subcutaneous_fat_kg,
            "subcutaneous_fat_percentage": self.subcutaneous_fat_percentage,
            "visceral_fat_level": self.visceral_fat_level,
            "visceral_fat_percentage": self.visceral_fat_percentage,
            "visceral_fat_kg": self.visceral_fat_kg,
            "muscle_mass_kg": self.muscle_mass_kg,
            "bone_mass_kg": self.bone_mass_kg,
            "protein_percentage": self.protein_percentage,
            "protein_kg": self.protein_kg,
            "body_age": self.body_age,
            "apparent_age": self.apparent_age,
            "bmi": self.bmi,
            "lean_body_mass_kg": self.lean_body_mass_kg,
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


@dataclass
class MetabolicProfile:
    """Athlete metabolic profile for BMR/TDEE calculation.

    Attributes:
        athlete_id: Owner athlete id.
        sex: Biological sex for Mifflin-St Jeor.
        bmr_formula: ``mifflin`` or ``cunningham``.
        activity_level: ``sedentary``, ``light``, ``moderate``, ``active``, ``very_active``.
        bmr_kcal: Cached or manually overridden BMR.
        tdee_kcal: Cached or manually overridden TDEE.
        notes: Free-text metabolic notes.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 update timestamp.
    """
    athlete_id: int | None = None
    sex: str = "male"
    bmr_formula: str = "mifflin"
    activity_level: str = "moderate"
    bmr_kcal: float | None = None
    tdee_kcal: float | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "athlete_id": self.athlete_id,
            "sex": self.sex,
            "bmr_formula": self.bmr_formula,
            "activity_level": self.activity_level,
            "bmr_kcal": self.bmr_kcal,
            "tdee_kcal": self.tdee_kcal,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class FoodLog:
    """Single food log entry for daily nutrition tracking.

    Attributes:
        id: Local database id.
        athlete_id: Owner athlete id.
        tenant_id: Tenant id for multi-tenant isolation.
        date: ISO-8601 date string (YYYY-MM-DD).
        meal_type: ``breakfast``, ``lunch``, ``dinner``, ``snack``, ``other``.
        description: Free-text food description.
        kcal: Energy in kcal.
        carbs_g: Carbohydrates in grams.
        protein_g: Protein in grams.
        fat_g: Fat in grams.
        fiber_g: Fiber in grams.
        water_ml: Water intake in ml.
        note: Optional notes.
        recorded_at: ISO-8601 timestamp of the entry.
        created_at: ISO-8601 creation timestamp.
    """
    id: int | None = None
    athlete_id: int | None = None
    tenant_id: int = 0
    date: str = ""
    meal_type: str = "other"
    description: str = ""
    kcal: float = 0.0
    carbs_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    water_ml: float | None = None
    note: str | None = None
    recorded_at: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "date": self.date,
            "meal_type": self.meal_type,
            "description": self.description,
            "kcal": self.kcal,
            "carbs_g": self.carbs_g,
            "protein_g": self.protein_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g,
            "water_ml": self.water_ml,
            "note": self.note,
            "recorded_at": self.recorded_at,
            "created_at": self.created_at,
        }


@dataclass
class MetabolicDailySummary:
    """Aggregated daily metabolic and nutrition summary.

    Attributes:
        id: Local database id.
        athlete_id: Owner athlete id.
        tenant_id: Tenant id for multi-tenant isolation.
        date: ISO-8601 date string (YYYY-MM-DD).
        bmr_kcal: Basal Metabolic Rate.
        neat_kcal: Non-Exercise Activity Thermogenesis.
        eat_kcal: Exercise Activity Thermogenesis.
        climb_bonus_kcal: Extra kcal from elevation gain.
        tdee_kcal: Total Daily Energy Expenditure.
        intake_kcal: Total kcal from food logs.
        balance_kcal: intake_kcal - tdee_kcal.
        steps_estimated: Estimated step count.
        elevation_gain_estimated_m: Total elevation gain for the day.
        rides_count: Number of rides/activities for the day.
        gps_neat_kcal: NEAT estimated from GPS low-speed segments.
        notes: Free-text notes.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 update timestamp.
    """
    id: int | None = None
    athlete_id: int | None = None
    tenant_id: int = 0
    date: str = ""
    bmr_kcal: float = 0.0
    neat_kcal: float = 0.0
    eat_kcal: float = 0.0
    climb_bonus_kcal: float = 0.0
    tdee_kcal: float = 0.0
    intake_kcal: float = 0.0
    balance_kcal: float = 0.0
    steps_estimated: int | None = None
    elevation_gain_estimated_m: float | None = None
    rides_count: int = 0
    gps_neat_kcal: float = 0.0
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "date": self.date,
            "bmr_kcal": self.bmr_kcal,
            "neat_kcal": self.neat_kcal,
            "eat_kcal": self.eat_kcal,
            "climb_bonus_kcal": self.climb_bonus_kcal,
            "tdee_kcal": self.tdee_kcal,
            "intake_kcal": self.intake_kcal,
            "balance_kcal": self.balance_kcal,
            "steps_estimated": self.steps_estimated,
            "elevation_gain_estimated_m": self.elevation_gain_estimated_m,
            "rides_count": self.rides_count,
            "gps_neat_kcal": self.gps_neat_kcal,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
