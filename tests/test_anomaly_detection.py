
from bike_analyzer.backend.analytics.anomaly_detection import (
    detect_ride_anomalies,
    summarize_anomalies,
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


def test_no_anomalies_uniform_rides():
    rides = [_ride({"id": i, "distance_km": 25.0 + i * 0.1}) for i in range(10)]
    reports = detect_ride_anomalies(rides)
    assert len(reports) == 10
    assert all(r.anomalies == [] for r in reports)


def test_flags_extreme_distance_outlier():
    rides = [_ride({"id": i, "distance_km": 25.0 + i}) for i in range(9)]
    rides.append(_ride({"id": 9, "distance_km": 500.0}))
    reports = detect_ride_anomalies(rides, z_threshold=2.0)
    outlier = next(r for r in reports if r.ride_id == 9)
    assert any(a.metric == "distance_km" for a in outlier.anomalies)
    assert outlier.risk_level != "none"


def test_flags_zero_duration_anomaly():
    rides = [_ride({"id": i, "duration_minutes": 60.0 + i * 5}) for i in range(9)]
    rides.append(_ride({"id": 9, "duration_minutes": 0.0}))
    reports = detect_ride_anomalies(rides, z_threshold=2.0)
    outlier = next(r for r in reports if r.ride_id == 9)
    assert any(a.metric == "duration_minutes" for a in outlier.anomalies)


def test_returns_empty_for_few_rides():
    assert detect_ride_anomalies([_ride(), _ride()]) == []


def test_returns_empty_for_empty_input():
    assert detect_ride_anomalies([]) == []


def test_summarize_anomalies_aggregates():
    rides = [_ride({"id": i, "distance_km": 25.0, "duration_minutes": 60.0, "avg_speed_kmh": 25.0}) for i in range(10)]
    rides.append(_ride({"id": 10, "distance_km": 500.0}))
    rides.append(_ride({"id": 11, "duration_minutes": 0.0}))
    reports = detect_ride_anomalies(rides, z_threshold=2.0)
    summary = summarize_anomalies(reports)
    assert summary["total_rides"] == 12
    assert summary["anomalous_rides"] > 0
    assert len(summary["flagged_rides"]) > 0


def test_high_risk_multiple_anomalies():
    base_rides = [_ride({"id": i, "distance_km": 25.0 + i, "duration_minutes": 60.0 + i * 5}) for i in range(10)]
    outlier = _ride({"id": 99, "distance_km": 500.0, "duration_minutes": 0.0, "avg_speed_kmh": 100.0})
    rides = base_rides + [outlier]
    reports = detect_ride_anomalies(rides, z_threshold=2.0)
    flagged = next(r for r in reports if r.ride_id == 99)
    assert flagged.risk_level == "high"
