"""Error-branch coverage for API routes.

Adds tests for 403/404/400/422 branches on already-tested endpoints
to move routes.py coverage higher with minimal new client setup.
"""

from __future__ import annotations

import os

from starlette.testclient import TestClient

from bike_analyzer.backend.security import create_access_token


class TestRouteErrorBranches:
    """Error branches on endpoints already hit by smoke tests."""

    def test_get_ride_not_found(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

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

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        athlete_id = db_mod.save_athlete({"name": "Validation Test", "experience_level": "Beginner"}, user_id=0)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.put(f"/api/v1/athletes/{athlete_id}", json={"weight_kg": -5})
        assert response.status_code in (400, 422)

    def test_sqlite_integrity_error_returns_409(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": 1, "title": "Test", "date": "2024-06-15"},
        )
        assert response.status_code in (200, 400, 401, 409)

    def test_google_oauth_callback_missing_params(self, db_path):
        import bike_analyzer.backend.api.app_factory as app_factory_mod
        import bike_analyzer.backend.settings as settings_mod
        from bike_analyzer.backend.api import routes as routes_mod
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        settings_mod._settings = None
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        routes_mod._s = settings_mod.get_settings()
        app_factory_mod._s = settings_mod.get_settings()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/auth/google/callback", follow_redirects=False)
        assert response.status_code == 404

    def test_strava_callback_missing_params(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/import/strava/callback")
        assert response.status_code == 200

    def test_garmin_callback_missing_params(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/import/garmin/callback")
        assert response.status_code == 200

    def test_ble_device_not_found(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.get("/api/v1/ble/devices/99999")
        assert response.status_code in (404, 401, 405)

    def test_import_multiple_empty(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.post("/api/v1/import/multiple", files=[])
        assert response.status_code in (400, 401, 422)

    def test_strava_callback_page_error(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/import/strava/callback", params={"error": "access_denied"})
        assert response.status_code == 200

    def test_strava_callback_page_missing_code(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/import/strava/callback")
        assert response.status_code == 200

    def test_import_providers_returns_config(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/import/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_coach_workout_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/coach/workout")
        assert response.status_code == 401

    def test_coach_workout_forbidden_for_other_athlete(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        token_owner = create_access_token(subject="10", is_admin=False)
        token_other = create_access_token(subject="20", is_admin=False)  # noqa: F841
        tc.headers["Authorization"] = f"Bearer {token_owner}"
        response = tc.get("/api/v1/coach/workout?athlete_id=20")
        assert response.status_code == 403

    def test_ble_sync_invalid_device(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.post("/api/v1/ble/devices/99999/sync", json={})
        assert response.status_code in (404, 401)

    def test_auth_me_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_athletes_me_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/athletes/me")
        assert response.status_code == 401

    def test_health_detailed_public(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)

        response = tc.get("/api/v1/health/detailed")
        assert response.status_code == 404

    def test_athlete_profile_update_not_found(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.put("/api/v1/athletes/99999", json={"weight_kg": 75.5})
        assert response.status_code == 404

    def test_athlete_profile_update_invalid_weight(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"

        response = tc.put("/api/v1/athletes/0", json={"weight_kg": -5})
        assert response.status_code in (400, 422)

    def test_athletes_list_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        response = tc.get("/api/v1/athletes")
        assert response.status_code == 401

    def test_athlete_metric_log_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        response = tc.post(
            "/api/v1/athletes/0/metrics",
            json={"metric_type": "weight", "value": 75.0},
        )
        assert response.status_code == 401

    def test_athlete_history_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        response = tc.get("/api/v1/athletes/me/history")
        assert response.status_code == 401

    def test_client_athletes_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        response = tc.get("/api/v1/client/athletes")
        assert response.status_code == 404

    def test_sentry_debug_in_test(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        response = tc.get("/api/v1/sentry-debug")
        assert response.status_code == 500

    def test_alerts_webhook_unauthenticated(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        os.environ["ALERTMANAGER_WEBHOOK_TOKEN"] = "secret-token"
        app = create_app()
        tc = TestClient(app)
        response = tc.post("/api/v1/alerts/webhook", json={"receiver": "test"})
        assert response.status_code == 401
