"""Tests for ATL/CTL/TSB training load model."""

from bike_analyzer.backend.analytics.training_load import (
    calculate_atl_ctl_tsb,
    calculate_rss,
    get_current_training_status,
)
from bike_analyzer.backend.models.models import Ride


def test_calculate_rss_basic():
    """Test TSS calculation for basic ride."""
    ride = Ride(date="2024-01-15", distance_km=50.0, duration_minutes=120.0, avg_speed_kmh=25.0)
    tss = calculate_rss(ride)
    assert 0 <= tss <= 200
    assert tss > 0


def test_calculate_rss_with_elevation():
    """Test TSS calculation with elevation gain."""
    ride = Ride(
        date="2024-01-15",
        distance_km=30.0,
        duration_minutes=90.0,
        avg_speed_kmh=20.0,
        elevation_gain_m=500.0,
    )
    tss = calculate_rss(ride)
    assert tss > 0


def test_calculate_atl_ctl_tsb_empty():
    """Test ATL/CTL/TSB with no rides."""
    result = calculate_atl_ctl_tsb([])
    assert result == []


def test_calculate_atl_ctl_tsb_single_ride():
    """Test ATL/CTL/TSB with single ride."""
    ride = Ride(date="2024-01-15", distance_km=50.0, duration_minutes=120.0, avg_speed_kmh=25.0)
    result = calculate_atl_ctl_tsb([ride])
    assert len(result) >= 1
    assert result[0].atl >= 0
    assert result[0].ctl >= 0


def test_calculate_atl_ctl_tsb_multiple_rides():
    """Test ATL/CTL/TSB builds over multiple rides."""
    rides = [
        Ride(
            date=f"2024-01-{15 + i:02d}",
            distance_km=40.0,
            duration_minutes=100.0,
            avg_speed_kmh=24.0,
        )
        for i in range(7)
    ]
    result = calculate_atl_ctl_tsb(rides)
    assert len(result) >= 7
    for day in result:
        assert day.ctl >= day.atl  # CTL is chronic (longer term), should be >= ATL typically


def test_get_current_training_status_fresh():
    """Test status when TSB is high (fresh)."""
    rides = [
        Ride(date="2024-01-10", distance_km=20.0, duration_minutes=60.0, avg_speed_kmh=20.0),
    ]
    status = get_current_training_status(rides)
    assert "tsb" in status
    assert "status" in status
    assert "recommendation" in status


def test_get_current_training_status_no_rides():
    """Test status with no ride data."""
    status = get_current_training_status([])
    assert status["status"] == "no_data"
