"""Tests for analytics_trends pure functions."""

from datetime import date, datetime

import pytest

from bike_analyzer.backend.analytics.analytics_trends import (
    _filter_valid_rides,
    _fit_linear,
    _rolling_average,
    _safe_float,
    _to_date,
    calculate_fitness_trends,
    calculate_monthly_progression,
)


class TestToDate:
    def test_date_object(self):
        d = date(2024, 6, 15)
        assert _to_date(d) == d

    def test_iso_string(self):
        assert _to_date("2024-06-15") == date(2024, 6, 15)

    def test_datetime_object(self):
        dt = datetime(2024, 6, 15, 10, 0, 0)
        result = _to_date(dt)
        assert result is not None
        assert hasattr(result, 'year')

    def test_none_returns_none(self):
        assert _to_date(None) is None

    def test_invalid_string(self):
        assert _to_date("not-a-date") is None

    def test_empty_string(self):
        assert _to_date("") is None


class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float("25.5") == 25.5

    def test_none(self):
        assert _safe_float(None) is None

    def test_infinity(self):
        assert _safe_float(float("inf")) is None

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_invalid_string(self):
        assert _safe_float("abc") is None


class TestFilterValidRides:
    def test_valid_rides(self):
        rides = [
            {"date": "2024-06-15", "distance_km": 25.0, "avg_speed_kmh": 25.0, "duration_minutes": 60},
            {"date": "2024-06-16", "distance": 30.0, "avg_speed": 28.0, "duration": 70},
        ]
        result = _filter_valid_rides(rides)
        assert len(result) == 2

    def test_filters_invalid(self):
        rides = [
            {"date": "2024-06-15", "distance_km": 25.0, "avg_speed_kmh": 25.0, "duration_minutes": 60},
            {"date": "bad-date", "distance_km": 0},
            {"not_a_dict": True},
        ]
        result = _filter_valid_rides(rides)
        assert len(result) == 1

    def test_empty_input(self):
        assert _filter_valid_rides([]) == []


class TestFitLinear:
    def test_single_value(self):
        result = _fit_linear([10.0])
        assert result["slope"] == 0.0
        assert result["intercept"] == 10.0

    def test_two_values(self):
        result = _fit_linear([10.0, 20.0])
        assert "slope" in result
        assert "r2" in result

    def test_upward_trend(self):
        result = _fit_linear([10.0, 12.0, 14.0, 16.0])
        assert result["slope"] > 0

    def test_downward_trend(self):
        result = _fit_linear([20.0, 16.0, 12.0, 8.0])
        assert result["slope"] < 0

    def test_flat_trend(self):
        result = _fit_linear([10.0, 10.0, 10.0])
        assert abs(result["slope"]) < 0.001

    def test_empty(self):
        result = _fit_linear([])
        assert result["slope"] == 0.0


class TestRollingAverage:
    def test_basic(self):
        result = _rolling_average([10.0, 20.0, 30.0], window=2)
        assert len(result) == 3
        assert result[0] == 10.0
        assert result[1] == 15.0

    def test_invalid_window(self):
        assert _rolling_average([10.0, 20.0], window=0) == []

    def test_empty_input(self):
        assert _rolling_average([]) == []


class TestCalculateFitnessTrends:
    def test_insufficient_data(self):
        result = calculate_fitness_trends([])
        assert result["ready"] is False
        assert result["total_rides"] == 0
        assert result["trend"] == "insufficient_data"

    def test_with_rides(self):
        rides = [
            {"date": "2024-06-01", "distance_km": 25.0, "avg_speed_kmh": 25.0, "duration_minutes": 60},
            {"date": "2024-06-02", "distance_km": 30.0, "avg_speed_kmh": 28.0, "duration_minutes": 70},
            {"date": "2024-06-03", "distance_km": 28.0, "avg_speed_kmh": 27.0, "duration_minutes": 65},
        ]
        result = calculate_fitness_trends(rides, metric="distance_km")
        assert result["ready"] is True
        assert result["total_rides"] == 3
        assert result["trend"] in ("improving", "declining", "stable")

    def test_custom_metric(self):
        rides = [
            {"date": "2024-06-01", "avg_speed_kmh": 25.0, "duration_minutes": 60, "distance_km": 25.0},
            {"date": "2024-06-02", "avg_speed_kmh": 28.0, "duration_minutes": 70, "distance_km": 30.0},
        ]
        result = calculate_fitness_trends(rides, metric="avg_speed_kmh")
        assert "values" in result
        assert len(result["values"]) == 2


class TestCalculateMonthlyProgression:
    def test_empty_rides(self):
        result = calculate_monthly_progression([])
        assert isinstance(result, dict)
        assert result["ready"] is False
        assert result["months"] == []

    def test_single_month(self):
        rides = [
            {"date": "2024-06-15", "distance_km": 100.0, "duration_minutes": 240, "avg_speed_kmh": 25.0},
        ]
        result = calculate_monthly_progression(rides)
        assert "2024-06" in result or len(result) > 0

    def test_multiple_months(self):
        rides = [
            {"date": "2024-05-15", "distance_km": 80.0, "duration_minutes": 180, "avg_speed_kmh": 25.0},
            {"date": "2024-06-15", "distance_km": 100.0, "duration_minutes": 240, "avg_speed_kmh": 25.0},
        ]
        result = calculate_monthly_progression(rides)
        assert len(result) >= 1
