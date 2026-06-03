"""Test analytics."""
from bike_analyzer.backend.models.models import Ride
from bike_analyzer.backend.analytics.calories import estimate_calories
from bike_analyzer.backend.analytics.fatigue import calculate_fatigue_score
from bike_analyzer.backend.analytics.analytics import calculate_summary

def test_calorie_estimation():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=20.0, weight_kg=70.0)
    c = estimate_calories(r)
    assert 0 < c < 1000

def test_fatigue_calculation():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=90.0, avg_speed_kmh=22.0, weight_kg=70.0, heart_rate_avg=150.0, elevation_gain_m=200.0)
    f = calculate_fatigue_score(r)
    assert 0 <= f <= 10

def test_calculate_summary():
    rides = [Ride(date="2024-06-01", distance_km=20.0, duration_minutes=45.0, avg_speed_kmh=26.7), Ride(date="2024-06-02", distance_km=30.0, duration_minutes=70.0, avg_speed_kmh=25.7)]
    s = calculate_summary(rides)
    assert s["total_rides"] == 2 and s["total_km"] == 50.0

def test_empty_summary():
    assert calculate_summary([])["total_rides"] == 0
