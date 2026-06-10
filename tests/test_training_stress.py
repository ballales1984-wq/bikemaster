"""Tests for training stress score (TSS) estimation."""

from bike_analyzer.backend.analytics.training_stress import (
    estimate_tss,
    exponentially_weighted_moving_average,
)
from bike_analyzer.backend.models.models import Ride


def test_ewma_empty():
    assert exponentially_weighted_moving_average([], 7.0) == 0.0


def test_ewma_single():
    result = exponentially_weighted_moving_average([50.0], 7.0)
    assert result > 0


def test_ewma_decays():
    values = [100.0, 80.0, 60.0, 40.0, 20.0]
    result = exponentially_weighted_moving_average(values, 7.0)
    assert result > 0


def test_estimate_tss_basic():
    ride = Ride(date="2024-01-15", distance_km=50.0, duration_minutes=120.0, avg_speed_kmh=25.0)
    tss = estimate_tss(ride, ftp=250.0)
    assert 0 <= tss <= 500
    assert tss > 0


def test_estimate_tss_zero_duration():
    ride = Ride(date="2024-01-15", distance_km=0.0, duration_minutes=0.0)
    assert estimate_tss(ride) == 0.0


def test_estimate_tss_with_ftp():
    ride = Ride(date="2024-01-15", duration_minutes=90.0, avg_speed_kmh=35.0)
    tss_fast = estimate_tss(ride, ftp=250.0)
    assert tss_fast > 0
