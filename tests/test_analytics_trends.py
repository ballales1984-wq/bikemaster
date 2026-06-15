"""Tests for analytics_trends module."""
import pytest
from datetime import date, datetime
from bike_analyzer.backend.analytics.analytics_trends import (
    _to_date,
    _safe_float,
    _filter_valid_rides,
    _duration_hours,
    _fit_linear,
    _rolling_average,
    calculate_fitness_trends,
    calculate_monthly_progression,
    calculate_period_comparison,
    calculate_training_volume_projection,
    get_ride_metrics,
)


def test_to_date_from_date():
    assert _to_date(date(2024, 6, 15)) == date(2024, 6, 15)


def test_to_date_from_datetime():
    assert _to_date(datetime(2024, 6, 15, 10, 30)).date() == date(2024, 6, 15)


def test_to_date_from_iso_string():
    assert _to_date("2024-06-15") == date(2024, 6, 15)


def test_to_date_from_iso_string_with_time():
    assert _to_date("2024-06-15T10:30:00") == date(2024, 6, 15)


def test_to_date_invalid_string():
    assert _to_date("invalid") is None


def test_to_date_invalid_type():
    assert _to_date(123) is None


def test_safe_float_valid():
    assert _safe_float(10.5) == 10.5


def test_safe_float_none():
    assert _safe_float(None) is None


def test_safe_float_string():
    assert _safe_float("42.5") == 42.5


def test_safe_float_invalid():
    assert _safe_float("abc") is None


def test_safe_float_inf():
    import math
    assert _safe_float(float("inf")) is None


def test_filter_valid_rides_empty():
    assert _filter_valid_rides([]) == []


def test_filter_valid_rides_non_dict():
    assert _filter_valid_rides(["not a dict"]) == []


def test_filter_valid_rides_missing_fields():
    rides = [{"date": "2024-06-15"}]
    assert _filter_valid_rides(rides) == []


def test_filter_valid_rides_valid():
    rides = [
        {"date": "2024-06-15", "distance_km": 20.0, "avg_speed_kmh": 25.0, "duration_minutes": 48.0},
    ]
    result = _filter_valid_rides(rides)
    assert len(result) == 1


def test_duration_hours():
    assert _duration_hours({"duration_minutes": 120}) == 2.0


def test_duration_hours_missing():
    assert _duration_hours({}) == 0.0


def test_fit_linear_empty():
    result = _fit_linear([])
    assert result["slope"] == 0.0
    assert result["r2"] == 0.0


def test_fit_linear_single_value():
    result = _fit_linear([5.0])
    assert result["slope"] == 0.0
    assert result["intercept"] == 5.0


def test_fit_linear_two_values():
    result = _fit_linear([1.0, 3.0])
    assert result["slope"] == 2.0


def test_fit_linear_three_values():
    result = _fit_linear([1.0, 2.0, 3.0])
    assert result["slope"] == 1.0
    assert result["r2"] == 1.0


def test_rolling_average_empty():
    assert _rolling_average([]) == []


def test_rolling_average_zero_window():
    assert _rolling_average([1, 2, 3], window=0) == []


def test_rolling_average_basic():
    result = _rolling_average([1.0, 2.0, 3.0], window=2)
    assert result[0] == 1.0
    assert result[-1] == 2.5


def test_calculate_fitness_trends_empty():
    result = calculate_fitness_trends([])
    assert result["ready"] is False
    assert result["trend"] == "insufficient_data"


def test_calculate_fitness_trends_improving():
    rides = [
        {"date": "2024-06-01", "distance_km": 10.0, "avg_speed_kmh": 20.0, "duration_minutes": 30.0},
        {"date": "2024-06-08", "distance_km": 15.0, "avg_speed_kmh": 22.0, "duration_minutes": 40.0},
        {"date": "2024-06-15", "distance_km": 20.0, "avg_speed_kmh": 25.0, "duration_minutes": 48.0},
    ]
    result = calculate_fitness_trends(rides)
    assert result["ready"] is True
    assert result["trend"] == "improving"


def test_calculate_fitness_trends_declining():
    rides = [
        {"date": "2024-06-01", "distance_km": 30.0, "avg_speed_kmh": 30.0, "duration_minutes": 60.0},
        {"date": "2024-06-08", "distance_km": 25.0, "avg_speed_kmh": 27.0, "duration_minutes": 55.0},
        {"date": "2024-06-15", "distance_km": 20.0, "avg_speed_kmh": 22.0, "duration_minutes": 55.0},
    ]
    result = calculate_fitness_trends(rides)
    assert result["ready"] is True
    assert result["trend"] == "declining"


def test_calculate_monthly_progression_empty():
    result = calculate_monthly_progression([])
    assert result["ready"] is False
    assert result["months"] == []


def test_calculate_monthly_progression_single_month():
    rides = [
        {"date": "2024-06-01", "distance_km": 20.0, "avg_speed_kmh": 25.0, "duration_minutes": 48.0, "calories": 500.0},
        {"date": "2024-06-15", "distance_km": 25.0, "avg_speed_kmh": 27.0, "duration_minutes": 55.0, "calories": 600.0},
    ]
    result = calculate_monthly_progression(rides)
    assert result["ready"] is True
    assert len(result["months"]) == 1
    assert result["total_distance_km"] == [45.0]


def test_calculate_period_comparison_empty():
    result = calculate_period_comparison([])
    assert result["ready"] is False


def test_calculate_period_comparison_zero_period():
    result = calculate_period_comparison([], period_days=0)
    assert result["ready"] is False


def test_calculate_period_comparison_with_data():
    rides = [
        {"date": "2024-06-01", "distance_km": 20.0, "avg_speed_kmh": 25.0, "duration_minutes": 48.0},
        {"date": "2024-06-08", "distance_km": 25.0, "avg_speed_kmh": 27.0, "duration_minutes": 55.0},
        {"date": "2024-06-15", "distance_km": 30.0, "avg_speed_kmh": 28.0, "duration_minutes": 65.0},
    ]
    result = calculate_period_comparison(rides)
    assert result["ready"] is True
    assert result["recent_rides"] >= 0


def test_calculate_training_volume_projection_empty():
    result = calculate_training_volume_projection([])
    assert result["ready"] is False
    assert result["confidence"] == "none"


def test_calculate_training_volume_projection_low():
    rides = [{"date": "2024-06-15", "distance_km": 20.0, "avg_speed_kmh": 25.0, "duration_minutes": 48.0}]
    result = calculate_training_volume_projection(rides)
    assert result["ready"] is True
    assert result["confidence"] == "low"


def test_calculate_training_volume_projection_medium():
    rides = [
        {"date": "2024-06-01", "distance_km": 20.0, "avg_speed_kmh": 25.0, "duration_minutes": 48.0},
        {"date": "2024-06-08", "distance_km": 25.0, "avg_speed_kmh": 27.0, "duration_minutes": 55.0},
        {"date": "2024-06-15", "distance_km": 30.0, "avg_speed_kmh": 28.0, "duration_minutes": 65.0},
    ]
    result = calculate_training_volume_projection(rides)
    assert result["ready"] is True


def test_get_ride_metrics_empty():
    result = get_ride_metrics({})
    assert result == {}


def test_get_ride_metrics_partial():
    result = get_ride_metrics({"distance_km": 20.0, "calories": 500.0})
    assert "distance_km" in result
    assert "calories" in result


def test_get_ride_metrics_all_fields():
    result = get_ride_metrics({
        "distance_km": 20.0,
        "duration_minutes": 48.0,
        "avg_speed_kmh": 25.0,
        "calories": 500.0,
    })
    assert len(result) == 4