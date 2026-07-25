"""Tests for zone_analysis module."""

from __future__ import annotations

import pytest

from bike_analyzer.backend.analytics.zone_analysis import (
    DEFAULT_FTP,
    DEFAULT_MAX_HR,
    HR_ZONE_PCT,
    _as_float,
    _hr_distribution,
    _to_gps_points,
    calculate_zone_distributions,
)


class TestAsFloat:
    def test_none_returns_none(self):
        assert _as_float(None) is None

    def test_valid_int(self):
        assert _as_float(42) == 42.0

    def test_valid_float(self):
        assert _as_float(3.14) == 3.14

    def test_valid_string(self):
        assert _as_float("42.5") == 42.5

    def test_invalid_string(self):
        assert _as_float("abc") is None

    def test_zero(self):
        assert _as_float(0) == 0.0


class TestToGpsPoints:
    def test_empty_list(self):
        assert _to_gps_points([]) == []

    def test_none_input(self):
        assert _to_gps_points(None) == []

    def test_valid_dicts(self):
        data = [
            {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00Z", "power": 200.0, "heart_rate": 150.0},
            {"lat": 45.1, "lon": 7.1, "timestamp": "2024-06-15T10:01:00Z", "power": 210.0, "heart_rate": 155.0},
        ]
        points = _to_gps_points(data)
        assert len(points) == 2
        assert points[0].lat == 45.0
        assert points[0].power == 200.0
        assert points[0].heart_rate == 150.0

    def test_non_dict_skipped(self):
        data = [{"lat": 45.0, "lon": 7.0, "timestamp": ""}, "bad", None, {"lat": 45.1, "lon": 7.1, "timestamp": ""}]
        points = _to_gps_points(data)
        assert len(points) == 2

    def test_missing_fields_defaults(self):
        data = [{"lat": 45.0, "lon": 7.0, "timestamp": ""}]
        points = _to_gps_points(data)
        assert len(points) == 1
        assert points[0].power is None
        assert points[0].heart_rate is None


class TestHrDistribution:
    def test_empty_samples_returns_zones_with_zero_counts(self):
        zones = _hr_distribution([], DEFAULT_MAX_HR)
        assert len(zones) == 5
        assert all(z["count"] == 0 for z in zones)
        assert all(z["pct_time"] == 0.0 for z in zones)

    def test_samples_distributed_across_zones(self):
        hr_samples = [120, 140, 160, 170, 185]
        zones = _hr_distribution(hr_samples, DEFAULT_MAX_HR)
        total_counts = sum(z["count"] for z in zones)
        assert total_counts == 5

    def test_zone_labels_present(self):
        zones = _hr_distribution([140], DEFAULT_MAX_HR)
        labels = {z["label"] for z in zones}
        assert "Recovery" in labels
        assert "Endurance" in labels
        assert "Tempo" in labels
        assert "Threshold" in labels
        assert "VO2max" in labels

    def test_zone_boundaries(self):
        zones = _hr_distribution([], DEFAULT_MAX_HR)
        for z in zones:
            assert "lower_bpm" in z
            assert "upper_bpm" in z
            assert z["lower_bpm"] < z["upper_bpm"]

    def test_z5_inclusive_of_max_hr(self):
        hr_samples = [190.0]
        zones = _hr_distribution(hr_samples, 190.0)
        z5 = next(z for z in zones if z["zone"] == "Z5")
        assert z5["count"] == 1


class TestCalculateZoneDistributions:
    def test_empty_rides(self):
        result = calculate_zone_distributions([])
        assert result["power"]["available"] is False
        assert result["hr"]["available"] is False
        assert result["rides_with_power"] == 0
        assert result["rides_with_hr"] == 0

    def test_rides_without_gps(self):
        rides = [{"id": 1, "gps_points": None}, {"id": 2, "gps_points": []}]
        result = calculate_zone_distributions(rides)
        assert result["power"]["total_samples"] == 0
        assert result["hr"]["total_samples"] == 0

    def test_hr_distribution_from_gps(self):
        rides = [
            {
                "id": 1,
                "gps_points": [
                    {"lat": 45.0, "lon": 7.0, "timestamp": "", "heart_rate": 140.0},
                    {"lat": 45.1, "lon": 7.1, "timestamp": "", "heart_rate": 160.0},
                ],
            }
        ]
        result = calculate_zone_distributions(rides, max_hr=190)
        assert result["hr"]["available"] is True
        assert result["hr"]["total_samples"] == 2
        assert result["rides_with_hr"] == 1
        total_pct = sum(z["pct_time"] for z in result["hr"]["zones"])
        assert abs(total_pct - 100.0) < 0.1

    def test_power_distribution_from_gps(self):
        rides = [
            {
                "id": 1,
                "gps_points": [
                    {"lat": 45.0, "lon": 7.0, "timestamp": "", "power": 200.0},
                    {"lat": 45.1, "lon": 7.1, "timestamp": "", "power": 220.0},
                ],
            }
        ]
        result = calculate_zone_distributions(rides, ftp_watts=250.0)
        assert result["power"]["available"] is True
        assert result["power"]["total_samples"] == 2
        assert result["rides_with_power"] == 1

    def test_mixed_power_and_hr(self):
        rides = [
            {
                "id": 1,
                "gps_points": [
                    {"lat": 45.0, "lon": 7.0, "timestamp": "", "power": 200.0, "heart_rate": 140.0},
                ],
            },
            {
                "id": 2,
                "gps_points": [
                    {"lat": 45.2, "lon": 7.2, "timestamp": "", "power": 210.0, "heart_rate": 155.0},
                ],
            },
        ]
        result = calculate_zone_distributions(rides, ftp_watts=250.0, max_hr=190)
        assert result["power"]["available"] is True
        assert result["hr"]["available"] is True
        assert result["rides_with_power"] == 2
        assert result["rides_with_hr"] == 2

    def test_default_ftp_and_max_hr(self):
        rides = [
            {
                "id": 1,
                "gps_points": [
                    {"lat": 45.0, "lon": 7.0, "timestamp": "", "power": 200.0},
                ],
            }
        ]
        result = calculate_zone_distributions(rides)
        assert result["ftp_watts"] == DEFAULT_FTP
        assert result["max_hr"] == DEFAULT_MAX_HR

    def test_custom_ftp_and_max_hr(self):
        rides = [
            {
                "id": 1,
                "gps_points": [
                    {"lat": 45.0, "lon": 7.0, "timestamp": "", "power": 200.0, "heart_rate": 140.0},
                ],
            }
        ]
        result = calculate_zone_distributions(rides, ftp_watts=300.0, max_hr=185.0)
        assert result["ftp_watts"] == 300.0
        assert result["max_hr"] == 185.0

    def test_hr_zone_reference_present(self):
        rides = []
        result = calculate_zone_distributions(rides, max_hr=185.0)
        assert "hr_zone_reference" in result
        assert len(result["hr_zone_reference"]) == 5

    def test_partial_gps_points_skipped(self):
        rides = [
            {
                "id": 1,
                "gps_points": [
                    {"lat": 45.0, "lon": 7.0, "timestamp": "", "power": None, "heart_rate": None},
                    {"lat": 45.1, "lon": 7.1, "timestamp": "", "power": 200.0, "heart_rate": 150.0},
                ],
            }
        ]
        result = calculate_zone_distributions(rides, ftp_watts=250.0, max_hr=190)
        assert result["power"]["total_samples"] == 2
        assert result["hr"]["total_samples"] == 1
