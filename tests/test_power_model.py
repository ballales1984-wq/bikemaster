"""Tests for power_model.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bike_analyzer.backend.analytics.power_model import (
    calculate_advanced_power_metrics,
    calculate_power_profile,
    calculate_power_zones,
    detect_aerobic_decoupling,
    efficiency_factor,
    estimate_critical_power,
    estimate_ftp_from_20min,
    intensity_factor,
    normalized_power,
    training_stress_score,
    variability_index,
)
from bike_analyzer.backend.models.models import GPSPoint


def _ts(minutes: int) -> datetime:
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return base + timedelta(minutes=minutes)


def test_normalized_power_short_series():
    assert normalized_power([], window_size=30) == 0.0
    assert normalized_power([100.0], window_size=30) == 100.0
    assert normalized_power([200.0, 300.0, 250.0], window_size=30) == pytest.approx(250.0, abs=1.0)


def test_normalized_power_widow_effect():
    watts = [100.0] * 50 + [400.0] * 50
    np = normalized_power(watts, window_size=30)
    assert np > 200.0
    assert np < 400.0


def test_intensity_factor():
    assert intensity_factor(300.0, 250.0) == pytest.approx(1.2, abs=0.01)
    assert intensity_factor(300.0, 0.0) == 0.0


def test_variability_index():
    assert variability_index(300.0, 250.0) == pytest.approx(1.2, abs=0.01)
    assert variability_index(300.0, 0.0) == 0.0


def test_efficiency_factor():
    assert efficiency_factor(300.0, 150.0) == pytest.approx(2.0, abs=0.01)
    assert efficiency_factor(300.0, 0.0) == 0.0


def test_training_stress_score():
    assert training_stress_score(300.0, 1.2, 1.0) == pytest.approx(144.0, abs=0.1)
    assert training_stress_score(300.0, 1.2, 10.0) == 500.0
    assert training_stress_score(300.0, 0.0, 1.0) == 0.0


def test_calculate_power_zones_empty_points():
    zones = calculate_power_zones([], ftp=250.0)
    assert zones == {}


def test_calculate_power_zones_with_power():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(i), power=140.0 + i * 25.0)
        for i in range(10)
    ]
    zones = calculate_power_zones(points, ftp=250.0)
    assert "Z1" in zones
    assert "Z7" in zones
    total_count = sum(z["count"] for z in zones.values())
    assert total_count == 10


def test_calculate_power_profile_empty():
    profile = calculate_power_profile([])
    assert profile["5s"] is None
    assert profile["20min"] is None


def test_calculate_power_profile_best_efforts():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=base + timedelta(seconds=i), power=300.0)
        for i in range(1201)
    ]
    profile = calculate_power_profile(points)
    assert profile["5s"] is not None
    assert profile["1min"] is not None
    assert profile["20min"] is not None


def test_estimate_ftp_from_20min():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    ride = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=base + timedelta(seconds=i), power=300.0)
        for i in range(1200)
    ]
    ftp = estimate_ftp_from_20min(ride)
    assert ftp == pytest.approx(285.0, abs=1.0)


def test_estimate_critical_power_insufficient():
    ride = [GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(0), power=200.0)]
    result = estimate_critical_power(ride)
    assert result["cp_w"] == 0.0
    assert result["w_prime_j"] == 0.0


def test_estimate_critical_power_valid():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=base + timedelta(seconds=i), power=350.0 if i < 300 else 300.0)
        for i in range(601)
    ]
    result = estimate_critical_power(points)
    assert result["cp_w"] > 0
    assert result["w_prime_j"] > 0


def test_detect_aerobic_decoupling_short():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(i), power=200.0, heart_rate=150.0) for i in range(10)]
    result = detect_aerobic_decoupling(points, ftp=250.0)
    assert result["decoupling_pct"] == 0.0
    assert result["significant"] is False


def test_detect_aerobic_decoupling_significant():
    first = [GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(i), power=200.0, heart_rate=150.0) for i in range(30)]
    second = [GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(30 + i), power=200.0, heart_rate=165.0) for i in range(30)]
    result = detect_aerobic_decoupling(first + second, ftp=250.0)
    assert result["significant"] is True
    assert result["first_half_hr"] == pytest.approx(150.0, abs=0.1)
    assert result["second_half_hr"] == pytest.approx(165.0, abs=0.1)


def test_calculate_advanced_power_metrics_no_power():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(0))]
    result = calculate_advanced_power_metrics(points, ftp=250.0)
    assert result["available"] is False
    assert result["reason"] == "no_power_data"


def test_calculate_advanced_power_metrics_with_power():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=_ts(i), power=220.0 + (i % 10) * 5.0, heart_rate=140.0)
        for i in range(40)
    ]
    result = calculate_advanced_power_metrics(points, ftp=250.0)
    assert result["available"] is True
    assert "normalized_power_w" in result
    assert "tss" in result
    assert "decoupling" in result