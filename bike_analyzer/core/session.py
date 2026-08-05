"""New Super App domain: spine that connects tracking, health and AI.

Pure entities (no dependency on DB/provider). Extend the existing model
in a backward-compatible way: `Ride` remains valid, `SessionData` is its superset.

Main components:
- ``ActivityType`` - enum of trackable activity types.
- ``SessionMode`` - enum of tracking modes (live, background, off).
- ``SensorSample`` - instant sensor reading (HR, cadence, power).
- ``SessionData`` - raw stream of a tracking session.
- ``HealthSample`` - health data sample (sleep, HRV, steps, weight).
- ``FusionRecord`` - fused snapshot for the AI Coach (health + weather + traffic + state).
- ``Recommendation`` - structured output from the AI Coach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .models import GPSPoint, Ride


class ActivityType(StrEnum):
    """Tracked activity type (superset of `ride`).

    Supported values include: ride, walk, hike, run,
    indoor activities and more.
    """

    RIDE = "ride"
    WALK = "walk"
    HIKE = "hike"
    RUN = "run"
    INDOOR = "indoor"
    OTHER = "other"

    @classmethod
    def values(cls) -> list[str]:
        """List of enum values of supported sports activities."""
        return [m.value for m in cls]


class SessionMode(StrEnum):
    """Tracking mode.

    - LIVE: official tracked and saved ride.
    - BACKGROUND: informal background tracking.
    - OFF: inactive tracking.
    """

    LIVE = "live"
    BACKGROUND = "background"
    OFF = "off"


class HealthMetricType(StrEnum):
    """Supported health sample types.

    Includes native device metrics and those imported from
    Google Fit / Apple Health.
    """

    SLEEP_HOURS = "sleep_hours"
    HRV_MS = "hrv_ms"
    STEPS = "steps"
    RESTING_HR = "resting_hr"
    WEIGHT_KG = "weight_kg"
    BLOOD_OXYGEN = "blood_oxygen"


@dataclass
class SensorSample:
    """Instant sensor reading associated with a GPS point.

    Attributes:
        timestamp: UTC timestamp of the sample.
        heart_rate: Heart rate in bpm (optional).
        cadence: Pedaling cadence in rpm (optional).
        power: Instant power in watts (optional).
    """

    timestamp: datetime
    heart_rate: float | None = None
    cadence: float | None = None
    power: float | None = None


@dataclass
class SessionData:
    """Raw stream of a tracking session (live or background).

    This is the input to `UnifiedMetricsEngine`: contains GPS + sensors + metadata,
    but NOT yet calculated metrics.
    """

    athlete_id: int | None
    tenant_id: int = 0
    mode: SessionMode = SessionMode.LIVE
    activity_type: ActivityType = ActivityType.RIDE
    started_at: datetime = field(default_factory=datetime.now)
    points: list[GPSPoint] = field(default_factory=list)
    sensor_samples: list[SensorSample] = field(default_factory=list)
    title: str | None = None
    is_official: bool = True
    source: str = "gps_tracking"

    def to_ride(self) -> Ride:
        """Promotes the session to `Ride` (existing storage entity)."""
        gps = self.points
        total_distance = sum(
            gps[i].distance_to(gps[i - 1]) for i in range(1, len(gps))
        ) if len(gps) > 1 else 0.0
        duration = 0.0
        if gps:
            span = (gps[-1].timestamp - gps[0].timestamp).total_seconds()
            duration = span / 60.0
        hr_values = [s.heart_rate for s in self.sensor_samples if s.heart_rate]
        return Ride(
            athlete_id=self.athlete_id,
            tenant_id=self.tenant_id,
            date=self.started_at.date().isoformat(),
            distance_km=total_distance / 1000.0,
            duration_minutes=duration,
            avg_speed_kmh=(total_distance / 1000.0) / (duration / 60.0) if duration else 0.0,
            heart_rate_avg=sum(hr_values) / len(hr_values) if hr_values else None,
            title=self.title,
            gps_points=gps,
            external_source=None,
            external_id=None,
            activity_type=self.activity_type.value,
            is_official=self.is_official,
            source=self.source,
        )


@dataclass
class HealthSample:
    """Health data sample (sleep, HRV, steps, weight, etc.)."""

    athlete_id: int
    date: str
    metric_type: HealthMetricType
    value: float
    tenant_id: int = 0
    source: str = "manual"

    def to_dict(self) -> dict[str, Any]:
        """Serializes the health sample into a JSON-compatible dictionary."""
        return {
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "date": self.date,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "source": self.source,
        }


@dataclass
class FusionRecord:
    """Fused snapshot ready for the AI Coach: health + weather + traffic + state.

    This is the only input the AI Coach should consume (never raw sources).
    """

    athlete_id: int
    tenant_id: int = 0
    date: str = ""
    activity: dict[str, Any] | None = None
    health: list[dict[str, Any]] = field(default_factory=list)
    weather: dict[str, Any] | None = None
    traffic_risk: float | None = None
    fitness_state: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes the fusion record into a JSON-compatible dictionary."""
        return {
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "date": self.date,
            "activity": self.activity,
            "health": self.health,
            "weather": self.weather,
            "traffic_risk": self.traffic_risk,
            "fitness_state": self.fitness_state,
        }


@dataclass
class Recommendation:
    """Structured output from the AI Coach."""

    athlete_id: int
    kind: str  # recovery | nutrition | training
    text: str
    tenant_id: int = 0
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes the recommendation into a JSON-compatible dictionary."""
        return {
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "kind": self.kind,
            "text": self.text,
            "created_at": self.created_at or datetime.now(UTC).isoformat(),
        }

