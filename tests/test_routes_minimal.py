"""Minimal test to verify TestClient works in pytest."""

import os
import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod


@pytest.fixture
def client(db_path):
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
