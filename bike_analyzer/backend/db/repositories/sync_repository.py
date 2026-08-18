"""Sync repository — SQLite persistence for sync metadata, entity state and conflicts."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _row_to_sync_entity_state(row: tuple) -> dict:
    cols = (
        [d[0] for d in row.cursor_description]
        if hasattr(row, "cursor_description")
        else [
            "id",
            "entity_type",
            "entity_id",
            "source",
            "reliability_score",
            "last_modified",
            "sync_status",
            "sync_error",
            "cloud_id",
            "created_at",
            "updated_at",
        ]
    )
    data = dict(zip(cols, row, strict=False))
    return {
        "id": data.get("id"),
        "entity_type": data.get("entity_type"),
        "entity_id": data.get("entity_id"),
        "source": data.get("source", "device"),
        "reliability_score": data.get("reliability_score", 1.0),
        "last_modified": data.get("last_modified"),
        "sync_status": data.get("sync_status", "local"),
        "sync_error": data.get("sync_error"),
        "cloud_id": data.get("cloud_id"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def save_sync_entity_state(entity_type: str, entity_id: int, data: dict) -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sync_entity_state (entity_type, entity_id, source, reliability_score,
               last_modified, sync_status, sync_error, cloud_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                   source = excluded.source,
                   reliability_score = excluded.reliability_score,
                   last_modified = excluded.last_modified,
                   sync_status = excluded.sync_status,
                   sync_error = excluded.sync_error,
                   cloud_id = excluded.cloud_id,
                   updated_at = excluded.updated_at""",
            (entity_type, entity_id,
             data.get("source", "device"), data.get("reliability_score", 1.0),
             data.get("last_modified", now), data.get("sync_status", "local"),
             data.get("sync_error"), data.get("cloud_id"),
             data.get("created_at", now), now),
        )
        conn.commit()
        cur.execute("SELECT id FROM sync_entity_state WHERE entity_type = ? AND entity_id = ?",
                    (entity_type, entity_id))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def get_sync_entity_state(entity_type: str, entity_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM sync_entity_state WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def save_sync_setting(key: str, value: str) -> None:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sync_settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value, now),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def get_sync_setting(key: str) -> str | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM sync_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def save_sync_conflict(conflict: dict) -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sync_conflicts (entity_type, entity_id, local_data, remote_data,
               local_reliability, remote_reliability, local_modified, remote_modified,
               resolution, resolved_data, resolution_reason, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conflict.get("entity_type"), conflict.get("entity_id"),
             conflict.get("local_data", "{}"), conflict.get("remote_data", "{}"),
             conflict.get("local_reliability", 1.0), conflict.get("remote_reliability", 1.0),
             conflict.get("local_modified", now), conflict.get("remote_modified", now),
             conflict.get("resolution", "unresolved"), conflict.get("resolved_data"),
             conflict.get("resolution_reason"), now, now),
        )
        conn.commit()
        cur.execute("SELECT id FROM sync_conflicts WHERE entity_type = ? AND entity_id = ? AND created_at = ?",
                    (conflict.get("entity_type"), conflict.get("entity_id"), now))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def get_pending_sync_entities(entity_type: str | None = None) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if entity_type:
            cur.execute(
                "SELECT * FROM sync_entity_state WHERE entity_type = ? AND sync_status IN ('pending', 'local')",
                (entity_type,),
            )
        else:
            cur.execute(
                "SELECT * FROM sync_entity_state WHERE sync_status IN ('pending', 'local')"
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def get_sync_conflicts(unresolved_only: bool = True) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if unresolved_only:
            cur.execute("SELECT * FROM sync_conflicts WHERE resolution = 'unresolved'")
        else:
            cur.execute("SELECT * FROM sync_conflicts")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_sync")
def resolve_sync_conflict(conflict_id: int, resolution: str, resolved_data: str, reason: str) -> None:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE sync_conflicts
            SET resolution = ?, resolved_data = ?, resolution_reason = ?, updated_at = ?
            WHERE id = ?""",
            (resolution, resolved_data, reason, now, conflict_id),
        )
        conn.commit()
