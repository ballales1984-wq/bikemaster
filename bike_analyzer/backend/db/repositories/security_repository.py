"""Security repository — SQLite persistence for revoked JWT tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_security")
def revoke_token(jti: str, ttl: int = 7200) -> None:
    now = datetime.now(UTC).isoformat()
    expires_at = (datetime.now(UTC) + timedelta(seconds=ttl)).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO revoked_tokens (jti, revoked_at, expires_at)
               VALUES (?, ?, ?)
               ON CONFLICT(jti) DO UPDATE SET revoked_at = excluded.revoked_at""",
            (jti, now, expires_at),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_security")
def is_token_revoked(jti: str) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT expires_at FROM revoked_tokens WHERE jti = ?", (jti,))
        row = cur.fetchone()
        if not row:
            return False
        expires_at = datetime.fromisoformat(row[0])
        return datetime.now(UTC) < expires_at


@pg_dispatch("bike_analyzer.backend.db.postgres_security")
def sweep_revoked_tokens() -> None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (datetime.now(UTC).isoformat(),))
        conn.commit()
