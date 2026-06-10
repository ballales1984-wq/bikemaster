"""Test AI Coach (mock mode)."""

import os

os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"

from bike_analyzer.backend.analytics.ai_coach import (
    analyze_historical_trend,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def test_analyze_historical_trend_empty():
    result = analyze_historical_trend([])
    assert "insufficienti" in result.lower()


def test_analyze_historical_trend():
    rides = [
        Ride(
            date=f"2024-06-{i:02d}",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=500,
            elevation_gain_m=200,
        )
        for i in range(1, 4)
    ]
    result = analyze_historical_trend(rides)
    assert "Trend:" in result


def test_clean_ai_output():
    from bike_analyzer.backend.analytics.ai_coach import _clean_ai_output

    assert _clean_ai_output("  test  ") == "test"
    assert _clean_ai_output("1.50 km") == "1.5 km"
    assert _clean_ai_output("5.0 hours") == "5 hours"
    assert _clean_ai_output("test  multiple   spaces") == "test multiple spaces"


def test_validate_athlete_profile_complete():
    from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

    athlete = AthleteProfile(name="Mario Rossi", weight_kg=75.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is True


def test_validate_athlete_profile_missing_name():
    from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

    athlete = AthleteProfile(name="", weight_kg=75.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is False
    assert "nome" in msg
