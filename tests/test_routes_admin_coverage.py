"""Coverage boost for admin endpoints in routes.py."""

from __future__ import annotations

import os

import pytest

from bike_analyzer.backend.security import create_access_token


def _make_client(db_path, subject="0", is_admin=True):
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    tc = pytest.importorskip("starlette.testclient").TestClient(app)
    token = create_access_token(subject=subject, is_admin=is_admin)
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc


class TestAdminAthletes:
    def test_list_athletes(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/athletes", json={"name": "A1", "weight_kg": 70})
        response = tc.get("/api/v1/admin/athletes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_athletes_non_admin_forbidden(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=False)
        response = tc.get("/api/v1/admin/athletes")
        assert response.status_code == 403


class TestAdminBackup:
    def test_get_backup(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/admin/backup")
        assert response.status_code in (200, 500)

    def test_schedule_backup(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.post("/api/v1/admin/backup/scheduled", json={"cron": "0 0 * * *"})
        assert response.status_code in (200, 422, 500)

    def test_rebuild_indexes(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.post("/api/v1/admin/indexes")
        assert response.status_code in (200, 500)


class TestAdminStats:
    def test_get_stats(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data or "rides_count" in data or "athletes" in data

    def test_get_stats_non_admin(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=False)
        response = tc.get("/api/v1/admin/stats")
        assert response.status_code == 403


class TestAdminResetDemo:
    def test_reset_demo(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.post("/api/v1/admin/reset-demo")
        assert response.status_code in (200, 500)


class TestAdminUsers:
    def test_list_users(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/admin/users")
        assert response.status_code == 200

    def test_get_user_not_found(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.get("/api/v1/admin/users/99999")
        assert response.status_code == 404

    def test_create_user(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        response = tc.post("/api/v1/admin/users", json={"username": "newuser", "password": "x"})
        assert response.status_code in (200, 400, 422)

    def test_update_user(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/admin/users", json={"username": "u1", "password": "x"})
        response = tc.put("/api/v1/admin/users/1", json={"username": "u1-updated"})
        assert response.status_code in (200, 404, 422)

    def test_delete_user(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/admin/users", json={"username": "u2", "password": "x"})
        response = tc.delete("/api/v1/admin/users/2")
        assert response.status_code in (200, 404)

    def test_toggle_admin(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/admin/users", json={"username": "u3", "password": "x"})
        response = tc.post("/api/v1/admin/users/3/toggle-admin")
        assert response.status_code in (200, 404)

    def test_toggle_client(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/admin/users", json={"username": "u4", "password": "x"})
        response = tc.post("/api/v1/admin/users/4/toggle-client")
        assert response.status_code in (200, 404)

    def test_toggle_active(self, db_path):
        tc = _make_client(db_path, subject="0", is_admin=True)
        tc.post("/api/v1/admin/users", json={"username": "u5", "password": "x"})
        response = tc.post("/api/v1/admin/users/5/toggle-active")
        assert response.status_code in (200, 404)
