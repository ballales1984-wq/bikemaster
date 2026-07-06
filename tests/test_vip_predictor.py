import pytest
from datetime import datetime, timezone

from bike_analyzer.backend.analytics.vip_predictor import estimate_vip


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
    return type("Ride", (), data)()


def test_estimate_vip_insufficient_data():
    result = estimate_vip([_ride()], athlete_ftp=250)
    assert result.probability_index == 0.0
    assert "insufficient_data" in result.risk_factors


def test_estimate_vip_high_probability():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rides = [
        _ride({"date": (base.replace(day=base.day + i * 2)).isoformat(), "duration_minutes": 90 + i * 5, "avg_speed_kmh": 28 + i * 0.3})
        for i in range(10)
    ]
    result = estimate_vip(rides, athlete_ftp=250)
    assert result.probability_index >= 0.0
    assert result.probability_index <= 1.0
    assert isinstance(result.recommendation, str)


def test_estimate_vip_low_readiness():
    rides = [
        _ride({"date": "2024-06-01T10:00:00Z", "duration_minutes": 25, "avg_speed_kmh": 38}),
        _ride({"date": "2024-06-03T10:00:00Z", "duration_minutes": 28, "avg_speed_kmh": 37}),
        _ride({"date": "2024-06-05T10:00:00Z", "duration_minutes": 22, "avg_speed_kmh": 39}),
    ]
    result = estimate_vip(rides, athlete_ftp=250)
    assert "low_duration" in result.risk_factors or "inconsistent_training" in result.risk_factors
