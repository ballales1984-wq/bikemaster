"""Android Health Connect integration for BikeMaster.

Provides:
- Connection management (connect/disconnect)
- Permission handling
- Data sync from Android Health Connect
"""

from __future__ import annotations

import logging
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
    from ..db.database import connect_health_connect

    return connect_health_connect(athlete_id, permissions=",".join(HEALTH_CONNECT_PERMISSIONS))


def disconnect(athlete_id: int) -> None:
    from ..db.database import disconnect_health_connect

    disconnect_health_connect(athlete_id)


def get_health_connect_token(athlete_id: int) -> dict | None:
    from ..db.database import get_health_connect_token

    return get_health_connect_token(athlete_id)


def sync_health_data(athlete_id: int, metrics: list[dict] | None = None, tenant_id: int = 0) -> dict:
    token = get_health_connect_token(athlete_id)
    if not token or not token.get("connected"):
        return {"synced": 0, "connected": False}
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
    from ..db.database import update_health_connect_sync
    update_health_connect_sync(athlete_id, str(now))
    logger.info("Health Connect sync for athlete %s: %d metrics stored", athlete_id, synced)
    return {"synced": synced, "connected": True}