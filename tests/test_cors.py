"""Functional CORS tests for the FastAPI backend.

Validates:
- Allowed origins receive correct Access-Control-* headers.
- Disallowed origins receive no CORS headers.
- Wildcard origin is forbidden in production (except Vercel/Render regex fallback).
- Vercel/Render regex fallback works.
- OPTIONS preflight returns CORS headers.
- No Origin header means no CORS headers added.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod


@pytest.fixture
def dev_client(tmp_path):
    """TestClient with development environment and default CORS origins."""
    db_path = str(tmp_path / "cors_test.db")
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    _reset_settings(environment="development")
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = "Bearer test-token"
    return tc


@pytest.fixture
def prod_client(tmp_path, monkeypatch):
    """TestClient with production environment and explicit CORS origins."""
    db_path = str(tmp_path / "cors_prod.db")
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://bikemaster.onrender.com,https://bikemaster-xi.vercel.app,"
        "http://localhost:8001,http://localhost:8080",
    )
    monkeypatch.setenv("OAUTH_ALLOWED_REDIRECT_HOSTS", "bikemaster.onrender.com,bikemaster-xi.vercel.app")
    _reset_settings(environment="production")
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = "Bearer test-token"
    return tc


def _reset_settings(environment: str = "development") -> None:
    import bike_analyzer.backend.settings as settings_mod

    settings_mod._settings = None
    os.environ["ENVIRONMENT"] = environment


class TestCorsMiddleware:
    def test_allowed_origin_receives_cors_headers(self, prod_client):
        resp = prod_client.get(
            "/api/v1/health",
            headers={"Origin": "https://bikemaster-xi.vercel.app"},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "https://bikemaster-xi.vercel.app"
        assert resp.headers["access-control-allow-credentials"] == "true"

    def test_disallowed_origin_receives_no_cors_headers(self, prod_client):
        resp = prod_client.get(
            "/api/v1/health",
            headers={"Origin": "https://evil.com"},
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers

    def test_localhost_allowed_in_production(self, prod_client):
        resp = prod_client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:8001"},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "http://localhost:8001"

    def test_vercel_regex_fallback(self, prod_client):
        resp = prod_client.get(
            "/api/v1/health",
            headers={"Origin": "https://bikemaster-random-123.vercel.app"},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "https://bikemaster-random-123.vercel.app"

    def test_onrender_regex_fallback(self, prod_client):
        resp = prod_client.get(
            "/api/v1/health",
            headers={"Origin": "https://bikemaster.onrender.com"},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "https://bikemaster.onrender.com"

    def test_preflight_options_returns_cors_headers(self, prod_client):
        resp = prod_client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://bikemaster-xi.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert resp.status_code in (200, 204)
        assert resp.headers["access-control-allow-origin"] == "https://bikemaster-xi.vercel.app"
        assert "POST" in resp.headers["access-control-allow-methods"]
        assert "Authorization" in resp.headers["access-control-allow-headers"]

    def test_wildcard_origin_forbids_non_vercel_origin(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "cors_wildcard.db")
        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        _reset_settings(environment="production")
        app = create_app()
        tc = TestClient(app)
        resp = tc.get(
            "/api/v1/health",
            headers={"Origin": "https://evil.com"},
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers

    def test_empty_cors_origins_in_production_forbids_non_vercel(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "cors_empty.db")
        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        _reset_settings(environment="production")
        app = create_app()
        tc = TestClient(app)
        resp = tc.get(
            "/api/v1/health",
            headers={"Origin": "https://evil.com"},
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers

    def test_no_origin_header_does_not_add_cors(self, prod_client):
        resp = prod_client.get("/api/v1/health")
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers
