"""Shared pytest fixtures."""
import os
import pytest
from fastapi.testclient import TestClient
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"
os.environ["GOOGLE_MAPS_API_KEY"] = ""

@pytest.fixture(scope="session")
def client():
    from bike_analyzer.backend.api.app_factory import create_app
    app = create_app()
    return TestClient(app)

@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["BIKEMASTER_DB"] = db_path
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)
