"""Shared pytest fixtures."""
import os
import sys

import pytest
from fastapi.testclient import TestClient

os.environ["TEMP"] = "D:\\Temp"
os.environ["TMP"] = "D:\\Temp"
os.environ["TMPDIR"] = "D:\\Temp"
os.makedirs("D:\\Temp", exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"
os.environ["GOOGLE_MAPS_API_KEY"] = ""

@pytest.fixture(scope="session")
def client():
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.security import create_access_token
    app = create_app()
    test_client = TestClient(app)
    token = create_access_token(subject="0", is_admin=True)
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client

@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_path
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)
