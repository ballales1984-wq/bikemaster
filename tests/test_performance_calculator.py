"""Tests for core performance calculator."""

from bike_analyzer.core.calculators.performance import (
    efficiency_score,
    endurance_score,
    monthly_scores,
    performance_score,
    recovery_score,
)
from bike_analyzer.core.models import Ride


def _ride(**kwargs):
    defaults = dict(  # noqa: C408
        id=1, athlete_id=1, date="2024-06-15",
        distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0,
        weight_kg=70.0, calories=600.0, heart_rate_avg=150.0,
        elevation_gain_m=200.0, gps_points=[],
    )
    defaults.update(kwargs)
    return Ride(**defaults)


class TestPerformanceScore:
    def test_basic(self):
        r = _ride(avg_speed_kmh=25.0, duration_minutes=60.0, elevation_gain_m=200.0)
        score = performance_score(r)
        assert 0.0 <= score <= 10.0

    def test_high_speed(self):
        r = _ride(avg_speed_kmh=40.0, duration_minutes=120.0, elevation_gain_m=500.0)
        score = performance_score(r)
        assert score > 0

    def test_low_speed(self):
        r = _ride(avg_speed_kmh=10.0, duration_minutes=30.0, elevation_gain_m=0.0)
        score = performance_score(r)
        assert score >= 0.0

    def test_no_elevation(self):
        r = _ride(avg_speed_kmh=25.0, duration_minutes=60.0, elevation_gain_m=None)
        score = performance_score(r)
        assert 0.0 <= score <= 10.0


class TestEnduranceScore:
    def test_empty_list(self):
        assert endurance_score([]) == 0.0

    def test_single_ride(self):
        rides = [_ride(duration_minutes=120.0, distance_km=50.0)]
        score = endurance_score(rides)
        assert 0.0 <= score <= 10.0

    def test_many_rides(self):
        rides = [_ride(id=i, duration_minutes=120.0, distance_km=50.0) for i in range(20)]
        score = endurance_score(rides)
        assert 0.0 <= score <= 10.0

    def test_short_rides(self):
        rides = [_ride(id=i, duration_minutes=30.0, distance_km=10.0) for i in range(5)]
        score = endurance_score(rides)
        assert score >= 0.0


class TestRecoveryScore:
    def test_low_fatigue(self):
        r = _ride(duration_minutes=30.0, avg_speed_kmh=20.0, elevation_gain_m=50.0)
        score = recovery_score(r)
        assert 0.0 <= score <= 10.0

    def test_high_fatigue(self):
        r = _ride(duration_minutes=180.0, avg_speed_kmh=30.0, elevation_gain_m=1000.0, heart_rate_avg=190.0)
        score = recovery_score(r)
        assert 0.0 <= score <= 10.0


class TestEfficiencyScore:
    def test_basic(self):
        r = _ride(distance_km=25.0, calories=600.0)
        score = efficiency_score(r)
        assert 0.0 <= score <= 10.0

    def test_zero_distance(self):
        r = _ride(distance_km=0.0, calories=100.0)
        score = efficiency_score(r)
        assert score == 0.0

    def test_low_calories(self):
        r = _ride(distance_km=50.0, calories=300.0)
        score = efficiency_score(r)
        assert score > 0


class TestMonthlyScores:
    def test_empty_list(self):
        result = monthly_scores([])
        assert result == {
            "performance": 0, "endurance": 0, "recovery": 0,
            "efficiency": 0, "avg_fatigue": 0,
        }

    def test_with_rides(self):
        rides = [
            _ride(id=1, duration_minutes=60.0, distance_km=25.0, calories=500.0),
            _ride(id=2, duration_minutes=90.0, distance_km=40.0, calories=800.0),
        ]
        result = monthly_scores(rides)
        assert "performance" in result
        assert "endurance" in result
        assert "recovery" in result
        assert "efficiency" in result
        assert "avg_fatigue" in result
        assert all(isinstance(v, (int, float)) for v in result.values())
