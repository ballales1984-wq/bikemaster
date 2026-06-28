"""Tests for config.py settings wrapper."""

import os

import pytest


def test_dev_mode_uses_sqlite_default():
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
    os.environ["ENVIRONMENT"] = "development"
    os.environ.pop("DATABASE_URL", None)
    from bike_analyzer.backend.config import DB_PATH, DATABASE_URL

    assert "rides.db" in DB_PATH or DB_PATH.endswith(".db")


def test_config_exposes_expected_constants():
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
    from bike_analyzer.backend.config import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        ALGORITHM,
        CORS_ORIGINS,
        DB_PATH,
        GROQ_MODEL,
        OPENAI_MODEL,
        SECRET_KEY,
    )

    assert SECRET_KEY is not None
    assert ALGORITHM == "HS256"
    assert ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert isinstance(CORS_ORIGINS, list)
    assert len(CORS_ORIGINS) > 0
    assert GROQ_MODEL == "llama-3.3-70b-versatile"
    assert OPENAI_MODEL == "gpt-4o-mini"


def test_production_without_database_url_logs_warning(caplog):
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
    os.environ["ENVIRONMENT"] = "production"
    os.environ.pop("DATABASE_URL", None)
    with caplog.at_level("WARNING"):
        import bike_analyzer.backend.settings as settings_mod

        settings_mod._settings = None
        from bike_analyzer.backend.config import DATABASE_URL

        assert any("DATABASE_URL" in str(r.message) for r in caplog.records)
