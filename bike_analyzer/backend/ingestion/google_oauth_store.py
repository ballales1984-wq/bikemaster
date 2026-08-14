"""Google OAuth token storage and refresh helpers."""

from __future__ import annotations

import logging
import time

from ..settings import get_settings

_s = get_settings()
logger = logging.getLogger(__name__)

# noqa: S105
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
"""  # noqa: S105

TOKEN_REFRESH_BUFFER_SECONDS = 300


def _get_conn():
    from ..db.database import get_db_connection

    return get_db_connection()


def ensure_google_tokens_table() -> None:
    with _get_conn() as conn:
        conn.executescript(_GOOGLE_TOKEN_TABLE)


def store_google_token(athlete_id: int, provider: str, token_data: dict) -> None:
    from ..db.database import save_google_token

    expires_at = token_data.get("expires_at", 0)
    if isinstance(expires_at, str):
        try:
            expires_at = int(expires_at)
        except ValueError:
            expires_at = 0
    if not expires_at and "expires_in" in token_data:
        expires_at = int(time.time()) + int(token_data["expires_in"])
    encrypted_access = token_data.get("access_token", "")
    encrypted_refresh = token_data.get("refresh_token", "")
    try:
        from ..db.token_crypto import encrypt_token
        if encrypted_access:
            encrypted_access = encrypt_token(encrypted_access)
        if encrypted_refresh:
            encrypted_refresh = encrypt_token(encrypted_refresh)
    except Exception:
        logger.warning("Google token encryption skipped", exc_info=True)
    save_google_token(
        athlete_id=athlete_id,
        provider=provider,
        access_token=encrypted_access,
        refresh_token=encrypted_refresh,
        expires_at=expires_at,
        scope=token_data.get("scope", ""),
    )


def get_google_token(athlete_id: int, provider: str) -> dict | None:
    from ..db.database import get_google_token

    row = get_google_token(athlete_id, provider)
    if not row:
        return None
    access_token, refresh_token = row.get("access_token", ""), row.get("refresh_token", "")
    try:
        from ..db.token_crypto import decrypt_token
        if access_token:
            access_token = decrypt_token(access_token)
        if refresh_token:
            refresh_token = decrypt_token(refresh_token)
    except Exception:
        logger.warning("Google token decryption failed", exc_info=True)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": row.get("expires_at"),
        "scope": row.get("scope"),
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
                from ..db.database import delete_google_token
                delete_google_token(athlete_id, provider)
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
    from ..db.database import delete_google_token as _delete

    _delete(athlete_id, provider)
