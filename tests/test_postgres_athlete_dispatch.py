"""Tests for the PostgreSQL dispatch layer in db/postgres_athlete.py.

These tests exercise the sync PostgreSQL code path *without* a real database by
mocking ``psycopg2`` at the ``_connect`` boundary. They assert that:

* ``has_postgres()`` flips the dispatch on when ``DATABASE_URL`` is set.
* Each ``database.py`` function delegates to its PostgreSQL twin.
* The generated SQL (INSERT/UPDATE/SELECT/RETURNING) and return shapes match
  the SQLite implementation, so the two stores stay swap-compatible.

No network and no psycopg2 driver are required: ``postgres_athlete._connect``
is replaced with a factory returning a :class:`MagicMock` backed cursor.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

import bike_analyzer.backend.db.database as db
from bike_analyzer.backend.db import postgres_athlete as pa


def _pg_url():
    os.environ["DATABASE_URL"] = "postgresql://u:p@db.internal:5432/bikemaster"


def _clear_pg_url():
    os.environ.pop("DATABASE_URL", None)


def _mock_conn():
    conn = MagicMock(name="pg-conn")
    cur = MagicMock(name="pg-cur")
    cm = conn.cursor.return_value
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    all_cols = set(
        pa._INSERT_COLS + pa._UPDATE_COLS + pa._SNAPSHOT_COLS + pa._LOG_COLS + ["id", "user_id"]
    )
    cur.fetchall.return_value = [{"column_name": c} for c in all_cols]
    return conn, cur


@pytest.fixture(autouse=True)
def _pg_env():
    _pg_url()
    pa._EXISTING_COLUMNS_CACHE.clear()
    yield
    _clear_pg_url()


def test_has_postgres_true_when_url_set():
    assert pa.has_postgres() is True
    assert db.get_athlete.__module__.endswith("database")  # still the dispatch wrapper


def test_get_athlete_pg_returns_row(monkeypatch):
    _pg_url()
    existing = {"id": 1, "name": "PgRider", "weight_kg": 72.0, "tenant_id": 0}
    conn, cur = _mock_conn()
    cur.fetchone.return_value = existing
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    result = db.get_athlete(1)

    assert result == existing
    sent = cur.execute.call_args.args[0]
    assert "SELECT * FROM athletes WHERE id=%s" in str(sent)


def test_get_athlete_pg_not_found(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    assert db.get_athlete(999) is None


def test_save_athlete_pg_inserts_new(monkeypatch):
    conn, cur = _mock_conn()
    # Only the INSERT ... RETURNING call fetches once (athlete_id=None -> no get_athlete check).
    cur.fetchone.return_value = {"id": 42}
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    new_id = db.save_athlete({"name": "NewRider"}, athlete_id=None, tenant_id=0)

    assert new_id == 42
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("INSERT INTO athletes" in s and "RETURNING id" in s for s in sqls)


def test_save_athlete_pg_upserts_existing(monkeypatch):
    conn, cur = _mock_conn()
    existing = {"id": 7, "name": "Old", "tenant_id": 0, "weight_kg": 90.0}
    cur.fetchone.return_value = existing  # get_athlete finds the row
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    updated_id = db.save_athlete({"name": "New", "weight_kg": 80.0}, athlete_id=7, tenant_id=0)

    assert updated_id == 7
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("UPDATE athletes SET" in s and "WHERE id=%s" in s for s in sqls)
    assert not any("INSERT INTO athletes" in s for s in sqls)


def test_save_athlete_pg_upsert_preserves_existing_fields(monkeypatch):
    """Partial upsert must not reset fields absent from the incoming dict."""
    conn, cur = _mock_conn()
    existing = {"id": 7, "name": "Old", "tenant_id": 0, "weight_kg": 90.0,
                "experience_level": "Intermediate"}
    cur.fetchone.return_value = existing  # get_athlete finds the row
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    db.save_athlete({"name": "New"}, athlete_id=7, tenant_id=0)

    update_call = [c for c in cur.execute.call_args_list if "UPDATE athletes" in str(c.args[0])]
    assert update_call
    params = update_call[0].args[1]
    cols = pa._UPDATE_COLS
    assert params[cols.index("weight_kg")] == 90.0  # preserved, not reset to 70
    assert params[cols.index("name")] == "New"
    assert params[cols.index("experience_level")] == "Intermediate"


def test_update_athlete_pg_returns_true_and_updates(monkeypatch):
    conn, cur = _mock_conn()
    cur.rowcount = 1
    existing = {"id": 1, "name": "Old", "tenant_id": 0, "weight_kg": 70.0}
    # get_athlete (in update_athlete) -> existing; save_athlete_snapshot INSERT -> {"id":9}
    cur.fetchone.side_effect = [existing, {"id": 9}]
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    ok = db.update_athlete(1, {"weight_kg": 80.0})

    assert ok is True
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("UPDATE athletes SET" in s and "WHERE id=%s" in s for s in sqls)
    assert any("INSERT INTO athlete_history" in s for s in sqls)


def test_update_athlete_pg_missing_returns_false(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None  # athlete missing
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    assert db.update_athlete(4242, {"name": "Ghost"}) is False
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert not any("UPDATE athletes" in s for s in sqls)


def test_log_athlete_metric_pg_returns_id(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 99}
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    mid = db.log_athlete_metric(1, "weight_kg", 74.5, unit="kg", tenant_id=0)

    assert mid == 99
    sent = str(cur.execute.call_args.args[0])
    assert "INSERT INTO athlete_metric_log" in sent
    params = cur.execute.call_args.args[1]
    assert params[0] == 1 and params[1] == 0 and params[2] == "weight_kg"


def test_get_athlete_metric_log_pg_returns_series(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchall.return_value = [
        {"id": 1, "value": 70.0, "unit": "kg", "note": None, "source": "manual",
         "recorded_at": "2026-01-01T00:00:00+00:00"},
        {"id": 2, "value": 72.0, "unit": "kg", "note": None, "source": "manual",
         "recorded_at": "2026-01-02T00:00:00+00:00"},
    ]
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    series = db.get_athlete_metric_log(1, "weight_kg", tenant_id=0)

    assert len(series) == 2
    assert series[0]["value"] == 70.0
    sent = str(cur.execute.call_args.args[0])
    assert "SELECT id, value, unit, note, source, recorded_at" in sent
    assert "WHERE athlete_id=%s AND metric_type=%s" in sent


def test_save_athlete_snapshot_pg_returns_id(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 5}
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    snapshot_id = db.save_athlete_snapshot({"id": 1, "name": "Rider"}, tenant_id=0)

    assert snapshot_id == 5
    sent = str(cur.execute.call_args.args[0])
    assert "INSERT INTO athlete_history" in sent
    assert "RETURNING id" in sent


def test_get_athlete_history_pg_returns_list(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchall.return_value = [{"id": 1, "athlete_id": 1, "name": "Rider"}]
    monkeypatch.setattr(pa, "_connect", lambda: conn)

    history = db.get_athlete_history(1, tenant_id=0)

    assert history == [{"id": 1, "athlete_id": 1, "name": "Rider"}]
    sent = str(cur.execute.call_args.args[0])
    assert "SELECT * FROM athlete_history WHERE athlete_id=%s AND tenant_id=%s" in sent
