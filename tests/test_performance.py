"""Test performance engine."""

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.performance import (
    calculate_annual_scores,
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_monthly_scores,
    calculate_performance_score,
    calculate_recovery_score,
    classify_athlete,
    get_experience_level,
    should_save_to_database,
)
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride


def test_performance_score():
    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=60.0,
        avg_speed_kmh=25.0,
        calories=600,
        elevation_gain_m=200,
    )
    score = calculate_performance_score(r)
    assert 0 <= score <= 10


def test_endurance_score():
    rides = [
        Ride(date=f"2024-06-{i:02d}", distance_km=20.0, duration_minutes=45.0, avg_speed_kmh=25.0)
        for i in range(1, 22)
    ]
    score = calculate_endurance_score(rides)
    assert 0 <= score <= 10


def test_recovery_score():
    r = Ride(
        date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=600
    )
    score = calculate_recovery_score(r)
    assert 0 <= score <= 10


def test_efficiency_score():
    r = Ride(
        date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=600
    )
    score = calculate_efficiency_score(r)
    assert 0 <= score <= 10


def test_classify_athlete():
    beginner_rides = [
        Ride(date=f"2024-06-{i:02d}", distance_km=20.0, duration_minutes=45.0, avg_speed_kmh=20.0)
        for i in range(1, 5)
    ]
    assert classify_athlete(beginner_rides) == "Beginner"
    elite_rides = [
        Ride(date=f"2024-06-{i:02d}", distance_km=100.0, duration_minutes=200.0, avg_speed_kmh=25.0)
        for i in range(1, 35)
    ]
    assert classify_athlete(elite_rides) == "Elite"


def test_monthly_scores_empty():
    assert calculate_monthly_scores([]) == {
        "performance": 0,
        "endurance": 0,
        "recovery": 0,
        "efficiency": 0,
        "avg_fatigue": 0,
    }


def test_annual_scores_empty():
    assert calculate_annual_scores([]) == {
        "performance": 0,
        "endurance": 0,
        "total_km": 0,
        "total_calories": 0,
        "avg_fatigue": 0,
    }


def test_efficiency_score_zero_distance():
    r = Ride(
        date="2024-06-01", distance_km=0.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=500
    )
    assert calculate_efficiency_score(r) == 0.0


def test_get_experience_level():
    athlete = AthleteProfile(name="Test", experience_level="Intermediate")
    assert get_experience_level(athlete) == "Intermediate"


def test_should_save_to_database():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC))]
    assert should_save_to_database(points)
    assert not should_save_to_database([])
