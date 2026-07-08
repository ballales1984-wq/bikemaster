"""Tests for core domain models."""

from __future__ import annotations

from datetime import UTC, datetime

from bike_analyzer.core.models import (
    AthleteProfile,
    CalendarEvent,
    GPSPoint,
    Pause,
    Ride,
    RouteStatistics,
    Segment,
    haversine_distance_m,
)


def test_haversine_distance_m_zero():
    assert haversine_distance_m(0.0, 0.0, 0.0, 0.0) == 0.0


def test_haversine_distance_m_known():
    dist = haversine_distance_m(45.0, 9.0, 45.1, 9.1)
    assert dist > 0.0
    assert dist < 20000.0


def test_gps_point_distance_to():
    a = GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    b = GPSPoint(lat=45.1, lon=9.1, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    assert a.distance_to(b) > 0.0


def test_ride_to_dict_without_gps():
    ride = Ride(id=1, date="2024-01-01", distance_km=10.0)
    d = ride.to_dict()
    assert d["id"] == 1
    assert "gps_points" not in d


def test_ride_to_dict_with_gps():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=20.0),
        GPSPoint(lat=45.1, lon=9.1, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=22.0),
    ]
    ride = Ride(id=1, gps_points=points)
    d = ride.to_dict()
    assert "gps_points" in d
    assert len(d["gps_points"]) == 2
    assert d["gps_points"][0]["speed"] == 20.0


def test_ride_duration_hours():
    ride = Ride(duration_minutes=120.0)
    assert ride.duration_hours == 2.0


def test_athlete_profile_to_dict():
    profile = AthleteProfile(id=1, name="Test", ftp_watts=250.0)
    d = profile.to_dict()
    assert d["id"] == 1
    assert d["name"] == "Test"
    assert d["ftp_watts"] == 250.0


def test_calendar_event_to_dict():
    event = CalendarEvent(id=1, title="Morning Ride", completed=True)
    d = event.to_dict()
    assert d["id"] == 1
    assert d["completed"] is True


def test_segment_defaults():
    a = GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    b = GPSPoint(lat=45.1, lon=9.1, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    seg = Segment(start=a, end=b)
    assert seg.distance_m == 0.0
    assert seg.duration_s == 0.0


def test_pause_defaults():
    now = datetime(2024, 1, 1, tzinfo=UTC)
    pause = Pause(start=now, end=now)
    assert pause.duration_s == 0.0


def test_route_statistics_defaults():
    stats = RouteStatistics()
    assert stats.total_distance_m == 0.0
    assert stats.segment_count == 0
    assert stats.pause_count == 0
