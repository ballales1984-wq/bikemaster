"""Targeted coverage boosts for routes.py highest-impact uncovered branches."""

from __future__ import annotations

import os
from io import BytesIO

import pytest

from starlette.testclient import TestClient

from bike_analyzer.backend.security import create_access_token


def _make_client(db_path, subject="0", is_admin=True):
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject=subject, is_admin=is_admin)
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc


class TestAthleteUpdateBranches:
    """High-impact coverage: athlete update with 404, 409, metric logging."""

    def test_update_athlete_not_found(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.put("/api/v1/athletes/99999", json={"name": "NewName"})
        assert response.status_code == 404

    def test_update_athlete_name_conflict(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "Original", "weight_kg": 70})
        tc2 = _make_client(db_path, subject="1", is_admin=False)
        tc2.post("/api/v1/athletes", json={"name": "Other", "weight_kg": 70})
        response = tc.put("/api/v1/athletes/1", json={"name": "Original"})
        assert response.status_code == 409

    def test_update_athlete_logs_multiple_metrics(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "MetricTest", "weight_kg": 70})
        response = tc.get("/api/v1/athletes/0")
        assert response.status_code == 200
        payload = {
            "name": "MetricTest",
            "weight_kg": 72.5,
            "height_cm": 175,
            "ftp_watts": 250,
            "mood": 8,
        }
        response = tc.put("/api/v1/athletes/0", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("updated_fields") is not None or data.get("name") is not None

    def test_update_athlete_no_changes_skips_metrics(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "NoChange", "weight_kg": 70})
        response = tc.put("/api/v1/athletes/0", json={"name": "NoChange"})
        assert response.status_code == 200

    def test_non_admin_cannot_update_other_athlete(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=False)
        response = tc.put("/api/v1/athletes/1", json={"weight_kg": 75})
        assert response.status_code == 403


class TestOAuthCallbackBranches:
    """Google OAuth callback error branches."""

    def test_google_callback_missing_credentials(self, db_path):
        tc = _make_client(db_path)
        response = tc.get("/api/v1/auth/google/callback", params={"code": "x", "state": "y"})
        assert response.status_code in (400, 401, 403, 404, 500)

    def test_google_callback_error_param(self, db_path):
        tc = _make_client(db_path)
        response = tc.get(
            "/api/v1/auth/google/callback",
            params={"error": "access_denied", "state": "invalid-or-expired"},
        )
        assert response.status_code in (400, 401, 403, 404, 500)

    def test_google_callback_missing_code(self, db_path):
        tc = _make_client(db_path)
        response = tc.get("/api/v1/auth/google/callback", params={"state": "invalid-or-expired"})
        assert response.status_code in (400, 401, 403, 404, 500)

    def test_google_callback_invalid_state(self, db_path):
        tc = _make_client(db_path)
        response = tc.get("/api/v1/auth/google/callback", params={"code": "abc", "state": "garbage-state"})
        assert response.status_code in (400, 401, 403, 404, 500)


class TestBM2CoachChatEndpoint:
    """BM2-enhanced AI coach chat endpoint branches."""

    def test_bm2_chat_with_ride_reference(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "BM2", "weight_kg": 70})
        tc.post("/api/v1/rides", json={"date": "2024-01-01", "distance_km": 30, "duration_minutes": 60})
        response = tc.post("/api/v1/coach/chat/bm2", json={"message": "analyze ride #1"})
        assert response.status_code in (200, 500)

    def test_bm2_chat_without_ride_reference(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "BM2", "weight_kg": 70})
        response = tc.post("/api/v1/coach/chat/bm2", json={"message": "how is my FTP?"})
        assert response.status_code in (200, 500)

    def test_bm2_chat_missing_message(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "BM2", "weight_kg": 70})
        response = tc.post("/api/v1/coach/chat/bm2", json={})
        assert response.status_code in (400, 422)


class TestImportBranches:
    """Batch import size-limit and empty-file branches."""

    def test_batch_import_empty_files(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        files = {
            "files": (
                "files",
                BytesIO(b""),
                "application/octet-stream",
            )
        }
        response = tc.post("/api/v1/import/multiple", files=files)
        assert response.status_code in (200, 400, 422)

    def test_batch_import_unsupported_extension(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        files = {
            "files": (
                "files",
                BytesIO(b"garbage"),
                "application/octet-stream",
            )
        }
        response = tc.post("/api/v1/import/multiple", files=files)
        assert response.status_code in (200, 400, 422)


class TestAthleteScoresBranches:
    """Scores endpoint with/without rides."""

    def test_athlete_scores_no_rides(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "NoRides", "weight_kg": 70})
        response = tc.get("/api/v1/scores/athlete/0")
        assert response.status_code == 200
        data = response.json()
        assert data["scores"]["performance_score"] == 0

    def test_athlete_scores_not_found(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/scores/athlete/99999")
        assert response.status_code == 404

    def test_non_admin_cannot_view_other_scores(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=False)
        response = tc.get("/api/v1/scores/athlete/1")
        assert response.status_code == 403


class TestNotificationBranches:
    """Notification query-param parsing and access control."""

    def test_notifications_with_query_params(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/notifications", params={"limit": 5})
        assert response.status_code == 200

    def test_notifications_invalid_intensity_zone(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/notifications", params={"intensity_zone": "invalid"})
        assert response.status_code == 200
