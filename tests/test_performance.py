"""Test performance engine."""
from bike_analyzer.backend.models.models import Ride, AthleteProfile
from bike_analyzer.backend.analytics.performance import calculate_performance_score, calculate_endurance_score, calculate_recovery_score, calculate_efficiency_score, classify_athlete

def test_performance_score():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=600, elevation_gain_m=200)
    score = calculate_performance_score(r)
    assert 0 <= score <= 10

def test_endurance_score():
    rides = [Ride(date=f"2024-06-{i:02d}", distance_km=20.0, duration_minutes=45.0, avg_speed_kmh=25.0) for i in range(1, 22)]
    score = calculate_endurance_score(rides)
    assert 0 <= score <= 10

def test_recovery_score():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=600)
    score = calculate_recovery_score(r)
    assert 0 <= score <= 10

def test_efficiency_score():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=600)
    score = calculate_efficiency_score(r)
    assert 0 <= score <= 10

def test_classify_athlete():
    beginner_rides = [Ride(date=f"2024-06-{i:02d}", distance_km=20.0, duration_minutes=45.0, avg_speed_kmh=20.0) for i in range(1, 5)]
    assert classify_athlete(beginner_rides) == "Beginner"
    elite_rides = [Ride(date=f"2024-06-{i:02d}", distance_km=100.0, duration_minutes=200.0, avg_speed_kmh=25.0) for i in range(1, 35)]
    assert classify_athlete(elite_rides) == "Elite"