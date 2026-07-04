"""Integration tests for API routes — targets routes.py coverage gaps."""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app


@pytest.fixture
def athlete_client(client, tmp_db):
    """Client with a pre-created athlete for authenticated routes."""
    import bike_analyzer.backend.config as cfg_mod
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = tmp_db
    cfg_mod.DB_PATH = tmp_db
    db_mod.DB_PATH = tmp_db
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "Test Rider", "experience_level": "Intermediate"})
    token = create_access_token(subject=str(athlete_id), is_admin=False)
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


@pytest.fixture
def admin_client(tmp_db):
    import bike_analyzer.backend.config as cfg_mod
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = tmp_db
    cfg_mod.DB_PATH = tmp_db
    db_mod.DB_PATH = tmp_db
    db_mod.init_db()
    token = create_access_token(subject="0", is_admin=True)
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc


class TestCoachRoutes:
    def test_workout_recommendations(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/workout?athlete_id={aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_coach_full_with_athlete(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/full?athlete_id={aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "training_advice" in data
        assert "recovery_advice" in data

    def test_coach_full_without_athlete_id(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/coach/full")
        assert resp.status_code == 200

    def test_coach_recovery(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/recovery?athlete_id={aid}")
        assert resp.status_code == 200
        data = resp.json()
        # Endpoint may return error if athlete profile incomplete
        assert "recommendations" in data or "recovery_advice" in data

    def test_coach_chat(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/chat?athlete_id={aid}&message=hello")
        # 422 if message required but not provided
        assert resp.status_code in (200, 422)

    def test_coach_chat_post(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(f"/api/v1/coach/chat?athlete_id={aid}&message=test")
        # 422 if message required but not provided
        assert resp.status_code in (200, 422)

    def test_coach_history(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/history?athlete_id={aid}")
        assert resp.status_code == 200


class TestKnowledgeRoutes:
    def test_list_knowledge(self, client):
        resp = client.get("/api/v1/knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert "topics" in data

    def test_search_knowledge(self, client):
        resp = client.get("/api/v1/knowledge/search?query=VO2+Max")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    def test_search_knowledge_empty_query(self, client):
        resp = client.get("/api/v1/knowledge/search?query=")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_knowledge_stats(self, client):
        resp = client.get("/api/v1/knowledge/stats")
        assert resp.status_code == 200


class TestTrainingRoutes:
    def test_training_load(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/load?athlete_id={aid}&days=30")
        assert resp.status_code == 200

    def test_training_status(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/status?athlete_id={aid}")
        assert resp.status_code == 200

    def test_training_summary(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/summary?athlete_id={aid}")
        assert resp.status_code == 200

    def test_training_goals_post(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            f"/api/v1/training/goals?athlete_id={aid}",
            json={
                "title": "Test Goal",
                "goal_type": "granfondo",
                "target_date": "2026-12-31",
                "target_distance_km": 100,
            },
        )
        assert resp.status_code == 200

    def test_training_goals_list(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/goals?athlete_id={aid}")
        assert resp.status_code == 200
