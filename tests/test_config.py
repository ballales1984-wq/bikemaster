"""Tests for settings.py configuration."""

import os


def test_dev_mode_uses_sqlite_default():
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
    os.environ["ENVIRONMENT"] = "development"
    os.environ.pop("DATABASE_URL", None)
    from bike_analyzer.backend.settings import get_settings

    s = get_settings()
    assert "rides.db" in s.db_path or s.db_path.endswith(".db")


def test_settings_exposes_expected_constants():
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
    from bike_analyzer.backend.settings import get_settings

    s = get_settings()

    assert s.secret_key is not None
    assert s.algorithm == "HS256"
    assert s.access_token_expire_minutes == 30
    assert isinstance(s.cors_origins, str)
    assert len(s.cors_origins) > 0
    assert s.groq_model == "llama-3.3-70b-versatile"
    assert s.openai_model == "gpt-4o-mini"


def test_production_without_database_url_logs_warning(caplog):
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
    os.environ["ENVIRONMENT"] = "production"
    os.environ.pop("DATABASE_URL", None)
    with caplog.at_level("WARNING"):
        import bike_analyzer.backend.settings as settings_mod

        settings_mod._settings = None
        settings_mod.get_settings()

        assert any("DATABASE_URL" in str(r.message) for r in caplog.records)
