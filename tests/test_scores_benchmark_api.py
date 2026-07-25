"""Tests for scores and benchmark API endpoints."""

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
    athlete_id = db_mod.save_athlete({"name": "Score Rider", "experience_level": "Intermediate"})
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


class TestAthleteScores:
    def test_get_scores_empty(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/scores/athlete/{aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "athlete" in data
        assert "scores" in data
        assert data["scores"]["performance_score"] == 0
        assert data["scores"]["endurance_score"] == 0
        assert data["scores"]["efficiency_score"] == 0
        assert data["scores"]["experience_level"] == "Beginner"

    def test_get_scores_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        resp = tc2.get(f"/api/v1/scores/athlete/{aid}")
        assert resp.status_code == 403

    def test_get_scores_admin_can_see_all(self, admin_client, athlete_client):
        tc_admin, admin_id = admin_client
        tc_athlete, aid = athlete_client
        resp = tc_admin.get(f"/api/v1/scores/athlete/{aid}")
        assert resp.status_code == 200
        assert "scores" in resp.json()

    def test_get_scores_not_found(self, admin_client):
        tc, admin_id = admin_client
        resp = tc.get("/api/v1/scores/athlete/99999")
        assert resp.status_code == 404

    def test_get_scores_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/scores/athlete/1")
        assert resp.status_code == 401


class TestBenchmarkCompare:
    def test_compare_valid_ride(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/benchmark/compare",
            json={
                "date": "2024-06-15",
                "distance_km": 40.0,
                "duration_minutes": 90.0,
                "avg_speed_kmh": 26.7,
                "elevation_gain_m": 500.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_compare_minimal_ride(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/benchmark/compare",
            json={
                "date": "2024-06-15",
                "distance_km": 20.0,
                "duration_minutes": 60.0,
            },
        )
        assert resp.status_code == 200

    def test_compare_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.post(
            "/api/v1/benchmark/compare",
            json={"date": "2024-06-15", "distance_km": 20.0, "duration_minutes": 60.0},
        )
        assert resp.status_code == 401

    def test_compare_missing_date(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/benchmark/compare",
            json={"distance_km": 20.0, "duration_minutes": 60.0},
        )
        assert resp.status_code == 422

    def test_compare_negative_distance(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/benchmark/compare",
            json={"date": "2024-06-15", "distance_km": -10.0, "duration_minutes": 60.0},
        )
        assert resp.status_code == 422
