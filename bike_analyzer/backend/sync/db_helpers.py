"""SQLite helpers for sync metadata tables."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..utils.logger import get_logger
from .models import ConflictRecord, SyncEntityState, SyncStatus

logger = get_logger(__name__)


def ensure_sync_tables() -> None:
    """Create sync metadata tables if they do not exist."""
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sync_entity_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                source TEXT DEFAULT 'device',
                reliability_score REAL DEFAULT 1.0,
                last_modified TEXT NOT NULL,
                sync_status TEXT DEFAULT 'local',
                sync_error TEXT,
                cloud_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(entity_type, entity_id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sync_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                local_data TEXT NOT NULL,
                remote_data TEXT NOT NULL,
                local_reliability REAL NOT NULL,
                remote_reliability REAL NOT NULL,
                local_modified TEXT NOT NULL,
                remote_modified TEXT NOT NULL,
                resolution TEXT DEFAULT 'unresolved',
                resolved_data TEXT,
                resolution_reason TEXT,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sync_entity_state_type ON sync_entity_state(entity_type, sync_status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sync_conflicts_resolution ON sync_conflicts(resolution)"
        )
        conn.commit()


def get_entity_state(entity_type: str, entity_id: int) -> SyncEntityState | None:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM sync_entity_state WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_state(row)


def upsert_entity_state(state: SyncEntityState) -> None:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO sync_entity_state
            (entity_type, entity_id, source, reliability_score, last_modified,
             sync_status, sync_error, cloud_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.entity_type,
                state.entity_id,
                state.source,
                state.reliability_score,
                state.last_modified,
                state.sync_status.value,
                state.sync_error,
                state.cloud_id,
                state.created_at,
                state.updated_at,
            ),
        )
        conn.commit()


def mark_synced(entity_type: str, entity_id: int, cloud_id: str | None = None) -> None:
    state = get_entity_state(entity_type, entity_id)
    if state is None:
        state = SyncEntityState(
            entity_type=entity_type,
            entity_id=entity_id,
            sync_status=SyncStatus.SYNCED,
        )
    else:
        state.sync_status = SyncStatus.SYNCED
        state.sync_error = None
    if cloud_id is not None:
        state.cloud_id = cloud_id
    state.updated_at = datetime.now(UTC).isoformat()
    upsert_entity_state(state)


def mark_pending(entity_type: str, entity_id: int) -> None:
    state = get_entity_state(entity_type, entity_id)
    if state is None:
        state = SyncEntityState(
            entity_type=entity_type,
            entity_id=entity_id,
            sync_status=SyncStatus.PENDING,
        )
    else:
        state.sync_status = SyncStatus.PENDING
    state.updated_at = datetime.now(UTC).isoformat()
    upsert_entity_state(state)


def mark_conflict(entity_type: str, entity_id: int, error: str) -> None:
    state = get_entity_state(entity_type, entity_id)
    if state is None:
        state = SyncEntityState(
            entity_type=entity_type,
            entity_id=entity_id,
            sync_status=SyncStatus.CONFLICT,
            sync_error=error,
        )
    else:
        state.sync_status = SyncStatus.CONFLICT
        state.sync_error = error
    state.updated_at = datetime.now(UTC).isoformat()
    upsert_entity_state(state)


def mark_error(entity_type: str, entity_id: int, error: str) -> None:
    state = get_entity_state(entity_type, entity_id)
    if state is None:
        state = SyncEntityState(
            entity_type=entity_type,
            entity_id=entity_id,
            sync_status=SyncStatus.ERROR,
            sync_error=error,
        )
    else:
        state.sync_status = SyncStatus.ERROR
        state.sync_error = error
    state.updated_at = datetime.now(UTC).isoformat()
    upsert_entity_state(state)


def get_pending_entities(entity_type: str | None = None) -> list[SyncEntityState]:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
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
        return [_row_to_state(r) for r in rows]


def get_conflicts(unresolved_only: bool = True) -> list[ConflictRecord]:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        if unresolved_only:
            cur.execute("SELECT * FROM sync_conflicts WHERE resolution = 'unresolved'")
        else:
            cur.execute("SELECT * FROM sync_conflicts")
        rows = cur.fetchall()
        return [_row_to_conflict(r) for r in rows]


def save_conflict(conflict: ConflictRecord) -> int:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        now = datetime.now(UTC).isoformat()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sync_conflicts
            (entity_type, entity_id, local_data, remote_data,
             local_reliability, remote_reliability,
             local_modified, remote_modified, resolution, resolved_data, resolution_reason, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conflict.entity_type,
                conflict.entity_id,
                json.dumps(conflict.local_data),
                json.dumps(conflict.remote_data),
                conflict.local_reliability,
                conflict.remote_reliability,
                conflict.local_modified,
                conflict.remote_modified,
                conflict.resolution,
                json.dumps(conflict.resolved_data) if conflict.resolved_data else None,
                conflict.resolution_reason,
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid


def resolve_conflict_db(conflict_id: int, resolution: str, resolved_data: dict[str, Any], reason: str) -> None:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """UPDATE sync_conflicts
            SET resolution = ?, resolved_data = ?, resolution_reason = ?, updated_at = ?
            WHERE id = ?""",
            (resolution, json.dumps(resolved_data), reason, now, conflict_id),
        )
        conn.commit()


def get_last_sync_ts() -> str | None:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT value FROM sync_settings WHERE key = 'last_sync_ts'"
        )
        row = cur.fetchone()
        return row["value"] if row else None


def set_last_sync_ts(ts: str) -> None:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO sync_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("last_sync_ts", ts, now),
        )
        conn.commit()


def _row_to_state(row) -> SyncEntityState:
    return SyncEntityState(
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        source=row["source"] or "device",
        reliability_score=float(row["reliability_score"] or 1.0),
        last_modified=row["last_modified"],
        sync_status=SyncStatus(row["sync_status"] or "local"),
        sync_error=row["sync_error"],
        cloud_id=row["cloud_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_conflict(row) -> ConflictRecord:
    local_data: dict[str, Any] = {}
    remote_data: dict[str, Any] = {}
    resolved_data: dict[str, Any] | None = None
    try:
        local_data = json.loads(row["local_data"]) if row["local_data"] else {}
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        remote_data = json.loads(row["remote_data"]) if row["remote_data"] else {}
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        resolved_data = json.loads(row["resolved_data"]) if row["resolved_data"] else None
    except (json.JSONDecodeError, TypeError):
        pass
    return ConflictRecord(
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        local_data=local_data,
        remote_data=remote_data,
        local_reliability=float(row["local_reliability"] or 1.0),
        remote_reliability=float(row["remote_reliability"] or 1.0),
        local_modified=row["local_modified"],
        remote_modified=row["remote_modified"],
        resolution=row["resolution"] or "unresolved",
        resolved_data=resolved_data,
        resolution_reason=row["resolution_reason"] or "",
    )


__all__ = [
    "ensure_sync_tables",
    "get_entity_state",
    "upsert_entity_state",
    "mark_synced",
    "mark_pending",
    "mark_conflict",
    "mark_error",
    "get_pending_entities",
    "get_conflicts",
    "save_conflict",
    "resolve_conflict_db",
    "get_last_sync_ts",
    "set_last_sync_ts",
]
