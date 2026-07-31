"""Android Health Connect integration for BikeMaster.

Provides:
- Connection management (connect/disconnect)
- Permission handling
- Data sync from Android Health Connect
"""

from __future__ import annotations

import logging
import sqlite3
import time

from ..settings import get_settings

_s = get_settings()

logger = logging.getLogger(__name__)

HEALTH_CONNECT_PERMISSIONS = [
    "weight",
    "height",
    "heart_rate",
    "steps",
    "sleep",
    "blood_pressure",
    "activity",
]


def _get_conn():
    from ..db.database import get_db_connection

    return get_db_connection()


def ensure_health_connect_table() -> None:
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS health_connect_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                connected INTEGER NOT NULL DEFAULT 1,
                permissions TEXT DEFAULT '[]',
                last_sync_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(athlete_id)
            )
            """
        )


def connect(athlete_id: int) -> dict:
    ensure_health_connect_table()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO health_connect_tokens (athlete_id, connected, permissions)
            VALUES (?, 1, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                connected = 1,
                permissions = excluded.permissions,
                updated_at = datetime('now')
            """,
            (athlete_id, str(HEALTH_CONNECT_PERMISSIONS)),
        )
    return {
        "status": "connected",
        "permissions": HEALTH_CONNECT_PERMISSIONS,
    }


def disconnect(athlete_id: int) -> None:
    ensure_health_connect_table()
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM health_connect_tokens WHERE athlete_id = ?",
            (athlete_id,),
        )


def get_health_connect_token(athlete_id: int) -> dict | None:
    ensure_health_connect_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT connected, permissions, last_sync_at "
            "FROM health_connect_tokens WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "connected": bool(row[0]),
        "permissions": row[1],
        "last_sync_at": row[2],
    }


def sync_health_data(athlete_id: int, metrics: list[dict] | None = None, tenant_id: int = 0) -> dict:
    token = get_health_connect_token(athlete_id)
    if not token or not token.get("connected"):
        return {"synced": 0, "connected": False}
    ensure_health_connect_table()
    now = time.time()
    synced = 0
    if metrics:
        from ..db.database import log_athlete_metric

        tid = tenant_id or athlete_id
        for m in metrics:
            metric_id = log_athlete_metric(
                athlete_id=athlete_id,
                tenant_id=tid,
                metric_type=m.get("metric_type"),
                value=m.get("value"),
                unit=m.get("unit"),
                note=m.get("source"),
                source=m.get("source", "health_connect"),
                recorded_at=m.get("recorded_at"),
            )
            if metric_id:
                synced += 1
    with _get_conn() as conn:
        conn.execute(
            "UPDATE health_connect_tokens SET last_sync_at = ?, updated_at = datetime('now') WHERE athlete_id = ?",
            (now, athlete_id),
        )
    logger.info("Health Connect sync for athlete %s: %d metrics stored", athlete_id, synced)
    return {"synced": synced, "connected": True}