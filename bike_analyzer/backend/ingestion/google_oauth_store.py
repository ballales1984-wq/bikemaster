"""Google OAuth token storage and refresh helpers."""

from __future__ import annotations

import time

from ..settings import get_settings

_s = get_settings()

_GOOGLE_TOKEN_TABLE = """
CREATE TABLE IF NOT EXISTS google_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    provider TEXT NOT NULL CHECK(provider IN ('google_fit','google_health')),
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at INTEGER,
    scope TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_google_tokens_athlete_provider
    ON google_tokens(athlete_id, provider);
"""

TOKEN_REFRESH_BUFFER_SECONDS = 300


def _get_conn():
    from ..db.database import get_db_connection

    return get_db_connection()


def ensure_google_tokens_table() -> None:
    with _get_conn() as conn:
        conn.executescript(_GOOGLE_TOKEN_TABLE)


def store_google_token(athlete_id: int, provider: str, token_data: dict) -> None:
    ensure_google_tokens_table()
    expires_at = token_data.get("expires_at", 0)
    if isinstance(expires_at, str):
        try:
            expires_at = int(expires_at)
        except ValueError:
            expires_at = 0
    if not expires_at and "expires_in" in token_data:
        expires_at = int(time.time()) + int(token_data["expires_in"])
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO google_tokens (athlete_id, provider, access_token, refresh_token, expires_at, scope)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, provider) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at,
                scope = excluded.scope,
                updated_at = datetime('now')
            """,
            (
                athlete_id,
                provider,
                token_data.get("access_token", ""),
                token_data.get("refresh_token", ""),
                expires_at,
                token_data.get("scope", ""),
            ),
        )


def get_google_token(athlete_id: int, provider: str) -> dict | None:
    ensure_google_tokens_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT access_token, refresh_token, expires_at, scope "
            "FROM google_tokens WHERE athlete_id = ? AND provider = ?",
            (athlete_id, provider),
        ).fetchone()
    if not row:
        return None
    access_token, refresh_token, expires_at, scope = row
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "scope": scope,
    }


def refresh_google_token(athlete_id: int, provider: str) -> str | None:
    import requests

    token_data = get_google_token(athlete_id, provider)
    if not token_data:
        return None
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None

    try:
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": _s.google_client_id,
                "client_secret": _s.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        resp.raise_for_status()
        new_data = resp.json()
        new_data["refresh_token"] = new_data.get("refresh_token", refresh_token)
        store_google_token(athlete_id, provider, new_data)
        return new_data.get("access_token")
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 400:
            body = exc.response.text or ""
            if "invalid_grant" in body:
                with _get_conn() as conn:
                    conn.execute(
                        "DELETE FROM google_tokens WHERE athlete_id = ? AND provider = ?", (athlete_id, provider)
                    )
                return None
        raise


def get_valid_google_token(athlete_id: int, provider: str) -> str | None:
    token_data = get_google_token(athlete_id, provider)
    if not token_data:
        return None
    expires_at = token_data.get("expires_at") or 0
    if expires_at and expires_at - time.time() < TOKEN_REFRESH_BUFFER_SECONDS:
        try:
            return refresh_google_token(athlete_id, provider)
        except Exception:
            return token_data.get("access_token")
    return token_data.get("access_token")


def delete_google_token(athlete_id: int, provider: str) -> None:
    ensure_google_tokens_table()
    with _get_conn() as conn:
        conn.execute("DELETE FROM google_tokens WHERE athlete_id = ? AND provider = ?", (athlete_id, provider))
