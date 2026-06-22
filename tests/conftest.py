import asyncio
import inspect
import os
import time
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Set test environment BEFORE any imports that might trigger settings loading
os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-testing-123456"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["JWT_ISSUER"] = "test-issuer"
os.environ["JWT_AUDIENCE"] = "test-audience"
os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"
os.environ["GOOGLE_MAPS_API_KEY"] = ""
os.environ["SENTRY_DSN"] = ""
os.environ["ENVIRONMENT"] = "test"
os.environ["WEATHER_API_KEY"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""

_TMP = Path(os.environ.get("TEMP", "/tmp")) / "bikemaster_test_dbs"
_TMP.mkdir(exist_ok=True)


def _safe_unlink(path: Path) -> None:
    for attempt in range(5):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt < 4:
                time.sleep(0.05)
            else:
                pass


def _new_db_path() -> str:
    p = _TMP / f"test_{id(_new_db_path)}.db"
    for suffix in ("", "-wal", "-shm"):
        _safe_unlink(Path(str(p) + suffix))
    return str(p)


@pytest.fixture
def db_path():
    p = _new_db_path()
    yield p
    for suffix in ("", "-wal", "-shm"):
        _safe_unlink(Path(str(p) + suffix))


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from bike_analyzer.backend.rate_limiter import limiter

    limiter.reset()
    yield


@pytest.fixture
def client(db_path):
    import bike_analyzer.backend.config as cfg_mod
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.security import create_access_token
    from bike_analyzer.backend.db import database as db_mod

    os.environ["DB_PATH"] = db_path
    cfg_mod.DB_PATH = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()

    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject="0", is_admin=True)
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc


@pytest.fixture
def unauthenticated_client(db_path):
    """TestClient without default auth headers."""
    import bike_analyzer.backend.config as cfg_mod
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod

    os.environ["DB_PATH"] = db_path
    cfg_mod.DB_PATH = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    return TestClient(app)


@pytest.fixture
def tmp_db(tmp_path):
    p = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = p
    yield p
