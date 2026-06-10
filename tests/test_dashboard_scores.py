"""Tests for dashboard score aggregation and utility modules."""
from datetime import datetime, timezone

from bike_analyzer.backend.analytics.dashboard import (
    create_score_dashboard,
    get_score_breakdown,
)
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride


def test_create_score_dashboard_no_rides():
    athlete = AthleteProfile(name="Test", age=30, weight_kg=70.0, experience_level="Beginner")
    result = create_score_dashboard([], athlete)
    assert result["total_rides"] == 0
    assert result["performance"] == 0
    assert result["level"] == "Beginner"


def test_create_score_dashboard_with_rides():
    pts = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=15),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc), speed=20),
    ]
    ride = Ride(date="2024-01-01", distance_km=20.0, duration_minutes=60.0,
                avg_speed_kmh=20.0, weight_kg=70.0, calories=400)
    athlete = AthleteProfile(name="Test", age=30, weight_kg=70.0, experience_level="Intermediate")
    result = create_score_dashboard([ride], athlete)
    assert "performance" in result
    assert "endurance" in result
    assert "recovery" in result
    assert "efficiency" in result
    assert result["total_rides"] == 1


def test_get_score_breakdown():
    ride = Ride(date="2024-01-01", distance_km=25.0, duration_minutes=45.0,
                avg_speed_kmh=33.3, weight_kg=70.0, calories=500)
    breakdown = get_score_breakdown(ride)
    assert "performance" in breakdown
    assert "recovery" in breakdown
    assert "efficiency" in breakdown
