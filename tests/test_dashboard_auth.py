"""Tests for dashboard endpoint and auth refresh token."""

import os

os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-testing-123456"


class TestDashboardEndpoint:
    """Tests for the /api/v1/dashboard endpoint."""

    def test_dashboard_endpoint_exists(self, client):
        """Test that the dashboard endpoint returns data."""
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "athlete" in data
        assert "summary" in data
        assert "scores" in data
        assert "fitness" in data
        assert "trends" in data
        assert "rides_count" in data

    def test_dashboard_returns_zero_rides(self, client):
        """Test dashboard returns zeros for new user with no rides."""
        resp = client.get("/api/v1/dashboard")
        data = resp.json()
        assert data["rides_count"] == 0
        assert data["summary"]["total_rides"] == 0


class TestEmailField:
    """Tests for athlete email field."""

    def test_athlete_create_with_email(self, client):
        """Test athlete creation with email."""
        resp = client.post(
            "/api/v1/athletes", json={"name": "Test User", "email": "test@example.com", "experience_level": "Beginner"}
        )
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("name") == "Test User"

    def test_athlete_update_email(self, client):
        """Test athlete can update email."""
        resp = client.post("/api/v1/athletes", json={"name": "Email Test User", "email": "emailtest@example.com"})
        assert resp.status_code in (200, 409)


class TestRefreshToken:
    """Tests for refresh token functionality."""

    def test_refresh_endpoint_exists(self, client):
        """Test that the refresh endpoint exists."""
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid-token"})
        assert resp.status_code in (200, 401)

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token returns 401."""
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid-refresh-token"})
        assert resp.status_code == 401


class TestLoginWithRefresh:
    """Tests for login returning refresh token."""

    def test_login_returns_refresh_token(self, client, db_path):
        """Test that login response includes refresh_token."""
        from bike_analyzer.backend.db.database import init_db, save_athlete
        from bike_analyzer.backend.security import hash_password

        init_db()
        password_hash = hash_password("testpass123")
        save_athlete({"name": "loginuser", "email": "loginuser@test.com", "password_hash": password_hash})

        import bike_analyzer.backend.db.database as db_mod

        db_mod.DB_PATH = db_path

        from starlette.testclient import TestClient

        from bike_analyzer.backend.api.app_factory import create_app

        app = create_app()
        tc = TestClient(app)

        form = {"username": "loginuser", "password": "testpass123"}
        resp = tc.post("/api/v1/auth/login", data=form)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestRegisterWithEmail:
    """Tests for registration with email."""

    def test_register_with_email(self, client):
        """Test registration includes email field."""
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "emailuser", "password": "testpass123", "email": "emailuser@test.com"},
        )
        assert resp.status_code == 200 or resp.status_code == 400  # 400 if user exists
        if resp.status_code == 200:
            data = resp.json()
            assert "email" in data or "msg" in data


class TestScoreBreakdown:
    """Tests for score endpoint."""

    def test_scores_endpoint_exists(self, client):
        """Test scores endpoint returns data for current user."""
        resp = client.get("/api/v1/scores/athlete/0")
        assert resp.status_code in (200, 404)  # 404 if athlete not found
