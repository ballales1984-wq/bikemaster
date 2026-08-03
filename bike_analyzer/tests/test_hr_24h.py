"""Tests for 24-hour heart-rate tracking (independent of Google Health/Fit)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bike_analyzer.backend.db import database as db_module
from bike_analyzer.backend.db.database import (
    delete_hr_samples,
    delete_hr_settings,
    get_hr_24h_samples,
    get_hr_daily_summary,
    get_hr_settings,
    init_db,
    log_hr_sample,
    log_hr_samples,
    upsert_hr_settings,
)


UTC = timezone.utc


def _ensure_athlete(athlete_id: int) -> None:
    with db_module.get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO athletes (id, name) VALUES (?, ?)",
            (athlete_id, f"Athlete {athlete_id}"),
        )
        conn.commit()


def _setup(tmp_path, monkeypatch, athlete_id: int) -> None:
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / f"hr_{athlete_id}.db"))
    init_db()
    _ensure_athlete(athlete_id)


def _log_sample(athlete_id: int, hr: int, minutes_ago: int = 0, source: str = "ble", device_id: str | None = None):
    recorded = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    return log_hr_sample(
        athlete_id,
        hr,
        source=source,
        device_id=device_id,
        recorded_at=recorded,
    )


def test_log_and_retrieve_single_sample(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=1)

    sample_id = _log_sample(athlete_id=1, hr=120, minutes_ago=1)
    assert sample_id > 0

    samples = get_hr_24h_samples(athlete_id=1, hours=24)
    assert len(samples) == 1
    assert samples[0]["heart_rate"] == 120
    assert samples[0]["source"] == "ble"


def test_bulk_insert_filters_invalid(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=2)

    samples = [
        {"heart_rate": 100, "recorded_at": datetime.now(UTC).isoformat()},
        {"heart_rate": -5, "recorded_at": datetime.now(UTC).isoformat()},  # invalid
        {"heart_rate": 400, "recorded_at": datetime.now(UTC).isoformat()},  # invalid
        {"heart_rate": 85, "recorded_at": datetime.now(UTC).isoformat(), "source": "manual"},
    ]
    saved = log_hr_samples(athlete_id=2, samples=samples, source="ble")
    assert saved == 2


def test_24h_samples_ordered_oldest_first(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=3)

    _log_sample(athlete_id=3, hr=90, minutes_ago=5)
    _log_sample(athlete_id=3, hr=110, minutes_ago=3)
    _log_sample(athlete_id=3, hr=130, minutes_ago=1)

    samples = get_hr_24h_samples(athlete_id=3, hours=24)
    assert [s["heart_rate"] for s in samples] == [90, 110, 130]
    assert samples[0]["recorded_at"] < samples[-1]["recorded_at"]


def test_24h_window_filters_old_samples(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=4)

    old = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    log_hr_sample(athlete_id=4, heart_rate=70, recorded_at=old)
    _log_sample(athlete_id=4, hr=80, minutes_ago=2)

    samples = get_hr_24h_samples(athlete_id=4, hours=24)
    assert len(samples) == 1
    assert samples[0]["heart_rate"] == 80


def test_daily_summary_aggregates(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=5)

    base = datetime.now(UTC)
    log_hr_sample(athlete_id=5, heart_rate=60, recorded_at=base.isoformat())
    log_hr_sample(athlete_id=5, heart_rate=100, recorded_at=base.isoformat())
    log_hr_sample(athlete_id=5, heart_rate=140, recorded_at=base.isoformat())

    summary = get_hr_daily_summary(athlete_id=5, days=1)
    assert len(summary) == 1
    day0 = summary[0]
    assert day0["resting_hr"] == 60
    assert day0["max_hr"] == 140
    assert day0["sample_count"] == 3


def test_settings_upsert_and_retrieve(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=6)

    result = upsert_hr_settings(
        athlete_id=6,
        settings={"enabled": True, "interval_seconds": 15, "max_hr": 180},
    )
    assert bool(result["enabled"]) is True
    assert result["interval_seconds"] == 15
    assert result["max_hr"] == 180

    result2 = upsert_hr_settings(
        athlete_id=6,
        settings={"resting_hr": 55, "device_id": "AA:BB:CC:DD:EE:FF"},
    )
    assert result2["resting_hr"] == 55
    assert result2["device_id"] == "AA:BB:CC:DD:EE:FF"
    assert result2["interval_seconds"] == 15  # preserved from first upsert
    assert result2["max_hr"] == 180

    fetched = get_hr_settings(athlete_id=6)
    assert fetched is not None
    assert bool(fetched["enabled"]) is True
    assert fetched["resting_hr"] == 55


def test_settings_delete_and_recreate(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=7)

    upsert_hr_settings(athlete_id=7, settings={"enabled": True})
    assert get_hr_settings(athlete_id=7) is not None

    deleted = delete_hr_settings(athlete_id=7)
    assert deleted is True
    assert get_hr_settings(athlete_id=7) is None

    upsert_hr_settings(athlete_id=7, settings={"enabled": False})
    recreated = get_hr_settings(athlete_id=7)
    assert recreated is not None
    assert bool(recreated["enabled"]) is False


def test_delete_samples_removes_all(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=8)

    _log_sample(athlete_id=8, hr=100, minutes_ago=10)
    _log_sample(athlete_id=8, hr=110, minutes_ago=5)
    assert len(get_hr_24h_samples(athlete_id=8, hours=24)) == 2

    deleted = delete_hr_samples(athlete_id=8)
    assert deleted == 2
    assert len(get_hr_24h_samples(athlete_id=8, hours=24)) == 0


def test_delete_samples_older_than(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=9)

    old = (datetime.now(UTC) - timedelta(hours=26)).isoformat()
    log_hr_sample(athlete_id=9, heart_rate=90, recorded_at=old)
    _log_sample(athlete_id=9, hr=120, minutes_ago=3)

    deleted = delete_hr_samples(
        athlete_id=9, older_than=(datetime.now(UTC) - timedelta(hours=24)).isoformat()
    )
    assert deleted == 1
    remaining = get_hr_24h_samples(athlete_id=9, hours=48)
    assert len(remaining) == 1
    assert remaining[0]["heart_rate"] == 120


def test_invalid_heart_rate_rejected(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, athlete_id=10)

    assert log_hr_sample(athlete_id=10, heart_rate=0) == 0
    assert log_hr_sample(athlete_id=10, heart_rate=301) == 0
    assert len(get_hr_24h_samples(athlete_id=10, hours=24)) == 0
