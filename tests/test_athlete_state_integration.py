"""Integration tests for the Athlete State Engine API endpoints."""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


def _make_athlete_client(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "Test Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


def test_athlete_state_endpoint_with_auth(tmp_path):
    tc, athlete_id = _make_athlete_client(tmp_path)
    resp = tc.get("/api/v1/athlete/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["athlete_id"] == athlete_id
    assert "readiness" in data
    assert "fatigue_score" in data
    assert "ctl" in data
    assert "atl" in data
    assert "tsb" in data
    assert "risk_level" in data
    assert data["risk_level"] in ("ok", "warning", "high", "block")


def test_athlete_state_in_workout_generation(tmp_path):
    tc, athlete_id = _make_athlete_client(tmp_path)
    try:
        resp = tc.post("/api/v1/training/workouts/generate", json={"goal_id": 1, "event_count": 4})
    except RuntimeError as e:
        if "SQLAlchemy" in str(e):
            pytest.skip("SQLAlchemy/PostgreSQL not configured in test environment")
        raise
    assert resp.status_code in (200, 404, 422)
    if resp.status_code == 200:
        data = resp.json()
        assert "athlete_state" in data
        assert "generated" in data
        assert data["athlete_state"]["athlete_id"] == athlete_id


def test_athlete_state_model_roundtrip():
    from bike_analyzer.backend.analytics.athlete_state.models import AthleteState
    from datetime import datetime

    state = AthleteState(
        athlete_id=1,
        computed_at=datetime(2024, 6, 15, 10, 0, 0),
        fatigue_score=5.0,
        readiness=80.0,
        acwr=1.2,
        tsb=6.0,
        atl=70.0,
        ctl=75.0,
        fitness=75.0,
        fatigue=70.0,
        form=6.0,
        recovery_hours_needed=16.0,
        weekly_tss=500.0,
        monthly_tss=2000.0,
        trend_7d="increasing",
        trend_30d="stable",
        risk_indicators=["high_fatigue"],
        recommendation="Ready for hard effort",
        risk_level="ok",
    )
    d = state.to_dict()
    assert d["athlete_id"] == 1
    assert d["fatigue_score"] == 5.0
    assert d["readiness"] == 80.0
    assert d["is_ready_for_hard_effort"] is True

    dc = state.to_dataclass()
    assert dc.fatigue_score == 5.0
    assert dc.readiness == 80.0
    assert dc.acwr == 1.2
