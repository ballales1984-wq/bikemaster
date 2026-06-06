"""Tests for AI Coach endpoints."""
import os
os.environ["GROQ_API_KEY"] = "test-key"

from fastapi.testclient import TestClient
from bike_analyzer.backend.api.app_factory import create_app

client = TestClient(create_app())


def test_coach_workout_endpoint():
    r = client.get("/api/v1/coach/workout")
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data


def test_coach_full_endpoint():
    r = client.get("/api/v1/coach/full")
    assert r.status_code == 200
    data = r.json()
    assert "training_advice" in data
    assert "recovery_advice" in data
    assert "training_scores" in data
    assert "recovery_scores" in data
    assert "charts" in data


def test_coach_trends_endpoint():
    r = client.get("/api/v1/coach/trends")
    assert r.status_code == 200
    data = r.json()
    assert "Trend:" in data.get("historical_analysis", "")
