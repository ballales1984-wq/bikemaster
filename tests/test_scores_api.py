"""Test scores API endpoints."""
import os

os.environ["GROQ_API_KEY"] = ""

from bike_analyzer.backend.analytics.performance import (
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_performance_score,
)
from bike_analyzer.backend.models.models import Ride


def test_performance_score_zero_speed():
    r = Ride(date="2024-06-01", distance_km=0.0, duration_minutes=60.0, avg_speed_kmh=0.0, calories=0)
    score = calculate_performance_score(r)
    assert 0 <= score <= 10


def test_endurance_score_empty():
    score = calculate_endurance_score([])
    assert score == 0.0


def test_efficiency_score_high_calories():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=1000)
    score = calculate_efficiency_score(r)
    assert 0 <= score <= 10


def test_performance_score_max():
    r = Ride(date="2024-06-01", distance_km=100.0, duration_minutes=200.0, avg_speed_kmh=40.0, calories=800, elevation_gain_m=800)
    score = calculate_performance_score(r)
    assert score >= 8.0
