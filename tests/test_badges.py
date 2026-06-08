"""Tests for badge/medal system."""
import pytest
from bike_analyzer.backend.analytics.badges import calculate_badges, calculate_streak, get_heatmap_points


def test_calculate_badges_no_rides():
    badges = calculate_badges(1, [])
    assert any(b["id"] == 1 for b in badges)
    first = next(b for b in badges if b["id"] == 1)
    assert first["achieved"] is False


def test_calculate_badges_first_ride():
    ride = {"id": 1, "distance_km": 25.0, "duration_minutes": 90.0, "avg_speed_kmh": 20.0, "elevation_gain_m": 200.0, "date": "2024-01-15"}
    badges = calculate_badges(1, [ride])
    first = next(b for b in badges if b["id"] == 1)
    assert first["achieved"] is True
    assert first["progress"] == 100.0


def test_calculate_badges_distance():
    rides = [{"distance_km": 30.0} for _ in range(3)]
    badges = calculate_badges(1, rides)
    centomiglia = next(b for b in badges if b["id"] == 2)
    assert not centomiglia["achieved"]
    migliaia = next(b for b in badges if b["id"] == 3)
    assert not migliaia["achieved"]


def test_calculate_badges_centomiglia():
    rides = [{"distance_km": 50.0} for _ in range(20)]
    badges = calculate_badges(1, rides)
    centomiglia = next(b for b in badges if b["id"] == 2)
    assert centomiglia["achieved"] is True


def test_calculate_badges_speed():
    rides = [{"avg_speed_kmh": 32.0, "distance_km": 50.0}]
    badges = calculate_badges(1, rides)
    speed = next(b for b in badges if b["id"] == 9)
    assert speed["achieved"] is True


def test_calculate_streak_no_rides():
    assert calculate_streak([]) == 0


def test_calculate_streak_recent():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    rides = [{"date": (now - timedelta(days=i)).isoformat()} for i in range(3)]
    streak = calculate_streak(rides)
    assert streak == 3


def test_calculate_streak_gap():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    rides = [
        {"date": now.isoformat()},
        {"date": (now - timedelta(days=2)).isoformat()},
    ]
    streak = calculate_streak(rides)
    assert streak == 1


def test_heatmap_points_no_gps():
    result = get_heatmap_points([{"gps_points": None}])
    assert result["total_points"] == 0


def test_heatmap_points_with_gps():
    rides = [{"gps_points": [{"lat": 45.0, "lon": 9.0}, {"lat": 45.001, "lon": 9.001}]}]
    result = get_heatmap_points(rides)
    assert result["total_points"] == 2
    assert len(result["points"]) > 0
