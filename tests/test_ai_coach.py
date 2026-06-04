"""Test AI Coach (mock mode)."""
import os
os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"

from bike_analyzer.backend.models.models import Ride, AthleteProfile
from bike_analyzer.backend.analytics.ai_coach import analyze_historical_trend, generate_recovery_advice

def test_analyze_historical_trend_empty():
    result = analyze_historical_trend([])
    assert "insufficienti" in result.lower()

def test_analyze_historical_trend():
    rides = [Ride(date=f"2024-06-{i:02d}", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, calories=500, elevation_gain_m=200) for i in range(1, 4)]
    result = analyze_historical_trend(rides)
    assert "Trend:" in result