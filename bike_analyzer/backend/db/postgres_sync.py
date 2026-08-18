"""PostgreSQL-backed persistence for sync metadata tables.

Handles sync_entity_state, sync_settings, sync_conflicts when DATABASE_URL is configured.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..settings import get_settings
from .postgres_athlete import _connect, _safe_close, has_postgres

_s = get_settings()
logger = logging.getLogger(__name__)

__all__ = [
    "save_sync_entity_state",
    "get_sync_entity_state",
    "save_sync_setting",
    "get_sync_setting",
    "save_sync_conflict",
    "get_pending_sync_entities",
    "get_sync_conflicts",
    "resolve_sync_conflict",
]


def _ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_entity_state (
                id SERIAL PRIMARY KEY,
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
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id SERIAL PRIMARY KEY,
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
            )
            """
        )
    conn.commit()


def save_sync_entity_state(entity_type: str, entity_id: int, data: dict) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sync_entity_state (entity_type, entity_id, source, reliability_score,
                   last_modified, sync_status, sync_error, cloud_id, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                       source = excluded.source,
                       reliability_score = excluded.reliability_score,
                       last_modified = excluded.last_modified,
                       sync_status = excluded.sync_status,
                       sync_error = excluded.sync_error,
                       cloud_id = excluded.cloud_id,
                       updated_at = excluded.updated_at
                   RETURNING id""",
                (entity_type, entity_id,
                 data.get("source", "device"), data.get("reliability_score", 1.0),
                 data.get("last_modified", now), data.get("sync_status", "local"),
                 data.get("sync_error"), data.get("cloud_id"),
                 data.get("created_at", now), now),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_sync_entity_state(entity_type: str, entity_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sync_entity_state WHERE entity_type = %s AND entity_id = %s",
                (entity_type, entity_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def save_sync_setting(key: str, value: str) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sync_settings (key, value, updated_at)
                   VALUES (%s, %s, %s)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
                (key, value, now),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def get_sync_setting(key: str) -> str | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM sync_settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row["value"] if row else None
    finally:
        _safe_close(conn)


def save_sync_conflict(conflict: dict) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sync_conflicts (entity_type, entity_id, local_data, remote_data,
                   local_reliability, remote_reliability, local_modified, remote_modified,
                   resolution, resolved_data, resolution_reason, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (conflict.get("entity_type"), conflict.get("entity_id"),
                 conflict.get("local_data", "{}"), conflict.get("remote_data", "{}"),
                 conflict.get("local_reliability", 1.0), conflict.get("remote_reliability", 1.0),
                 conflict.get("local_modified", now), conflict.get("remote_modified", now),
                 conflict.get("resolution", "unresolved"), conflict.get("resolved_data"),
                 conflict.get("resolution_reason"), now, now),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_pending_sync_entities(entity_type: str | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if entity_type:
                cur.execute(
                    "SELECT * FROM sync_entity_state WHERE entity_type = %s AND sync_status IN ('pending', 'local')",
                    (entity_type,),
                )
            else:
                cur.execute(
                    "SELECT * FROM sync_entity_state WHERE sync_status IN ('pending', 'local')"
                )
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def get_sync_conflicts(unresolved_only: bool = True) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if unresolved_only:
                cur.execute("SELECT * FROM sync_conflicts WHERE resolution = 'unresolved'")
            else:
                cur.execute("SELECT * FROM sync_conflicts")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def resolve_sync_conflict(conflict_id: int, resolution: str, resolved_data: str, reason: str) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE sync_conflicts
                SET resolution = %s, resolved_data = %s, resolution_reason = %s, updated_at = %s
                WHERE id = %s""",
                (resolution, resolved_data, reason, now, conflict_id),
            )
            conn.commit()
    finally:
        _safe_close(conn)

