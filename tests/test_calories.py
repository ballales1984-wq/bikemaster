"""Tests for analytics calorie estimation."""

from __future__ import annotations

from bike_analyzer.backend.analytics.calories import (
    calculate_calories_met,
    calculate_calories_physics,
    calories_per_km,
    ensure_calories,
    estimate_calories,
)
from bike_analyzer.backend.models.models import Ride


class TestEstimateCalories:
    def test_met_method_returns_positive(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=70.0)
        assert estimate_calories(ride, method="met") > 0

    def test_physics_method_returns_positive(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=70.0)
        assert estimate_calories(ride, method="physics") > 0

    def test_zero_duration_returns_zero(self):
        ride = Ride(duration_minutes=0, distance_km=0, avg_speed_kmh=0, weight_kg=70.0)
        assert estimate_calories(ride) == 0.0

    def test_longer_ride_more_calories(self):
        short = Ride(duration_minutes=30.0, distance_km=15.0, avg_speed_kmh=30.0, weight_kg=70.0)
        long = Ride(duration_minutes=120.0, distance_km=60.0, avg_speed_kmh=30.0, weight_kg=70.0)
        assert estimate_calories(long) > estimate_calories(short)


class TestCalculateCaloriesMet:
    def test_returns_positive(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=70.0)
        assert calculate_calories_met(ride) > 0


class TestCalculateCaloriesPhysics:
    def test_returns_positive(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=70.0)
        assert calculate_calories_physics(ride) > 0


class TestCaloriesPerKm:
    def test_zero_distance_returns_zero(self):
        ride = Ride(distance_km=0, calories=0)
        assert calories_per_km(ride) == 0.0

    def test_calculates_correctly(self):
        ride = Ride(distance_km=10.0, calories=500.0)
        assert calories_per_km(ride) == 50.0


class TestEnsureCalories:
    def test_existing_calories_returned(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=70.0, calories=600.0)
        assert ensure_calories(ride) == 600.0

    def test_missing_calories_estimated(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=70.0, calories=0)
        result = ensure_calories(ride)
        assert result > 0

    def test_zero_speed_returns_zero(self):
        ride = Ride(duration_minutes=60.0, distance_km=0, avg_speed_kmh=0, weight_kg=70.0, calories=0)
        assert ensure_calories(ride) == 0.0

    def test_compute_missing_avg_speed_from_distance_and_duration(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=0, weight_kg=70.0, calories=0)
        result = ensure_calories(ride)
        assert ride.avg_speed_kmh == 0
        assert result > 0

    def test_default_weight_when_missing(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=30.0, weight_kg=0, calories=0)
        result = ensure_calories(ride)
        assert ride.weight_kg == 0
        assert result > 0

    def test_does_not_mutate_original_ride(self):
        ride = Ride(duration_minutes=60.0, distance_km=30.0, avg_speed_kmh=0, weight_kg=0, calories=0)
        original_speed = ride.avg_speed_kmh
        original_weight = ride.weight_kg
        ensure_calories(ride)
        assert ride.avg_speed_kmh == original_speed
        assert ride.weight_kg == original_weight
