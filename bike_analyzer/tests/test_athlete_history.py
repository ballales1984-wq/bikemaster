"""Tests for athlete history snapshot functionality."""
from __future__ import annotations

from bike_analyzer.backend.db import database as db_module
from bike_analyzer.backend.db.database import (
    get_athlete,
    get_athlete_history,
    init_db,
    save_athlete,
    save_athlete_snapshot,
    update_athlete,
)


def _make_athlete_data(athlete_id: int = 1, name: str = "Test Rider") -> dict:
    return {
        "id": athlete_id,
        "name": name,
        "email": "test@example.com",
        "age": 30,
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "fat_percentage": 15.0,
        "years_active": 2,
        "weekly_sessions": 3,
        "monthly_hours": 8.0,
        "annual_hours": 96.0,
        "experience_level": "Intermediate",
        "goals": "Gran Fondo",
        "preferred_terrain": "mountain",
        "weekly_volume_km": 200.0,
        "best_segments": None,
        "medical_notes": None,
        "equipment": "Road bike",
        "ftp_watts": 250.0,
        "body_water_percentage": 55.0,
        "muscle_mass_percentage": 42.0,
        "bmr_kcal": 1800.0,
        "fat_mass_kg": 10.5,
        "subcutaneous_fat_kg": 8.0,
        "subcutaneous_fat_percentage": 11.0,
        "visceral_fat_level": 5.0,
        "visceral_fat_percentage": 7.0,
        "visceral_fat_kg": 3.5,
        "muscle_mass_kg": 29.0,
        "bone_mass_kg": 10.0,
        "protein_percentage": 16.0,
        "protein_kg": 11.2,
        "body_age": 28,
        "apparent_age": 27,
        "password_hash": None,
        "tenant_id": 0,
    }


def test_save_athlete_creates_history_on_update(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_history.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    init_db()

    athlete_data = _make_athlete_data(athlete_id=1, name="Test Rider")
    save_athlete(athlete_data, athlete_id=1, tenant_id=0)

    initial = get_athlete(1, 0)
    assert initial is not None
    assert initial["weight_kg"] == 70.0

    history = get_athlete_history(1, limit=10)
    assert len(history) == 0

    update_athlete(1, {"weight_kg": 72.0})

    history = get_athlete_history(1, limit=10)
    assert len(history) == 1

    snapshot = history[0]
    assert snapshot["athlete_id"] == 1
    assert snapshot["recorded_at"] is not None
    assert snapshot["weight_kg"] == 70.0
    assert snapshot["changed_by"] is None

    updated = get_athlete(1, 0)
    assert updated["weight_kg"] == 72.0


def test_multiple_updates_create_multiple_snapshots(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_multi_history.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    init_db()

    athlete_data = _make_athlete_data(athlete_id=2, name="Multi Rider")
    save_athlete(athlete_data, athlete_id=2, tenant_id=0)

    update_athlete(2, {"weight_kg": 71.0})
    update_athlete(2, {"weight_kg": 73.0})
    update_athlete(2, {"ftp_watts": 260.0})

    history = get_athlete_history(2, limit=10)
    assert len(history) == 3

    values = [h["weight_kg"] for h in history]
    assert values == [73.0, 71.0, 70.0]

    timestamps = [h["recorded_at"] for h in history]
    assert timestamps == sorted(timestamps, reverse=True)


def test_history_snapshot_function(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_snapshot.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    init_db()

    athlete_data = _make_athlete_data(athlete_id=3, name="Snapshot Rider")
    save_athlete(athlete_data, athlete_id=3, tenant_id=0)

    snapshot_id = save_athlete_snapshot(athlete_data, tenant_id=0, changed_by=99)
    assert snapshot_id > 0

    history = get_athlete_history(3, limit=10)
    assert len(history) == 1
    assert history[0]["id"] == snapshot_id
    assert history[0]["athlete_id"] == 3
    assert history[0]["changed_by"] == 99
    assert history[0]["weight_kg"] == 70.0
    assert history[0]["ftp_watts"] == 250.0
    assert "password_hash" not in history[0]


def test_get_athlete_history_filters_by_tenant(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_tenant_history.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    init_db()

    athlete_data = _make_athlete_data(athlete_id=4, name="Tenant Rider")
    athlete_data["tenant_id"] = 10
    save_athlete(athlete_data, athlete_id=4, tenant_id=10)

    update_athlete(4, {"weight_kg": 75.0})

    history_all = get_athlete_history(4, limit=10)
    assert len(history_all) == 1, f"Expected 1 unfiltered history but got {len(history_all)}"

    history_filtered = get_athlete_history(4, tenant_id=10, limit=10)
    assert len(history_filtered) == 1, f"Expected 1 filtered history but got {len(history_filtered)}"
