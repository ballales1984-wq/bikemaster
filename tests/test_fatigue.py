"""Tests for analytics fatigue model."""

from __future__ import annotations

from bike_analyzer.backend.analytics.fatigue import (
    calculate_fatigue_score,
    estimate_recovery_hours,
    get_recovery_recommendation,
)
from bike_analyzer.backend.models.models import Ride


class TestCalculateFatigueScore:
    def test_short_easy_ride_low_fatigue(self):
        ride = Ride(duration_minutes=60.0, avg_speed_kmh=20.0, distance_km=20.0, elevation_gain_m=100.0, weight_kg=70.0)
        score = calculate_fatigue_score(ride, rider_age=30)
        assert 0 <= score <= 10

    def test_long_hard_ride_high_fatigue(self):
        ride = Ride(duration_minutes=300.0, avg_speed_kmh=35.0, heart_rate_avg=175, distance_km=150.0, elevation_gain_m=3000.0, weight_kg=70.0)
        score = calculate_fatigue_score(ride, rider_age=30)
        assert score >= 5

    def test_zero_duration_returns_zero(self):
        ride = Ride(duration_minutes=0, avg_speed_kmh=0, distance_km=0, elevation_gain_m=0, weight_kg=70.0)
        score = calculate_fatigue_score(ride)
        assert score >= 0

    def test_high_hr_increases_intensity(self):
        base = Ride(duration_minutes=120.0, avg_speed_kmh=25.0, distance_km=50.0, elevation_gain_m=500.0, weight_kg=70.0, heart_rate_avg=150)
        low_hr = Ride(duration_minutes=120.0, avg_speed_kmh=25.0, distance_km=50.0, elevation_gain_m=500.0, weight_kg=70.0, heart_rate_avg=120)
        assert calculate_fatigue_score(base, rider_age=30) > calculate_fatigue_score(low_hr, rider_age=30)

    def test_high_elevation_increases_fatigue(self):
        flat = Ride(duration_minutes=120.0, avg_speed_kmh=25.0, distance_km=50.0, elevation_gain_m=0, weight_kg=70.0)
        hilly = Ride(duration_minutes=120.0, avg_speed_kmh=25.0, distance_km=50.0, elevation_gain_m=2000.0, weight_kg=70.0)
        assert calculate_fatigue_score(hilly) > calculate_fatigue_score(flat)

    def test_capped_at_maximum(self):
        extreme = Ride(duration_minutes=480.0, avg_speed_kmh=50.0, heart_rate_avg=190, distance_km=400.0, elevation_gain_m=10000.0, weight_kg=120.0)
        assert calculate_fatigue_score(extreme, rider_age=30) <= 10.0


class TestEstimateRecoveryHours:
    def test_low_fatigue_needs_8h(self):
        assert estimate_recovery_hours(2.0) == 8.0

    def test_moderate_fatigue_needs_16h(self):
        assert estimate_recovery_hours(4.5) == 16.0

    def test_high_fatigue_needs_24h(self):
        assert estimate_recovery_hours(6.5) == 24.0

    def test_extreme_fatigue_needs_48h(self):
        assert estimate_recovery_hours(9.0) == 48.0


class TestGetRecoveryRecommendation:
    def test_minimal_fatigue(self):
        assert "Minimal fatigue" in get_recovery_recommendation(1.0)

    def test_light_fatigue(self):
        assert "easy spin" in get_recovery_recommendation(3.0)

    def test_moderate_fatigue(self):
        assert "rest day" in get_recovery_recommendation(5.0)

    def test_high_fatigue(self):
        assert "rest required" in get_recovery_recommendation(7.0)

    def test_extreme_fatigue(self):
        assert "multiple rest days" in get_recovery_recommendation(9.0)
