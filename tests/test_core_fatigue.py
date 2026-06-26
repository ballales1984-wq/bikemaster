"""Tests for core fatigue calculator."""

from bike_analyzer.core.models import Ride
from bike_analyzer.core.calculators.fatigue import (
    calculate_fatigue_score,
    estimate_recovery_hours,
    get_recovery_recommendation,
)


def test_fatigue_basic():
    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=90.0,
        avg_speed_kmh=22.0,
        weight_kg=70.0,
        heart_rate_avg=150.0,
        elevation_gain_m=200.0,
    )
    f = calculate_fatigue_score(r)
    assert 0 <= f <= 10


def test_fatigue_no_hr():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=90.0, avg_speed_kmh=22.0)
    f = calculate_fatigue_score(r)
    assert 0 <= f <= 10


def test_fatigue_short_ride():
    r = Ride(date="2024-06-01", distance_km=10.0, duration_minutes=30.0, avg_speed_kmh=20.0)
    f = calculate_fatigue_score(r)
    assert 0 <= f <= 10


def test_fatigue_long_elevation():
    r = Ride(
        date="2024-06-01",
        distance_km=30.0,
        duration_minutes=150.0,
        avg_speed_kmh=20.0,
        elevation_gain_m=1000.0,
    )
    f = calculate_fatigue_score(r)
    assert 0 <= f <= 10


def test_fatigue_high_hr():
    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=90.0,
        avg_speed_kmh=20.0,
        heart_rate_avg=190.0,
    )
    f = calculate_fatigue_score(r)
    assert f > 0


def test_fatigue_no_elevation():
    r = Ride(date="2024-06-01", distance_km=30.0, duration_minutes=90.0, avg_speed_kmh=22.0, elevation_gain_m=None)
    f = calculate_fatigue_score(r)
    assert 0 <= f <= 10


def test_estimate_recovery_hours():
    assert estimate_recovery_hours(1.0) == 8.0
    assert estimate_recovery_hours(4.0) == 16.0
    assert estimate_recovery_hours(6.0) == 24.0
    assert estimate_recovery_hours(9.0) == 48.0


def test_get_recovery_recommendation():
    assert "Minimal" in get_recovery_recommendation(1.0)
    assert "Light fatigue" in get_recovery_recommendation(3.0)
    assert "Moderate fatigue" in get_recovery_recommendation(5.0)
    assert "High fatigue" in get_recovery_recommendation(7.0)
    assert "Extreme fatigue" in get_recovery_recommendation(9.0)


def test_fatigue_high_age():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=90.0, avg_speed_kmh=22.0, heart_rate_avg=180.0)
    f = calculate_fatigue_score(r, rider_age=250)
    assert 0 <= f <= 10