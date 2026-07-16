"""Tests for the sync management REST API (api/sync_routes.py).

These cover the local orchestration endpoints (status, settings, conflicts)
without requiring a configured cloud backend.
"""

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


def _client(subject: str = "1", is_admin: bool = True, db_path: str | None = None) -> TestClient:
    if db_path:
        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = f"Bearer {create_access_token(subject=subject, is_admin=is_admin)}"
    return tc


def test_sync_status_requires_auth():
    app = create_app()
    tc = TestClient(app)
    assert tc.get("/api/v1/sync/status").status_code in (401, 403)


def test_sync_status_ok(db_path):
    resp = _client(db_path=db_path).get("/api/v1/sync/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "mode" in body
    assert "enabled" in body
    assert "pending_count" in body
    assert "conflict_count" in body
    assert "cloud_connected" in body


def test_sync_settings_get_and_update(db_path):
    tc = _client(db_path=db_path)
    resp = tc.get("/api/v1/sync/settings")
    assert resp.status_code == 200
    assert "mode" in resp.json()

    upd = tc.put("/api/v1/sync/settings", json={"mode": "manual"})
    assert upd.status_code == 200
    assert upd.json()["mode"] in ("manual", "Manual", "MANUAL")

    bad = tc.put("/api/v1/sync/settings", json={"mode": "invalid"})
    assert bad.status_code == 422

    bad_hour = tc.put("/api/v1/sync/settings", json={"daily_hour": 99})
    assert bad_hour.status_code == 422


def test_sync_trigger_not_enabled(db_path):
    tc = _client(db_path=db_path)
    resp = tc.post("/api/v1/sync/trigger")
    assert resp.status_code == 400


def test_sync_conflicts_list_empty(db_path):
    resp = _client(db_path=db_path).get("/api/v1/sync/conflicts")
    assert resp.status_code == 200
    assert resp.json()["conflicts"] == []


def test_resolve_conflict_not_found(db_path):
    resp = _client(db_path=db_path).post(
        "/api/v1/sync/conflicts/0/resolve",
        json={"resolution": "local"},
    )
    assert resp.status_code == 404


def test_resolve_conflict_bad_resolution(db_path):
    resp = _client(db_path=db_path).post(
        "/api/v1/sync/conflicts/0/resolve",
        json={"resolution": "sideways"},
    )
    assert resp.status_code == 422
