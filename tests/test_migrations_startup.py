"""Tests for automatic Alembic migration runner on startup."""

from __future__ import annotations

import importlib

import pytest

import bike_analyzer.backend.db.migrations as migrations_mod


def test_run_migrations_disabled_by_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RUN_MIGRATIONS_ON_STARTUP", "0")
    assert migrations_mod.run_migrations_on_startup() is False


def test_run_migrations_skipped_without_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RUN_MIGRATIONS_ON_STARTUP", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Point settings at an in-memory sqlite so database_url is falsy-ish; instead
    # force the cached settings instance to report no database_url.
    from bike_analyzer.backend import settings as settings_mod

    class _FakeSettings:
        database_url: str | None = None

    monkeypatch.setattr(settings_mod, "_settings", _FakeSettings())
    importlib.reload(migrations_mod)
    assert migrations_mod.run_migrations_on_startup() is False
    importlib.reload(migrations_mod)


def test_run_migrations_missing_ini_is_safe(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory):
    monkeypatch.setenv("RUN_MIGRATIONS_ON_STARTUP", "1")
    from bike_analyzer.backend import settings as settings_mod

    class _FakeSettings:
        database_url = "postgresql://user:pass@localhost/db"

    monkeypatch.setattr(settings_mod, "_settings", _FakeSettings())
    # Alembic not installed in this path -> graceful skip.
    monkeypatch.setitem(__import__("sys").modules, "alembic", None)
    importlib.reload(migrations_mod)
    # Point repo-root resolution at a temp dir without alembic.ini.
    monkeypatch.setattr(migrations_mod, "__file__", str(tmp_path / "x" / "y" / "z" / "migrations.py"))
    assert migrations_mod.run_migrations_on_startup() is False
    importlib.reload(migrations_mod)
