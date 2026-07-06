import pytest

from bike_analyzer.backend.analytics.ride_route_estimator import estimate_route_preferences
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def _athlete(overrides=None):
    data = {
        "name": "Test",
        "age": 30,
        "weight_kg": 70.0,
        "experience_level": "Intermediate",
        "ftp_watts": 250.0,
        "weekly_volume_km": 150.0,
        "annual_hours": 200.0,
        "years_active": 5,
        "weekly_sessions": 4,
        "monthly_hours": 40.0,
        "goals": "granfondo",
        "preferred_terrain": "mountain",
    }
    if overrides:
        data.update(overrides)
    return AthleteProfile(**data)


def _ride(overrides=None):
    data = {
        "id": 1,
        "date": "2024-06-01T10:00:00Z",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "avg_speed_kmh": 25.0,
        "elevation_gain_m": 200.0,
        "calories": 600.0,
    }
    if overrides:
        data.update(overrides)
    return Ride(**data)


def test_no_rides_default_suggestion():
    athlete = _athlete()
    suggestions = estimate_route_preferences(athlete, [])
    assert len(suggestions) >= 1
    assert suggestions[0].distance_km > 0


def test_suggests_endurance_and_speed():
    athlete = _athlete()
    rides = [
        _ride({"distance_km": 30, "duration_minutes": 90, "avg_speed_kmh": 22, "elevation_gain_m": 300}),
        _ride({"distance_km": 35, "duration_minutes": 100, "avg_speed_kmh": 23, "elevation_gain_m": 350}),
    ]
    suggestions = estimate_route_preferences(athlete, rides)
    names = [s.name for s in suggestions]
    assert "Endurance base" in names
    assert "Speed work" in names


def test_hilly_route_added_for_elevation():
    athlete = _athlete()
    rides = [
        _ride({"distance_km": 30, "duration_minutes": 90, "avg_speed_kmh": 22, "elevation_gain_m": 500}),
        _ride({"distance_km": 32, "duration_minutes": 95, "avg_speed_kmh": 22, "elevation_gain_m": 550}),
    ]
    suggestions = estimate_route_preferences(athlete, rides)
    names = [s.name for s in suggestions]
    assert "Climbing repeat" in names
