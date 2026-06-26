"""Tests for dashboard score aggregation and utility modules."""

from datetime import UTC, datetime

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
    [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=15),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=20),
    ]
    ride = Ride(
        date="2024-01-01",
        distance_km=20.0,
        duration_minutes=60.0,
        avg_speed_kmh=20.0,
        weight_kg=70.0,
        calories=400,
    )
    athlete = AthleteProfile(name="Test", age=30, weight_kg=70.0, experience_level="Intermediate")
    result = create_score_dashboard([ride], athlete)
    assert "performance" in result
    assert "endurance" in result
    assert "recovery" in result
    assert "efficiency" in result
    assert result["total_rides"] == 1


def test_get_score_breakdown():
    ride = Ride(
        date="2024-01-01",
        distance_km=25.0,
        duration_minutes=45.0,
        avg_speed_kmh=33.3,
        weight_kg=70.0,
        calories=500,
    )
    breakdown = get_score_breakdown(ride)
    assert "performance" in breakdown
    assert "recovery" in breakdown
    assert "efficiency" in breakdown


def test_create_score_dashboard_multiple_rides():
    rides = [
        Ride(date="2024-01-01", distance_km=30.0, duration_minutes=90.0, avg_speed_kmh=20.0, calories=600),
        Ride(date="2024-01-02", distance_km=40.0, duration_minutes=120.0, avg_speed_kmh=20.0, calories=800),
    ]
    athlete = AthleteProfile(name="Test", experience_level="Intermediate")
    result = create_score_dashboard(rides, athlete)
    assert result["total_rides"] == 2
    assert result["total_km"] == 70.0


def test_create_score_dashboard_level():
    rides = [Ride(date=f"2024-01-{i:02d}", distance_km=100.0) for i in range(1, 40)]
    athlete = AthleteProfile(name="Test", experience_level="Intermediate")
    result = create_score_dashboard(rides, athlete)
    assert result["level"] in ["Beginner", "Amateur", "Intermediate", "Advanced", "Elite"]
