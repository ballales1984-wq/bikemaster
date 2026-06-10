import os
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-testing-123456"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["JWT_ISSUER"] = "test-issuer"
os.environ["JWT_AUDIENCE"] = "test-audience"
os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"
os.environ["GOOGLE_MAPS_API_KEY"] = ""

_TMP = Path(os.environ.get("TEMP", "/tmp")) / "bikemaster_test_dbs"
_TMP.mkdir(exist_ok=True)


def _new_db_path() -> str:
    p = _TMP / f"test_{id(_new_db_path)}.db"
    if p.exists():
        p.unlink()
    return str(p)


@pytest.fixture
def db_path():
    p = _new_db_path()
    yield p
    Path(p).unlink(missing_ok=True)


@pytest.fixture
def client(db_path):
    import bike_analyzer.backend.config as cfg_mod
    from bike_analyzer.backend.db import database as db_mod
    os.environ["DB_PATH"] = db_path
    cfg_mod.DB_PATH = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    from bike_analyzer.backend.security import create_access_token
    from bike_analyzer.backend.api.app_factory import create_app
    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject="0", is_admin=True)
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc


@pytest.fixture
def tmp_db(tmp_path):
    p = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = p
    yield p
