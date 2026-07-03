"""Tests for analytics/analytics_trends.py — trend analysis and projections."""

from __future__ import annotations

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
    calculate_period_comparison,
    calculate_training_volume_projection,
    get_ride_metrics,
)


def make_ride(date_str: str, distance_km: float = 30.0, avg_speed_kmh: float = 25.0,
              duration_minutes: float = 72.0, calories: float | None = 800.0, **kwargs) -> dict:
    ride = {
        "date": date_str,
        "distance_km": distance_km,
        "avg_speed_kmh": avg_speed_kmh,
        "duration_minutes": duration_minutes,
        "calories": calories,
    }
    ride.update(kwargs)
    return ride


class TestToDate:
    def test_date_object(self):
        d = date(2024, 6, 15)
        assert _to_date(d) == d

    def test_datetime_object(self):
        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = _to_date(dt)
        assert result == date(2024, 6, 15) or result == dt

    def test_iso_string(self):
        assert _to_date("2024-06-15T10:30:00") == date(2024, 6, 15)

    def test_date_only_string(self):
        assert _to_date("2024-06-15") == date(2024, 6, 15)

    def test_invalid_string(self):
        assert _to_date("not-a-date") is None

    def test_none_input(self):
        assert _to_date(None) is None

    def test_empty_string(self):
        assert _to_date("") is None


class TestSafeFloat:
    def test_valid_int(self):
        assert _safe_float(42) == 42.0

    def test_valid_float(self):
        assert _safe_float(3.14) == 3.14

    def test_none(self):
        assert _safe_float(None) is None

    def test_string_number(self):
        assert _safe_float("25.5") == 25.5

    def test_invalid_string(self):
        assert _safe_float("abc") is None

    def test_infinity(self):
        assert _safe_float(float("inf")) is None

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_zero(self):
        assert _safe_float(0) == 0.0


class TestFilterValidRides:
    def test_empty_input(self):
        assert _filter_valid_rides([]) == []

    def test_valid_ride(self):
        rides = [make_ride("2024-06-15")]
        assert len(_filter_valid_rides(rides)) == 1

    def test_missing_date(self):
        rides = [{"distance_km": 30.0, "avg_speed_kmh": 25.0, "duration_minutes": 72.0}]
        assert _filter_valid_rides(rides) == []

    def test_zero_distance(self):
        rides = [make_ride("2024-06-15", distance_km=0)]
        assert _filter_valid_rides(rides) == []

    def test_zero_speed(self):
        rides = [make_ride("2024-06-15", avg_speed_kmh=0)]
        assert _filter_valid_rides(rides) == []

    def test_zero_duration(self):
        rides = [make_ride("2024-06-15", duration_minutes=0)]
        assert _filter_valid_rides(rides) == []

    def test_non_dict_ignored(self):
        rides = ["not a dict", make_ride("2024-06-15")]
        assert len(_filter_valid_rides(rides)) == 1

    def test_alternative_field_names(self):
        rides = [{"date": "2024-06-15", "distance": 30.0, "avg_speed": 25.0, "duration": 72.0}]
        assert len(_filter_valid_rides(rides)) == 1


class TestFitLinear:
    def test_single_point(self):
        result = _fit_linear([5.0])
        assert result["slope"] == 0.0
        assert result["intercept"] == 5.0

    def test_perfect_line(self):
        result = _fit_linear([1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(result["slope"] - 1.0) < 1e-6
        assert abs(result["r2"] - 1.0) < 1e-6

    def test_flat_line(self):
        result = _fit_linear([5.0, 5.0, 5.0, 5.0])
        assert abs(result["slope"]) < 1e-6
        assert abs(result["r2"]) < 1e-6

    def test_empty_input(self):
        result = _fit_linear([])
        assert result["intercept"] == 0.0


class TestRollingAverage:
    def test_empty_input(self):
        assert _rolling_average([]) == []

    def test_single_value(self):
        assert _rolling_average([5.0]) == [5.0]

    def test_window_larger_than_data(self):
        result = _rolling_average([1.0, 2.0, 3.0], window=10)
        assert len(result) == 3
        assert abs(result[0] - 1.0) < 1e-6

    def test_window_equals_data(self):
        result = _rolling_average([1.0, 2.0, 3.0], window=3)
        assert abs(result[-1] - 2.0) < 1e-6

    def test_window_one(self):
        result = _rolling_average([1.0, 2.0, 3.0], window=1)
        assert result == [1.0, 2.0, 3.0]

    def test_zero_window(self):
        assert _rolling_average([1.0, 2.0], window=0) == []


class TestCalculateFitnessTrends:
    def test_empty_rides(self):
        result = calculate_fitness_trends([])
        assert result["ready"] is False
        assert result["trend"] == "insufficient_data"

    def test_no_valid_rides(self):
        result = calculate_fitness_trends([make_ride("2024-06-15", distance_km=0)])
        assert result["ready"] is False

    def test_improving_trend(self):
        rides = [make_ride(f"2024-06-{i:02d}", distance_km=20.0 + i * 5.0, avg_speed_kmh=22.0 + i * 0.5) for i in range(1, 10)]
        result = calculate_fitness_trends(rides, metric="distance_km")
        assert result["ready"] is True
        assert result["trend"] == "improving"

    def test_declining_trend(self):
        rides = [make_ride(f"2024-06-{i:02d}", distance_km=50.0 - i * 3.0, avg_speed_kmh=28.0 - i * 0.5) for i in range(1, 10)]
        result = calculate_fitness_trends(rides, metric="distance_km")
        assert result["trend"] == "declining"

    def test_stable_trend(self):
        rides = [make_ride(f"2024-06-{i:02d}", distance_km=30.0, avg_speed_kmh=25.0) for i in range(1, 10)]
        result = calculate_fitness_trends(rides, metric="distance_km")
        assert result["trend"] == "stable"

    def test_returns_expected_keys(self):
        rides = [make_ride(f"2024-06-{i:02d}", distance_km=30.0 + i * 2) for i in range(1, 10)]
        result = calculate_fitness_trends(rides)
        assert "slope" in result
        assert "r2" in result
        assert "rolling_avg" in result
        assert "dates" in result
        assert "values" in result
        assert "mean" in result
        assert "std" in result

    def test_rolling_average_length(self):
        rides = [make_ride(f"2024-06-{i:02d}", distance_km=20.0 + i * 2) for i in range(1, 10)]
        result = calculate_fitness_trends(rides, metric="distance_km", window=7)
        assert len(result["rolling_avg"]) == len(result["values"])

    def test_dates_sorted(self):
        rides = [
            make_ride("2024-06-20", distance_km=30.0),
            make_ride("2024-06-01", distance_km=25.0),
            make_ride("2024-06-10", distance_km=28.0),
        ]
        result = calculate_fitness_trends(rides, metric="distance_km")
        assert result["dates"] == sorted(result["dates"])

    def test_different_metric(self):
        rides = [make_ride(f"2024-06-{i:02d}", avg_speed_kmh=22.0 + i * 0.5) for i in range(1, 10)]
        result = calculate_fitness_trends(rides, metric="avg_speed_kmh")
        assert result["metric"] == "avg_speed_kmh"
        assert result["trend"] == "improving"


class TestCalculateMonthlyProgression:
    def test_empty_rides(self):
        result = calculate_monthly_progression([])
        assert result["ready"] is False
        assert result["months"] == []

    def test_single_month(self):
        rides = [make_ride("2024-06-15", distance_km=30.0, avg_speed_kmh=25.0, duration_minutes=72.0, calories=800.0)]
        result = calculate_monthly_progression(rides)
        assert result["ready"] is True
        assert len(result["months"]) == 1
        assert result["months"][0] == "2024-06"

    def test_multiple_months(self):
        rides = [
            make_ride("2024-05-15", distance_km=30.0, calories=800.0),
            make_ride("2024-06-15", distance_km=40.0, calories=900.0),
            make_ride("2024-06-20", distance_km=35.0, calories=850.0),
        ]
        result = calculate_monthly_progression(rides)
        assert len(result["months"]) == 2
        assert result["months"][0] == "2024-05"
        assert result["months"][1] == "2024-06"

    def test_distance_aggregation(self):
        rides = [
            make_ride("2024-06-01", distance_km=20.0),
            make_ride("2024-06-15", distance_km=30.0),
        ]
        result = calculate_monthly_progression(rides)
        assert result["total_distance_km"][-1] == pytest.approx(50.0)

    def test_ride_count(self):
        rides = [
            make_ride("2024-06-01", distance_km=20.0),
            make_ride("2024-06-15", distance_km=30.0),
            make_ride("2024-06-20", distance_km=25.0),
        ]
        result = calculate_monthly_progression(rides)
        assert result["ride_count"][-1] == 3

    def test_calories_optional(self):
        rides = [make_ride("2024-06-15", distance_km=30.0, calories=None)]
        result = calculate_monthly_progression(rides)
        assert result["ready"] is True
        assert result["avg_calories"][-1] == 0.0

    def test_avg_speed_calculation(self):
        rides = [
            make_ride("2024-06-01", distance_km=30.0, avg_speed_kmh=20.0),
            make_ride("2024-06-15", distance_km=30.0, avg_speed_kmh=30.0),
        ]
        result = calculate_monthly_progression(rides)
        assert result["avg_speed_kmh"][-1] == pytest.approx(25.0)

    def test_duration_in_hours(self):
        rides = [make_ride("2024-06-15", duration_minutes=120.0)]
        result = calculate_monthly_progression(rides)
        assert result["total_duration_hours"][-1] == pytest.approx(2.0)


class TestCalculatePeriodComparison:
    def test_empty_rides(self):
        result = calculate_period_comparison([])
        assert result["ready"] is False

    def test_single_ride(self):
        rides = [make_ride("2024-06-15", distance_km=30.0, avg_speed_kmh=25.0)]
        result = calculate_period_comparison(rides, period_days=7)
        assert result["recent_rides"] == 1
        assert result["previous_rides"] == 0

    def test_two_periods(self):
        base = "2024-06-01"
        rides = [
            make_ride(base, distance_km=30.0, avg_speed_kmh=25.0),
            make_ride("2024-06-05", distance_km=35.0, avg_speed_kmh=26.0),
            make_ride("2024-06-08", distance_km=40.0, avg_speed_kmh=27.0),
            make_ride("2024-06-12", distance_km=45.0, avg_speed_kmh=28.0),
        ]
        result = calculate_period_comparison(rides, period_days=7)
        assert result["ready"] is True
        assert result["recent_rides"] + result["previous_rides"] == 4

    def test_distance_change(self):
        base = "2024-06-01"
        rides = [
            make_ride(base, distance_km=30.0, avg_speed_kmh=25.0),
            make_ride("2024-06-10", distance_km=60.0, avg_speed_kmh=26.0),
        ]
        result = calculate_period_comparison(rides, period_days=7)
        assert result["distance_change_pct"] > 0

    def test_zero_previous_distance(self):
        rides = [make_ride("2024-06-15", distance_km=30.0, avg_speed_kmh=25.0)]
        result = calculate_period_comparison(rides, period_days=30)
        assert result["distance_change_pct"] == 0.0


class TestCalculateTrainingVolumeProjection:
    def test_empty_rides(self):
        result = calculate_training_volume_projection([])
        assert result["ready"] is False
        assert result["confidence"] == "none"

    def test_projection_returns_values(self):
        rides = [make_ride(f"2024-06-{i:02d}", distance_km=30.0 + i * 2) for i in range(1, 15)]
        result = calculate_training_volume_projection(rides, target_days=30)
        assert result["ready"] is True
        assert result["projected_distance_km"] > 0

    def test_confidence_high(self):
        rides = [make_ride(f"2024-05-{i:02d}", distance_km=30.0) for i in range(1, 21)]
        result = calculate_training_volume_projection(rides, target_days=30)
        assert result["confidence"] == "high"

    def test_confidence_low(self):
        rides = [make_ride("2024-06-15", distance_km=30.0)]
        result = calculate_training_volume_projection(rides, target_days=30)
        assert result["confidence"] == "low"

    def test_zero_period(self):
        rides = [make_ride("2024-06-15", distance_km=30.0)]
        result = calculate_training_volume_projection(rides, target_days=0)
        assert result["projected_distance_km"] == 0.0


class TestGetRideMetrics:
    def test_basic_metrics(self):
        ride = {
            "distance_km": 50.0,
            "duration_minutes": 120.0,
            "avg_speed_kmh": 25.0,
            "weight_kg": 70.0,
            "calories": 800.0,
            "heart_rate_avg": 150.0,
            "elevation_gain_m": 500.0,
        }
        metrics = get_ride_metrics(ride)
        assert metrics["distance_km"] == 50.0
        assert metrics["avg_speed_kmh"] == 25.0

    def test_skips_non_numeric(self):
        ride = {"distance_km": 50.0, "title": "Morning Ride", "notes": "Great session"}
        metrics = get_ride_metrics(ride)
        assert "title" not in metrics
        assert "notes" not in metrics

    def test_null_values_skipped(self):
        ride = {"distance_km": 50.0, "avg_speed_kmh": None, "duration_minutes": 120.0}
        metrics = get_ride_metrics(ride)
        assert "avg_speed_kmh" not in metrics
        assert "distance_km" in metrics

    def test_string_number_value(self):
        ride = {"distance_km": "40.0", "avg_speed_kmh": "25.0"}
        metrics = get_ride_metrics(ride)
        assert metrics["distance_km"] == 40.0
