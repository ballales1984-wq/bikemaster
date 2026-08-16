"""PostgreSQL-backed persistence for consent, legal acceptances, and AI audit logs."""

from __future__ import annotations

from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_legal_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_consent (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                consent_type TEXT NOT NULL,
                granted BOOLEAN DEFAULT TRUE,
                source TEXT NOT NULL DEFAULT 'web',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(athlete_id, consent_type)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_acceptances (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                acceptance_type TEXT NOT NULL,
                version TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'web',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_audit_log (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                response_length INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_ai_audit_log_athlete_id
            ON ai_audit_log(athlete_id)
            """
        )
        cur.execute(
            """
            ALTER TABLE user_consent
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        cur.execute(
            """
            ALTER TABLE legal_acceptances
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        conn.commit()


def save_consent(
    athlete_id: int,
    consent_type: str,
    granted: bool = True,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_consent (athlete_id, tenant_id, consent_type, granted, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id, consent_type) DO UPDATE SET
                    granted = excluded.granted,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (athlete_id, tenant_id, consent_type, granted, source, now, now),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def get_consent(athlete_id: int, consent_type: str) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM user_consent WHERE athlete_id = %s AND consent_type = %s",
                (athlete_id, consent_type),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def get_consents_by_athlete(athlete_id: int) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM user_consent WHERE athlete_id = %s", (athlete_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def save_legal_acceptance(
    athlete_id: int,
    acceptance_type: str,
    version: str,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO legal_acceptances (athlete_id, tenant_id, acceptance_type, version, source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (athlete_id, tenant_id, acceptance_type, version, source, now),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def get_legal_acceptances_by_athlete(athlete_id: int) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM legal_acceptances WHERE athlete_id = %s", (athlete_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def has_accepted_version(athlete_id: int, acceptance_type: str, min_version: str) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version FROM legal_acceptances "
                "WHERE athlete_id = %s AND acceptance_type = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (athlete_id, acceptance_type),
            )
            row = cur.fetchone()
        if not row:
            return False
        accepted = str(row["version"])
        return accepted >= min_version
    finally:
        _safe_close(conn)


def save_ai_audit_log(
    athlete_id: int,
    provider: str,
    model: str,
    prompt_hash: str,
    response_length: int = 0,
    tool_calls: int = 0,
    latency_ms: int = 0,
    tenant_id: int = 0,
) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_audit_log
                (athlete_id, tenant_id, provider, model, prompt_hash,
                 response_length, tool_calls, latency_ms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (athlete_id, tenant_id, provider, model, prompt_hash, response_length, tool_calls, latency_ms, now),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def get_ai_audit_logs_by_athlete(athlete_id: int, limit: int = 100) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_legal_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ai_audit_log WHERE athlete_id = %s ORDER BY created_at DESC LIMIT %s",
                (athlete_id, limit),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)
