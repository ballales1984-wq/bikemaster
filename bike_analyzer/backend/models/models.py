"""Backend API domain models.

These re-export the canonical pure domain entities defined in
``bike_analyzer.core.models`` so there is a single source of truth instead of two
divergent copies. The only backend-specific behavior is ``Ride.to_dict``: it returns
the API-shaped dict and deliberately omits ``gps_points`` (which arrive from the DB as
plain dicts and are serialized separately by the async facade). Core GPS points use
the ``altitude`` field name, matching the data produced by the GPX/FIT parsers.
"""

from __future__ import annotations

from dataclasses import dataclass

from bike_analyzer.core.models import (
    EARTH_RADIUS_M,
    AthleteProfile,
    CalendarEvent,
    GPSPoint,
    Pause,
    RouteStatistics,
    Segment,
    haversine_distance_m,
)
from bike_analyzer.core.models import (
    Ride as _CoreRide,
)


@dataclass
class Ride(_CoreRide):
    """API-oriented Ride whose ``to_dict`` omits raw gps_points."""

    def to_dict(self) -> dict:
        return {
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


__all__ = [
    "GPSPoint",
    "Segment",
    "Pause",
    "RouteStatistics",
    "Ride",
    "AthleteProfile",
    "CalendarEvent",
    "haversine_distance_m",
    "EARTH_RADIUS_M",
]
