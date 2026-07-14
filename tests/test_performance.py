"""Tests for analytics performance model."""

from __future__ import annotations

import pytest

from bike_analyzer.backend.analytics.fatigue import calculate_fatigue_score
from bike_analyzer.backend.analytics.performance import (
    calculate_annual_scores,
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_monthly_scores,
    calculate_performance_score,
    calculate_recovery_score,
    classify_athlete,
    get_experience_level,
    should_save_to_database,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


class TestCalculatePerformanceScore:
    def test_fast_ride_scores_higher(self):
        slow = Ride(avg_speed_kmh=15.0, duration_minutes=60.0, elevation_gain_m=0, distance_km=15.0, calories=300)
        fast = Ride(avg_speed_kmh=30.0, duration_minutes=60.0, elevation_gain_m=0, distance_km=30.0, calories=600)
        assert calculate_performance_score(fast) > calculate_performance_score(slow)

    def test_long_ride_scores_higher(self):
        short = Ride(avg_speed_kmh=25.0, duration_minutes=30.0, elevation_gain_m=0, distance_km=12.5, calories=250)
        long = Ride(avg_speed_kmh=25.0, duration_minutes=180.0, elevation_gain_m=0, distance_km=75.0, calories=750)
        assert calculate_performance_score(long) > calculate_performance_score(short)

    def test_elevation_contributes(self):
        flat = Ride(avg_speed_kmh=25.0, duration_minutes=60.0, elevation_gain_m=0, distance_km=25.0, calories=500)
        hilly = Ride(avg_speed_kmh=25.0, duration_minutes=60.0, elevation_gain_m=500.0, distance_km=25.0, calories=550)
        assert calculate_performance_score(hilly) > calculate_performance_score(flat)

    def test_capped_at_10(self):
        ride = Ride(avg_speed_kmh=50.0, duration_minutes=600.0, elevation_gain_m=5000.0, distance_km=500.0, calories=5000)
        assert calculate_performance_score(ride) <= 10.0

    def test_rounded_to_one_decimal(self):
        ride = Ride(avg_speed_kmh=25.0, duration_minutes=90.0, elevation_gain_m=250.0, distance_km=37.5, calories=600)
        score = calculate_performance_score(ride)
        assert score == round(score, 1)


class TestCalculateEnduranceScore:
    def test_empty_rides_returns_zero(self):
        assert calculate_endurance_score([]) == 0.0

    def test_many_long_rides_scores_high(self):
        rides = [Ride(duration_minutes=180.0, distance_km=80.0) for _ in range(20)]
        assert calculate_endurance_score(rides) >= 7.0

    def test_short_rides_scores_low(self):
        rides = [Ride(duration_minutes=30.0, distance_km=10.0) for _ in range(5)]
        assert calculate_endurance_score(rides) <= 3.0


class TestCalculateRecoveryScore:
    def test_inverse_of_fatigue(self):
        ride = Ride(duration_minutes=120.0, avg_speed_kmh=25.0, distance_km=50.0, elevation_gain_m=300.0, weight_kg=70.0)
        rec = calculate_recovery_score(ride)
        fat = calculate_fatigue_score(ride)
        assert round(rec + fat, 1) == 10.0

    def test_high_fatigue_low_recovery(self):
        ride = Ride(duration_minutes=360.0, avg_speed_kmh=45.0, heart_rate_avg=190, distance_km=250.0, elevation_gain_m=4000.0, weight_kg=70.0)
        assert calculate_recovery_score(ride) <= 4.0


class TestCalculateEfficiencyScore:
    def test_zero_distance_returns_zero(self):
        ride = Ride(distance_km=0, calories=0)
        assert calculate_efficiency_score(ride) == 0.0

    def test_low_calories_per_km_scores_high(self):
        ride = Ride(distance_km=50.0, calories=1000)
        assert calculate_efficiency_score(ride) >= 7.0

    def test_high_calories_per_km_scores_low(self):
        ride = Ride(distance_km=10.0, calories=800)
        assert calculate_efficiency_score(ride) <= 5.0


class TestClassifyAthlete:
    def test_empty_rides_unclassified(self):
        assert classify_athlete([]) == "Unclassified"

    def test_beginner(self):
        rides = [Ride(distance_km=10.0) for _ in range(5)]
        assert classify_athlete(rides) == "Beginner"

    def test_elite(self):
        rides = [Ride(distance_km=100.0) for _ in range(200)]
        assert classify_athlete(rides) == "Elite"


class TestGetExperienceLevel:
    def test_returns_athlete_level(self):
        athlete = AthleteProfile(experience_level="Advanced")
        assert get_experience_level(athlete) == "Advanced"


class TestShouldSaveToDatabase:
    def test_valid_points_returns_true(self):
        from datetime import datetime
        from bike_analyzer.core.models import GPSPoint
        points = [GPSPoint(lat=45.0, lon=7.0, altitude=100.0, timestamp=datetime.now())]
        assert should_save_to_database(points) is True

    def test_empty_points_returns_false(self):
        assert should_save_to_database([]) is False
