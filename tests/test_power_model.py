"""Tests for power_model analytics module."""
from datetime import datetime, timezone

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


class TestNormalizedPower:
    def test_empty_watts(self):
        assert normalized_power([]) == 0.0

    def test_single_watt(self):
        assert normalized_power([250]) == 250

    def test_short_series(self):
        watts = [200, 250, 300]
        assert normalized_power(watts) == sum(watts) / len(watts)

    def test_full_series(self):
        watts = [200] * 60 + [300] * 60
        result = normalized_power(watts)
        assert result > 0

    def test_high_power_values(self):
        watts = [400, 500, 600, 700, 800]
        result = normalized_power(watts)
        assert 500 < result < 800


class TestIntensityFactor:
    def test_normal_calculation(self):
        assert intensity_factor(275, 250) == 1.1
        assert intensity_factor(225, 250) == 0.9
        assert intensity_factor(250, 250) == 1.0

    def test_zero_ftp(self):
        assert intensity_factor(275, 0) == 0.0


class TestVariabilityIndex:
    def test_uniform_power(self):
        assert variability_index(250, 250) == 1.0

    def test_variable_power(self):
        assert variability_index(300, 250) == 1.2

    def test_zero_avg_power(self):
        assert variability_index(250, 0) == 0.0


class TestEfficiencyFactor:
    def test_normal_calculation(self):
        assert efficiency_factor(250, 150) == 1.667

    def test_zero_hr(self):
        assert efficiency_factor(250, 0) == 0.0


class TestTrainingStressScore:
    def test_normal_tss(self):
        assert training_stress_score(275, 1.1, 1.0) == 121.0

    def test_tss_cap(self):
        result = training_stress_score(400, 1.5, 2.0)
        assert result == 500.0

    def test_empty_session(self):
        result = training_stress_score(100, 0.8, 0.0)
        assert result == 0.0


class TestPowerZones:
    def test_no_power_data(self):
        zones = calculate_power_zones([], ftp=250)
        assert zones == {}

    def test_zero_ftp(self):
        points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc), power=250)]
        zones = calculate_power_zones(points, ftp=0)
        assert zones == {}

    def test_full_zones(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc), power=150),
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc), power=200),
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc), power=300),
        ]
        zones = calculate_power_zones(points, ftp=250)
        assert "Z1" in zones
        assert zones["Z1"]["label"] == "Recovery"
        assert zones["Z2"]["label"] == "Endurance"


class TestPowerProfile:
    def test_no_power_data(self):
        profile = calculate_power_profile([])
        assert all(v is None for v in profile.values())

    def test_with_power_points(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 6, 1, 10, i), power=300 + i * 10)
            for i in range(600)
        ]
        profile = calculate_power_profile(points)
        assert profile["5s"] is not None
        assert profile["1min"] is not None
        assert profile["20min"] is not None


class TestEstimateFtp:
    def test_no_20min_data(self):
        assert estimate_ftp_from_20min([]) == 0.0

    def test_with_20min_data(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 6, 1, 10, i), power=300)
            for i in range(1200)
        ]
        ftp = estimate_ftp_from_20min(points)
        assert ftp == 285.0


class TestEstimateCriticalPower:
    def test_no_data(self):
        assert estimate_critical_power([]).get("cp_w", 0) == 0.0

    def test_with_profile_data(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 6, 1, 10, i), power=300)
            for i in range(600)
        ]
        result = estimate_critical_power(points)
        assert result["cp_w"] >= 100
        assert result["w_prime_j"] >= 5000


class TestAerobicDecoupling:
    def test_insufficient_points(self):
        points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc)) for _ in range(10)]
        result = detect_aerobic_decoupling(points)
        assert result["significant"] is False

    def test_missing_power_or_hr(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc), power=250),
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(timezone.utc), power=250),
        ]
        result = detect_aerobic_decoupling(points, ftp=250)
        assert result["significant"] is False


class TestAdvancedPowerMetrics:
    def test_no_power_data(self):
        result = calculate_advanced_power_metrics([])
        assert result["available"] is False

    def test_full_metrics(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 6, 1, 10, i), power=250, heart_rate=150)
            for i in range(3600)
        ]
        result = calculate_advanced_power_metrics(points, ftp=250)
        assert result["available"] is True
        assert "avg_power_w" in result
        assert "normalized_power_w" in result
        assert "tss" in result
        assert "power_zones" in result
        assert "power_profile" in result
