"""Tests for analytics power model."""

from __future__ import annotations

from datetime import datetime, timedelta

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
from bike_analyzer.core.models import GPSPoint


def _gps_point(timestamp_offset: float, power: float | None = None, heart_rate: float | None = None) -> GPSPoint:
    return GPSPoint(
        lat=45.0,
        lon=7.0,
        timestamp=datetime.now() + timedelta(seconds=timestamp_offset),
        power=power,
        heart_rate=heart_rate,
    )


class TestNormalizedPower:
    def test_empty_returns_zero(self):
        assert normalized_power([]) == 0.0

    def test_single_value_returns_same(self):
        assert normalized_power([200.0]) == 200.0

    def test_smooths_variations(self):
        steady = normalized_power([200.0] * 60)
        variable = normalized_power([180.0 + (i % 5) * 10.0 for i in range(60)])
        assert steady >= variable

    def test_rounded_to_one_decimal(self):
        result = normalized_power([200.0] * 60)
        assert result == round(result, 1)


class TestIntensityFactor:
    def test_zero_ftp_returns_zero(self):
        assert intensity_factor(200.0, 0) == 0.0

    def test_calculates_correctly(self):
        assert intensity_factor(250.0, 250.0) == 1.0

    def test_rounded_to_three_decimals(self):
        result = intensity_factor(263.0, 250.0)
        assert result == round(result, 3)


class TestVariabilityIndex:
    def test_zero_avg_returns_zero(self):
        assert variability_index(200.0, 0) == 0.0

    def test_steady_ride_near_one(self):
        assert variability_index(200.0, 200.0) == 1.0


class TestEfficiencyFactor:
    def test_zero_hr_returns_zero(self):
        assert efficiency_factor(200.0, 0) == 0.0

    def test_calculates_correctly(self):
        assert efficiency_factor(200.0, 100.0) == 2.0


class TestTrainingStressScore:
    def test_zero_duration_returns_zero(self):
        assert training_stress_score(200.0, 0.8, 0) == 0.0

    def test_capped_at_maximum(self):
        assert training_stress_score(400.0, 1.5, 10.0) == 500.0

    def test_increases_with_duration(self):
        tss1 = training_stress_score(200.0, 0.8, 1.0)
        tss2 = training_stress_score(200.0, 0.8, 2.0)
        assert tss2 > tss1


class TestCalculatePowerZones:
    def test_returns_zones_dict(self):
        points = [_gps_point(i, power=200.0) for i in range(60)]
        zones = calculate_power_zones(points, ftp=250.0)
        assert "Z1" in zones
        assert "Z7" in zones

    def test_empty_points_returns_empty(self):
        assert calculate_power_zones([], ftp=250.0) == {}

    def test_zero_ftp_returns_empty(self):
        points = [_gps_point(i, power=200.0) for i in range(60)]
        assert calculate_power_zones(points, ftp=0) == {}


class TestPowerProfile:
    def test_empty_returns_none_profile(self):
        result = calculate_power_profile([])
        assert result["5s"] is None

    def test_best_effort_detected(self):
        points = [_gps_point(i, power=300.0 if 25 <= i <= 35 else 150.0) for i in range(60)]
        profile = calculate_power_profile(points)
        assert profile.get("5s") is not None


class TestEstimateFtp:
    def test_no_20min_power_returns_zero(self):
        assert estimate_ftp_from_20min([]) == 0.0

    def test_estimates_from_best_20min(self):
        points = [_gps_point(i, power=280.0) for i in range(1200)]
        ftp = estimate_ftp_from_20min(points)
        assert ftp > 0


class TestEstimateCriticalPower:
    def test_returns_dict_with_keys(self):
        points = [_gps_point(i, power=300.0) for i in range(600)]
        result = estimate_critical_power(points)
        assert "cp_w" in result
        assert "w_prime_j" in result

    def test_no_data_returns_zeros(self):
        result = estimate_critical_power([])
        assert result["cp_w"] == 0.0
        assert result["w_prime_j"] == 0.0


class TestDetectAerobicDecoupling:
    def test_insufficient_points_returns_zero(self):
        result = detect_aerobic_decoupling([_gps_point(0, power=200.0, heart_rate=150.0) for _ in range(10)])
        assert result["decoupling_pct"] == 0.0

    def test_significant_decoupling_detected(self):
        first = [_gps_point(i, power=200.0, heart_rate=150.0) for i in range(30)]
        second = [_gps_point(i + 30, power=200.0, heart_rate=170.0) for i in range(30)]
        result = detect_aerobic_decoupling(first + second, ftp=250.0)
        assert result["significant"] is True


class TestCalculateAdvancedPowerMetrics:
    def test_no_power_returns_unavailable(self):
        result = calculate_advanced_power_metrics([])
        assert result["available"] is False
        assert result["reason"] == "no_power_data"

    def test_with_power_data_returns_metrics(self):
        points = [_gps_point(i, power=200.0 + (i % 20)) for i in range(60)]
        result = calculate_advanced_power_metrics(points, ftp=250.0)
        assert result["available"] is True
        assert "normalized_power_w" in result
        assert "tss" in result
        assert "power_zones" in result
