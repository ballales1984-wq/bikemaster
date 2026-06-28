"""Tests for power_model module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bike_analyzer.backend.analytics.power_model import (
    POWER_ZONES_COGGAN,
    calculate_power_zones,
    efficiency_factor,
    intensity_factor,
    normalized_power,
    training_stress_score,
    variability_index,
)
from bike_analyzer.backend.models.models import GPSPoint


def _point(power=None, heart_rate=None, timestamp=None, **kwargs):
    ts = timestamp or datetime(2024, 1, 1, 8, 0, 0, tzinfo=UTC)
    return GPSPoint(lat=45.0, lon=9.0, timestamp=ts, power=power, heart_rate=heart_rate)


class TestNormalizedPower:
    def test_empty_list(self):
        assert normalized_power([]) == 0.0

    def test_single_value(self):
        assert normalized_power([200.0]) == 200.0

    def test_constant_power(self):
        result = normalized_power([200.0] * 100, window_size=30)
        assert 195.0 <= result <= 205.0

    def test_variable_power(self):
        watts = [100.0] * 15 + [300.0] * 15 + [100.0] * 15 + [300.0] * 15
        result = normalized_power(watts, window_size=30)
        assert result >= 200.0

    def test_too_few_values(self):
        result = normalized_power([150.0, 160.0], window_size=30)
        assert result == 155.0


class TestIntensityFactor:
    def test_basic(self):
        assert intensity_factor(250.0, 250.0) == 1.0

    def test_below_ftp(self):
        assert intensity_factor(200.0, 250.0) == 0.8

    def test_zero_ftp(self):
        assert intensity_factor(250.0, 0.0) == 0.0


class TestVariabilityIndex:
    def test_basic(self):
        assert variability_index(250.0, 200.0) == 1.25

    def test_zero_avg(self):
        assert variability_index(250.0, 0.0) == 0.0


class TestEfficiencyFactor:
    def test_basic(self):
        assert efficiency_factor(250.0, 150.0) == round(250.0 / 150.0, 3)

    def test_zero_hr(self):
        assert efficiency_factor(250.0, 0.0) == 0.0


class TestTrainingStressScore:
    def test_basic(self):
        tss = training_stress_score(250.0, 0.75, 1.0)
        assert tss > 0

    def test_capped_at_500(self):
        tss = training_stress_score(500.0, 1.5, 5.0)
        assert tss <= 500.0

    def test_zero_duration(self):
        assert training_stress_score(250.0, 0.5, 0.0) == 0.0


class TestCalculatePowerZones:
    def test_basic_zones(self):
        points = [_point(power=200.0) for _ in range(35)]
        zones = calculate_power_zones(points, ftp=250.0)
        assert "Z1" in zones
        assert "Z2" in zones
        assert zones["Z1"]["count"] >= 0

    def test_no_power_data(self):
        points = [_point(power=None) for _ in range(10)]
        zones = calculate_power_zones(points, ftp=250.0)
        assert zones == {}

    def test_zero_ftp(self):
        points = [_point(power=200.0) for _ in range(10)]
        zones = calculate_power_zones(points, ftp=0.0)
        assert zones == {}

    def test_zones_have_expected_keys(self):
        points = [_point(power=200.0) for _ in range(35)]
        zones = calculate_power_zones(points, ftp=250.0)
        for name, data in zones.items():
            assert "label" in data
            assert "count" in data
            assert "pct_time" in data


class TestCalculatePowerProfile:
    def test_empty(self):
        from bike_analyzer.backend.analytics.power_model import calculate_power_profile
        result = calculate_power_profile([])
        assert all(v is None for v in result.values())

    def test_with_power_data(self):
        from bike_analyzer.backend.analytics.power_model import calculate_power_profile
        base = datetime(2024, 1, 1, 8, 0, 0, tzinfo=UTC)
        points = [
            _point(power=500.0, timestamp=base),
            _point(power=300.0, timestamp=base),
            _point(power=250.0, timestamp=base),
        ]
        result = calculate_power_profile(points)
        assert "20min" in result
        assert "5min" in result


class TestEstimateFtp:
    def test_no_data(self):
        from bike_analyzer.backend.analytics.power_model import estimate_ftp_from_20min
        result = estimate_ftp_from_20min([])
        assert result == 0.0

    def test_with_20min_power(self):
        from bike_analyzer.backend.analytics.power_model import estimate_ftp_from_20min
        base = datetime(2024, 1, 1, 8, 0, 0, tzinfo=UTC)
        points = [_point(power=280.0, timestamp=base.replace(minute=i)) for i in range(30)]
        result = estimate_ftp_from_20min(points)
        assert result >= 0


class TestEstimateCriticalPower:
    def test_no_data(self):
        from bike_analyzer.backend.analytics.power_model import estimate_critical_power
        result = estimate_critical_power([])
        assert result["cp_w"] == 0.0
        assert result["w_prime_j"] == 0.0

    def test_with_data(self):
        from bike_analyzer.backend.analytics.power_model import estimate_critical_power
        base = datetime(2024, 1, 1, 8, 0, 0, tzinfo=UTC)
        points = [_point(power=300.0, timestamp=base) for _ in range(15)]
        result = estimate_critical_power(points)
        assert "cp_w" in result
        assert "w_prime_j" in result
