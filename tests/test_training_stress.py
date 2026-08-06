"""Tests for analytics training stress model."""

from __future__ import annotations

from bike_analyzer.backend.analytics.training_stress import (
    estimate_tss,
    exponentially_weighted_moving_average,
)
from bike_analyzer.backend.models.models import Ride


class TestExponentiallyWeightedMovingAverage:
    def test_empty_returns_zero(self):
        assert exponentially_weighted_moving_average([], tau_days=7.0) == 0.0

    def test_single_value_returns_same(self):
        assert exponentially_weighted_moving_average([5.0], tau_days=7.0) == 5.0

    def test_short_tau_fast_adaptation(self):
        values = [10.0, 20.0, 30.0]
        short = exponentially_weighted_moving_average(values, tau_days=1.0)
        long = exponentially_weighted_moving_average(values, tau_days=30.0)
        assert short > long

    def test_rounded_to_one_decimal(self):
        result = exponentially_weighted_moving_average([1.0, 2.0, 3.0], tau_days=7.0)
        assert result == round(result, 1)


class TestEstimateTss:
    def test_zero_duration_returns_zero(self):
        ride = Ride(duration_minutes=0, avg_speed_kmh=0, distance_km=0)
        assert estimate_tss(ride) == 0.0

    def test_speed_impacts_tss(self):
        slow = Ride(duration_minutes=60.0, avg_speed_kmh=20.0, distance_km=20.0)
        fast = Ride(duration_minutes=60.0, avg_speed_kmh=35.0, distance_km=35.0)
        assert estimate_tss(fast) > estimate_tss(slow)

    def test_capped_at_maximum(self):
        ride = Ride(duration_minutes=600.0, avg_speed_kmh=50.0, distance_km=500.0)
        assert estimate_tss(ride) <= 500.0

    def test_explicit_intensity_factor_used(self):
        ride = Ride(duration_minutes=60.0, avg_speed_kmh=20.0, distance_km=20.0)
        ride.intensity_factor = 0.9
        tss = estimate_tss(ride)
        assert tss > 50.0
