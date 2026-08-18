"""PostgreSQL-backed persistence for OAuth tokens (Strava / Garmin / Wahoo).

When ``DATABASE_URL`` is configured (production on Render) OAuth tokens
must live on the managed PostgreSQL database, not on the ephemeral
container-local SQLite file. On SQLite (local / offline) the synchronous
layer in ``database.py`` is still the authoritative store; this module is
only ever invoked through the thin dispatch guards added at the top of the
``database.py`` functions.

The public function names mirror ``database.py`` 1:1 so the routes keep
importing the same symbols.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres

__all__ = [
    "save_strava_token",
    "get_strava_token",
    "revoke_strava_token",
    "update_strava_last_sync",
    "save_garmin_token",
    "get_garmin_token",
    "revoke_garmin_token",
    "save_wahoo_token",
    "get_wahoo_token",
    "revoke_wahoo_token",
]


def _ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS strava_tokens (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                athlete_name TEXT,
                created_at TEXT,
                updated_at TEXT,
                tenant_id INTEGER DEFAULT 0,
                last_sync_ts TEXT,
                UNIQUE(athlete_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_tokens (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                athlete_name TEXT,
                created_at TEXT,
                updated_at TEXT,
                tenant_id INTEGER DEFAULT 0,
                UNIQUE(athlete_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wahoo_tokens (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                athlete_name TEXT,
                created_at TEXT,
                updated_at TEXT,
                tenant_id INTEGER DEFAULT 0,
                UNIQUE(athlete_id)
            )
            """
        )
    conn.commit()


def _dict_from_row(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def save_strava_token(
    athlete_id: int,
    access_token: str,
    refresh_token: str,
    expires_at: int | None,
    scope: str | None,
    athlete_name: str | None,
    tenant_id: int = 0,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    now = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strava_tokens
                (athlete_id, access_token, refresh_token, expires_at, scope,
                 athlete_name, created_at, updated_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    scope = EXCLUDED.scope,
                    athlete_name = EXCLUDED.athlete_name,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                (
                    athlete_id,
                    access_token,
                    refresh_token,
                    expires_at,
                    scope,
                    athlete_name,
                    now,
                    now,
                    tenant_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_strava_token(athlete_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM strava_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            return _dict_from_row(cur.fetchone())
    finally:
        _safe_close(conn)


def revoke_strava_token(athlete_id: int) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM strava_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def update_strava_last_sync(athlete_id: int, ts: str) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE strava_tokens SET last_sync_ts = %s WHERE athlete_id = %s",
                (ts, athlete_id),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def save_garmin_token(
    athlete_id: int,
    access_token: str,
    refresh_token: str,
    expires_at: int | None,
    scope: str | None,
    athlete_name: str | None,
    tenant_id: int = 0,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    now = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO garmin_tokens
                (athlete_id, access_token, refresh_token, expires_at, scope,
                 athlete_name, created_at, updated_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    scope = EXCLUDED.scope,
                    athlete_name = EXCLUDED.athlete_name,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                (
                    athlete_id,
                    access_token,
                    refresh_token,
                    expires_at,
                    scope,
                    athlete_name,
                    now,
                    now,
                    tenant_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_garmin_token(athlete_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM garmin_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            return _dict_from_row(cur.fetchone())
    finally:
        _safe_close(conn)


def revoke_garmin_token(athlete_id: int) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM garmin_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def save_wahoo_token(
    athlete_id: int,
    access_token: str,
    refresh_token: str,
    expires_at: int | None,
    scope: str | None,
    athlete_name: str | None,
    tenant_id: int = 0,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    now = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO wahoo_tokens
                (athlete_id, access_token, refresh_token, expires_at, scope,
                 athlete_name, created_at, updated_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    scope = EXCLUDED.scope,
                    athlete_name = EXCLUDED.athlete_name,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                (
                    athlete_id,
                    access_token,
                    refresh_token,
                    expires_at,
                    scope,
                    athlete_name,
                    now,
                    now,
                    tenant_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_wahoo_token(athlete_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM wahoo_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            return _dict_from_row(cur.fetchone())
    finally:
        _safe_close(conn)


def revoke_wahoo_token(athlete_id: int) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM wahoo_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)
