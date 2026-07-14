"""Tests for the session/domain fusion model in ``core/session.py``.

Covers the pure domain entities (``SessionData``, ``HealthSample``,
``FusionRecord``, ``Recommendation``) and enums. No DB required.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bike_analyzer.core.models import GPSPoint, Ride
from bike_analyzer.core.session import (
    ActivityType,
    FusionRecord,
    HealthMetricType,
    HealthSample,
    Recommendation,
    SensorSample,
    SessionData,
    SessionMode,
)


def _point(lat: float, lon: float, minutes: int) -> GPSPoint:
    return GPSPoint(
        lat=lat,
        lon=lon,
        timestamp=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC).replace(minute=minutes),
    )


class TestEnums:
    def test_activity_type_values(self):
        assert set(ActivityType.values()) == {
            "ride",
            "walk",
            "hike",
            "run",
            "indoor",
            "other",
        }

    def test_session_mode_members(self):
        assert SessionMode.LIVE.value == "live"
        assert SessionMode.BACKGROUND.value == "background"
        assert SessionMode.OFF.value == "off"

    def test_health_metric_type_members(self):
        assert HealthMetricType.SLEEP_HOURS.value == "sleep_hours"
        assert HealthMetricType.HRV_MS.value == "hrv_ms"
        assert HealthMetricType.STEPS.value == "steps"
        assert HealthMetricType.RESTING_HR.value == "resting_hr"
        assert HealthMetricType.WEIGHT_KG.value == "weight_kg"
        assert HealthMetricType.BLOOD_OXYGEN.value == "blood_oxygen"


class TestSensorSample:
    def test_defaults(self):
        sample = SensorSample(timestamp=datetime(2024, 6, 1, tzinfo=UTC))
        assert sample.heart_rate is None
        assert sample.cadence is None
        assert sample.power is None

    def test_full(self):
        sample = SensorSample(
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            heart_rate=140.0,
            cadence=90.0,
            power=250.0,
        )
        assert sample.heart_rate == 140.0
        assert sample.cadence == 90.0
        assert sample.power == 250.0


class TestSessionDataToRide:
    def test_empty_points(self):
        session = SessionData(athlete_id=1)
        ride = session.to_ride()
        assert isinstance(ride, Ride)
        assert ride.athlete_id == 1
        assert ride.distance_km == 0.0
        assert ride.duration_minutes == 0.0
        assert ride.avg_speed_kmh == 0.0
        assert ride.heart_rate_avg is None
        assert ride.activity_type == "ride"
        assert ride.is_official is True
        assert ride.source == "gps_tracking"

    def test_with_points_and_sensors(self):
        p0 = _point(45.0, 9.0, 0)
        p1 = _point(45.001, 9.001, 1)
        session = SessionData(
            athlete_id=7,
            tenant_id=3,
            mode=SessionMode.BACKGROUND,
            activity_type=ActivityType.RUN,
            started_at=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
            points=[p0, p1],
            sensor_samples=[
                SensorSample(timestamp=p0.timestamp, heart_rate=120.0),
                SensorSample(timestamp=p1.timestamp, heart_rate=160.0),
            ],
            title="Morning run",
            is_official=False,
            source="phone",
        )
        ride = session.to_ride()
        # Distance is the haversine gap between the two points (in km).
        expected_distance_m = p0.distance_to(p1)
        assert ride.distance_km == pytest.approx(expected_distance_m / 1000.0)
        # Two points 1 minute apart -> 1 minute duration.
        assert ride.duration_minutes == pytest.approx(1.0)
        assert ride.avg_speed_kmh == pytest.approx((expected_distance_m / 1000.0) / (1.0 / 60.0))
        assert ride.heart_rate_avg == pytest.approx(140.0)
        assert ride.tenant_id == 3
        assert ride.activity_type == "run"
        assert ride.title == "Morning run"
        assert ride.is_official is False
        assert ride.source == "phone"
        assert ride.gps_points == [p0, p1]


class TestHealthSample:
    def test_to_dict(self):
        sample = HealthSample(
            athlete_id=4,
            date="2024-06-01",
            metric_type=HealthMetricType.SLEEP_HOURS,
            value=7.5,
            tenant_id=2,
            source="google_fit",
        )
        assert sample.to_dict() == {
            "athlete_id": 4,
            "tenant_id": 2,
            "date": "2024-06-01",
            "metric_type": "sleep_hours",
            "value": 7.5,
            "source": "google_fit",
        }


class TestFusionRecord:
    def test_to_dict(self):
        record = FusionRecord(
            athlete_id=5,
            tenant_id=1,
            date="2024-06-01",
            activity={"distance_km": 30.0},
            health=[{"metric_type": "sleep_hours", "value": 8.0}],
            weather={"temp_c": 20.0},
            traffic_risk=0.3,
            fitness_state={"ctl": 50.0},
        )
        assert record.to_dict() == {
            "athlete_id": 5,
            "tenant_id": 1,
            "date": "2024-06-01",
            "activity": {"distance_km": 30.0},
            "health": [{"metric_type": "sleep_hours", "value": 8.0}],
            "weather": {"temp_c": 20.0},
            "traffic_risk": 0.3,
            "fitness_state": {"ctl": 50.0},
        }

    def test_to_dict_defaults(self):
        record = FusionRecord(athlete_id=5)
        d = record.to_dict()
        assert d["athlete_id"] == 5
        assert d["activity"] is None
        assert d["health"] == []
        assert d["weather"] is None
        assert d["traffic_risk"] is None
        assert d["fitness_state"] is None


class TestRecommendation:
    def test_to_dict_with_created_at(self):
        rec = Recommendation(
            athlete_id=9,
            kind="recovery",
            text="Rest tomorrow",
            tenant_id=4,
            created_at="2024-06-01T10:00:00",
        )
        assert rec.to_dict() == {
            "athlete_id": 9,
            "tenant_id": 4,
            "kind": "recovery",
            "text": "Rest tomorrow",
            "created_at": "2024-06-01T10:00:00",
        }

    def test_to_dict_defaults_created_at(self):
        rec = Recommendation(athlete_id=9, kind="nutrition", text="Eat carbs")
        d = rec.to_dict()
        assert d["created_at"] is not None
        assert d["kind"] == "nutrition"
        assert d["text"] == "Eat carbs"
