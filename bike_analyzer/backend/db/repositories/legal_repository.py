"""Legal repository — SQLite persistence for consent, legal acceptances and AI audit logs."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def save_consent(
    athlete_id: int,
    consent_type: str,
    granted: bool = True,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_consent (athlete_id, tenant_id, consent_type, granted, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id, consent_type) DO UPDATE SET
                   granted=excluded.granted,
                   source=excluded.source,
                   updated_at=excluded.updated_at""",
            (athlete_id, tenant_id, consent_type, 1 if granted else 0, source, now, now),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def get_consent(athlete_id: int, consent_type: str) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_consent WHERE athlete_id = ? AND consent_type = ?",
            (athlete_id, consent_type),
        )
        row = cur.fetchone()
    return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def get_consents_by_athlete(athlete_id: int) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_consent WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def save_legal_acceptance(
    athlete_id: int,
    acceptance_type: str,
    version: str,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO legal_acceptances (athlete_id, tenant_id, acceptance_type, version, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (athlete_id, tenant_id, acceptance_type, version, source, now),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def get_legal_acceptances_by_athlete(athlete_id: int) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM legal_acceptances WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def has_accepted_version(athlete_id: int, acceptance_type: str, min_version: str) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT version FROM legal_acceptances "
            "WHERE athlete_id = ? AND acceptance_type = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (athlete_id, acceptance_type),
        )
        row = cur.fetchone()
    if not row:
        return False
    accepted = str(row[0])
    return accepted >= min_version


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
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
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ai_audit_log
               (athlete_id, tenant_id, provider, model, prompt_hash,
                response_length, tool_calls, latency_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, tenant_id, provider, model, prompt_hash, response_length, tool_calls, latency_ms, now),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_legal")
def get_ai_audit_logs_by_athlete(athlete_id: int, limit: int = 100) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_audit_log WHERE athlete_id = ? ORDER BY created_at DESC LIMIT ?",
            (athlete_id, limit),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]
