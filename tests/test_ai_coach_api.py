import os

os.environ["GROQ_API_KEY"] = "test-key"

from bike_analyzer.backend.analytics.ai_coach import (
    ai_coach_full,
    analyze_historical_trend,
    generate_recovery_recommendations,
    generate_training_advice,
    validate_athlete_profile,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def test_validate_athlete_profile_rejects_empty():
    profile = AthleteProfile(name="", weight_kg=70.0, experience_level="Beginner")
    valid, msg = validate_athlete_profile(profile)
    assert valid is False
    assert "nome" in msg


def test_validate_athlete_profile_accepts_complete():
    profile = AthleteProfile(name="Marco", weight_kg=72.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(profile)
    assert valid is True
    assert msg == ""


def test_generate_training_advice_validates_profile():
    result = generate_training_advice(AthleteProfile(), [])
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_training_advice_with_local_mode(monkeypatch):
    import bike_analyzer.backend.analytics.ai_coach as coach
    import bike_analyzer.backend.config as cfg

    monkeypatch.setattr(cfg, "AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "AI_COACH_MODE", "local")
    result = generate_training_advice(
        AthleteProfile(name="Marco", weight_kg=70.0, experience_level="Beginner"), []
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_recovery_advice_returns_string():
    result = generate_recovery_recommendations(AthleteProfile(), [], fatigue_score=5.0)
    assert isinstance(result, str)
    assert len(result) > 0


def test_analyze_historical_trend_insufficient_data():
    result = analyze_historical_trend([])
    assert "Insufficient" in result


def test_analyze_historical_trend_with_rides():
    rides = [
        Ride(date="2026-01-01", distance_km=30.0, duration_minutes=90.0, avg_speed_kmh=20.0),
        Ride(date="2026-01-02", distance_km=35.0, duration_minutes=85.0, avg_speed_kmh=24.7),
    ]
    result = analyze_historical_trend(rides)
    assert isinstance(result, str)
    assert "Trend" in result


def test_ai_coach_full_returns_dict():
    result = ai_coach_full(
        AthleteProfile(name="Test", weight_kg=70.0, experience_level="Beginner"), [], athlete_id=0
    )
    assert isinstance(result, dict)
    assert "training_advice" in result
    assert "recovery_advice" in result
    assert "historical_analysis" in result
    assert "training_scores" in result
    assert "recovery_scores" in result
    assert "charts" in result


def test_ai_coach_workout_endpoint(client):
    r = client.get("/api/v1/coach/workout")
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data


def test_ai_coach_workout_endpoint_with_athlete(client, db_path):
    from bike_analyzer.backend.db import database as db_mod
    athlete_id = db_mod.save_athlete(
        {"name": "Test Athlete", "weight_kg": 70.0, "experience_level": "Beginner"}
    )
    r = client.get("/api/v1/coach/workout", params={"athlete_id": athlete_id})
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data


def test_ai_coach_recovery_endpoint(client):
    r = client.get("/api/v1/coach/recovery")
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data
