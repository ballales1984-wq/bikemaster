"""Error-branch coverage for API routes.

Adds tests for 403/404/400/422 branches on already-tested endpoints
to move routes.py coverage higher with minimal new client setup.
"""

from __future__ import annotations

import os
import pytest


from starlette.testclient import TestClient

from bike_analyzer.backend.security import create_access_token


class TestRouteErrorBranches:
    """Error branches on endpoints already hit by smoke tests."""

    def test_get_ride_not_found(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.get("/api/v1/rides/99999")
        assert response.status_code == 404

    def test_delete_ride_not_found(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.delete("/api/v1/rides/99999")
        assert response.status_code == 404

    def test_create_ride_missing_body(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.post("/api/v1/rides", json={})
        assert response.status_code in (400, 422)

    def test_register_duplicate_username(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        payload = {"username": "dupuser", "password": "password123"}
        tc.post("/api/v1/auth/register", json=payload)
        response = tc.post("/api/v1/auth/register", json=payload)
        assert response.status_code in (400, 409, 422)

    def test_non_admin_cannot_access_admin_users(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=False)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.get("/api/v1/admin/users")
        assert response.status_code == 403

    def test_unauthenticated_access_to_rides(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/rides")
        assert response.status_code == 401

    def test_athlete_profile_update_validation(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.put("/api/v1/athletes/0", json={"weight_kg": -5})
        assert response.status_code in (400, 422)
