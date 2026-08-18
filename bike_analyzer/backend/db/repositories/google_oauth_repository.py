"""Google OAuth repository — SQLite persistence for Google OAuth tokens."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_google_oauth")
def save_google_token(athlete_id: int, provider: str, access_token: str,
                      refresh_token: str, expires_at: int = 0, scope: str = "") -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO google_tokens (
                 athlete_id, provider, access_token, refresh_token, expires_at,
                 scope, created_at, updated_at
             )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id, provider) DO UPDATE SET
                   access_token=excluded.access_token,
                   refresh_token=excluded.refresh_token,
                   expires_at=excluded.expires_at,
                   scope=excluded.scope,
                   updated_at=excluded.updated_at""",
            (athlete_id, provider, access_token, refresh_token, expires_at, scope, now, now),
        )
        conn.commit()
        cur.execute("SELECT id FROM google_tokens WHERE athlete_id = ? AND provider = ?", (athlete_id, provider))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_google_oauth")
def get_google_token(athlete_id: int, provider: str) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM google_tokens WHERE athlete_id = ? AND provider = ?",
            (athlete_id, provider),
        )
        row = cur.fetchone()
        return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_google_oauth")
def delete_google_token(athlete_id: int, provider: str) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM google_tokens WHERE athlete_id = ? AND provider = ?", (athlete_id, provider))
        conn.commit()
        return cur.rowcount > 0
