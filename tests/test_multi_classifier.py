import pytest
from datetime import datetime, timezone

from bike_analyzer.backend.analytics.multi_classifier import (
    ClassifiedRide,
    category_distribution,
    classify_rides,
)
from bike_analyzer.backend.models.models import Ride


def _ride(overrides=None):
    data = {
        "id": 1,
        "date": "2024-06-01T10:00:00Z",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "avg_speed_kmh": 25.0,
        "elevation_gain_m": 200.0,
        "calories": 600.0,
    }
    if overrides:
        data.update(overrides)
    return Ride(**data)


def test_classify_endurance_ride():
    rides = [_ride({"duration_minutes": 120, "avg_speed_kmh": 22})]
    results = classify_rides(rides)
    assert "endurance" in results[0].categories


def test_classify_vo2max_ride():
    rides = [_ride({"duration_minutes": 15, "avg_speed_kmh": 38})]
    results = classify_rides(rides)
    assert "vo2max" in results[0].categories


def test_classify_hilly_ride():
    rides = [_ride({"distance_km": 20, "elevation_gain_m": 300})]
    results = classify_rides(rides)
    assert "hilly" in results[0].categories


def test_primary_category_is_first():
    rides = [_ride({"duration_minutes": 120, "avg_speed_kmh": 22})]
    results = classify_rides(rides)
    assert results[0].primary_category == results[0].categories[0]


def test_category_distribution_counts():
    rides = [
        _ride({"duration_minutes": 120, "avg_speed_kmh": 22}),
        _ride({"duration_minutes": 15, "avg_speed_kmh": 38}),
        _ride({"duration_minutes": 60, "avg_speed_kmh": 28}),
    ]
    dist = category_distribution(rides)
    assert isinstance(dist, dict)
    assert sum(dist.values()) >= 3


def test_empty_rides_returns_empty():
    assert classify_rides([]) == []
    assert category_distribution([]) == {}
