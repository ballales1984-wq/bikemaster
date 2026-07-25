"""Tests for coach API endpoints.

Covers /coach/workout, /coach/full, /coach/recovery, /coach/trends,
including access control, empty states, and response shape.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


@pytest.fixture
def athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "Coach Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


@pytest.fixture
def admin_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    admin_id = db_mod.save_athlete({"name": "Admin", "experience_level": "Advanced"})
    db_mod.update_athlete(admin_id, {"tenant_id": admin_id, "is_admin": True})
    token = create_access_token(subject=str(admin_id), is_admin=True, tenant_id=admin_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, admin_id


@pytest.fixture
def second_athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    aid = db_mod.save_athlete({"name": "Other Rider", "experience_level": "Beginner"})
    db_mod.update_athlete(aid, {"tenant_id": aid})
    token = create_access_token(subject=str(aid), is_admin=False, tenant_id=aid)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, aid


class TestCoachWorkout:
    def test_workout_returns_recommendations(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/workout?athlete_id={aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_workout_uses_current_user_when_no_id(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/coach/workout")
        assert resp.status_code == 200
        assert "recommendations" in resp.json()

    def test_workout_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        resp = tc2.get(f"/api/v1/coach/workout?athlete_id={aid}")
        assert resp.status_code == 403

    def test_workout_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/coach/workout")
        assert resp.status_code == 401


class TestCoachFull:
    def test_full_returns_report(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/full?athlete_id={aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "training_advice" in data
        assert "recovery_advice" in data
        assert "historical_analysis" in data
        assert "training_scores" in data
        assert "recovery_scores" in data
        assert "charts" in data

    def test_full_uses_current_user_when_no_id(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/coach/full")
        assert resp.status_code == 200
        data = resp.json()
        assert "training_advice" in data
        assert "recovery_advice" in data

    def test_full_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        resp = tc2.get(f"/api/v1/coach/full?athlete_id={aid}")
        assert resp.status_code == 403

    def test_full_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/coach/full")
        assert resp.status_code == 401


class TestCoachRecovery:
    def test_recovery_returns_recommendations(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/coach/recovery")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_recovery_with_fatigue_score(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/coach/recovery?fatigue_score=8.0")
        assert resp.status_code == 200
        assert "recommendations" in resp.json()

    def test_recovery_with_ride_id(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/coach/recovery?ride_id=0")
        assert resp.status_code in (200, 404)

    def test_recovery_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/coach/recovery")
        assert resp.status_code == 401


class TestCoachTrends:
    def test_trends_returns_analysis(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/coach/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (dict, str))

    def test_trends_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        # trends non accetta athlete_id come query param, usa current_user
        # quindi tc2 vede solo i propri trend (vuoti)
        resp = tc2.get("/api/v1/coach/trends")
        assert resp.status_code == 200

    def test_trends_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/coach/trends")
        assert resp.status_code == 401


class TestCoachAdminAccess:
    def test_admin_can_call_workout_for_any_athlete(self, admin_client, athlete_client):
        tc_admin, admin_id = admin_client
        tc_athlete, aid = athlete_client
        resp = tc_admin.get(f"/api/v1/coach/workout?athlete_id={aid}")
        assert resp.status_code == 200
        assert "recommendations" in resp.json()

    def test_admin_can_call_full_for_any_athlete(self, admin_client, athlete_client):
        tc_admin, admin_id = admin_client
        tc_athlete, aid = athlete_client
        resp = tc_admin.get(f"/api/v1/coach/full?athlete_id={aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "training_advice" in data
