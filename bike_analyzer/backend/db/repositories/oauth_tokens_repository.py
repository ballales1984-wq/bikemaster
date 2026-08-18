"""OAuth tokens repository — SQLite persistence for Strava, Garmin and Wahoo tokens."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def save_strava_token(athlete_id: int, access_token: str, refresh_token: str,
                      expires_at: int = 0, scope: str = "", athlete_name: str = "",
                      tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO strava_tokens (
                 athlete_id, access_token, refresh_token, expires_at, scope,
                 athlete_name, created_at, updated_at, tenant_id
             )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id) DO UPDATE SET
                   access_token=excluded.access_token,
                   refresh_token=excluded.refresh_token,
                   expires_at=excluded.expires_at,
                   scope=excluded.scope,
                   athlete_name=excluded.athlete_name,
                   updated_at=excluded.updated_at""",
            (athlete_id, access_token, refresh_token, expires_at, scope, athlete_name, now, now, tenant_id),
        )
        conn.commit()
        cur.execute("SELECT id FROM strava_tokens WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def get_strava_token(athlete_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM strava_tokens WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def revoke_strava_token(athlete_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM strava_tokens WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def update_strava_last_sync(athlete_id: int, ts: int) -> None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE strava_tokens SET last_sync_ts = ? WHERE athlete_id = ?", (ts, athlete_id))
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def save_garmin_token(athlete_id: int, access_token: str, refresh_token: str,
                      expires_at: int = 0, scope: str = "", athlete_name: str = "",
                      tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO garmin_tokens (
                 athlete_id, access_token, refresh_token, expires_at, scope,
                 athlete_name, created_at, updated_at, tenant_id
             )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id) DO UPDATE SET
                   access_token=excluded.access_token,
                   refresh_token=excluded.refresh_token,
                   expires_at=excluded.expires_at,
                   scope=excluded.scope,
                   athlete_name=excluded.athlete_name,
                   updated_at=excluded.updated_at""",
            (athlete_id, access_token, refresh_token, expires_at, scope, athlete_name, now, now, tenant_id),
        )
        conn.commit()
        cur.execute("SELECT id FROM garmin_tokens WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def get_garmin_token(athlete_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM garmin_tokens WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def revoke_garmin_token(athlete_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM garmin_tokens WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def save_wahoo_token(athlete_id: int, access_token: str, refresh_token: str,
                     expires_at: int = 0, scope: str = "", athlete_name: str = "",
                     tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO wahoo_tokens (
                 athlete_id, access_token, refresh_token, expires_at, scope,
                 athlete_name, created_at, updated_at, tenant_id
             )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id) DO UPDATE SET
                   access_token=excluded.access_token,
                   refresh_token=excluded.refresh_token,
                   expires_at=excluded.expires_at,
                   scope=excluded.scope,
                   athlete_name=excluded.athlete_name,
                   updated_at=excluded.updated_at""",
            (athlete_id, access_token, refresh_token, expires_at, scope, athlete_name, now, now, tenant_id),
        )
        conn.commit()
        cur.execute("SELECT id FROM wahoo_tokens WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def get_wahoo_token(athlete_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM wahoo_tokens WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_oauth_tokens")
def revoke_wahoo_token(athlete_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM wahoo_tokens WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0
