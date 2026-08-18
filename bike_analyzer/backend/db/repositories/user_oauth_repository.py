"""User OAuth repository — SQLite persistence for user OAuth credentials."""

from __future__ import annotations

from datetime import UTC, datetime
from contextlib import suppress

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _ensure_user_oauth_credentials_table() -> None:
    with _get_db_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_oauth_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                client_id TEXT,
                client_secret TEXT,
                redirect_uri TEXT,
                scope TEXT,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        with suppress(Exception):
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_oauth_user_provider "
                "ON user_oauth_credentials(user_id, provider)"
            )


@pg_dispatch("bike_analyzer.backend.db.postgres_user_oauth")
def get_user_oauth_credentials(user_id: int, provider: str) -> dict | None:
    _ensure_user_oauth_credentials_table()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_oauth_credentials WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        row = cur.fetchone()
        if row:
            creds = dict(row)
            if creds.get("client_secret"):
                try:
                    from ..db.token_crypto import decrypt_token

                    creds["client_secret"] = decrypt_token(creds["client_secret"])
                except Exception:
                    logger.debug(
                        "Failed to decrypt client_secret for user %s provider %s",
                        user_id,
                        provider,
                        exc_info=True,
                    )
            return creds
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_user_oauth")
def get_all_user_oauth_credentials(user_id: int) -> list[dict]:
    _ensure_user_oauth_credentials_table()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_oauth_credentials WHERE user_id = ?", (user_id,))
        return [dict(r) for r in cur.fetchall()]


@pg_dispatch("bike_analyzer.backend.db.postgres_user_oauth")
def save_user_oauth_credentials(user_id: int, provider: str, data: dict) -> None:
    _ensure_user_oauth_credentials_table()
    now = datetime.now(UTC).isoformat()
    client_secret = data.get("client_secret", "")
    if client_secret:
        from ..db.token_crypto import encrypt_token

        client_secret = encrypt_token(client_secret)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_oauth_credentials
               (user_id, provider, client_id, client_secret, redirect_uri,
                scope, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, provider) DO UPDATE SET
                   client_id = excluded.client_id,
                   client_secret = excluded.client_secret,
                   redirect_uri = excluded.redirect_uri,
                   scope = excluded.scope,
                   updated_at = excluded.updated_at""",
            (
                user_id,
                provider,
                data.get("client_id"),
                client_secret,
                data.get("redirect_uri"),
                data.get("scope"),
                now,
                now,
            ),
        )


@pg_dispatch("bike_analyzer.backend.db.postgres_user_oauth")
def delete_user_oauth_credentials(user_id: int, provider: str) -> bool:
    _ensure_user_oauth_credentials_table()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_oauth_credentials WHERE user_id = ? AND provider = ?", (user_id, provider))
        conn.commit()
        return cur.rowcount > 0
