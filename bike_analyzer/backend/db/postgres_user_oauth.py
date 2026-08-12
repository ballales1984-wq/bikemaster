"""PostgreSQL-backed persistence for user OAuth credentials."""

from __future__ import annotations

from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_user_oauth_credentials_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_oauth_credentials (
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                client_id TEXT,
                client_secret TEXT,
                redirect_uri TEXT,
                scope TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY(user_id, provider)
            )
            """
        )
        conn.commit()


def get_user_oauth_credentials(user_id: int, provider: str) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_user_oauth_credentials_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM user_oauth_credentials WHERE user_id = %s AND provider = %s",
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
                        pass
                return creds
            return None
    finally:
        _safe_close(conn)


def get_all_user_oauth_credentials(user_id: int) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_user_oauth_credentials_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM user_oauth_credentials WHERE user_id = %s", (user_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def save_user_oauth_credentials(user_id: int, provider: str, data: dict) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_user_oauth_credentials_table(conn)
        now = datetime.now(UTC).isoformat()
        client_secret = data.get("client_secret", "")
        if client_secret:
            try:
                from ..db.token_crypto import encrypt_token
                client_secret = encrypt_token(client_secret)
            except Exception:
                pass
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_oauth_credentials
                (user_id, provider, client_id, client_secret, redirect_uri,
                 scope, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    client_id = excluded.client_id,
                    client_secret = excluded.client_secret,
                    redirect_uri = excluded.redirect_uri,
                    scope = excluded.scope,
                    updated_at = excluded.updated_at
                """,
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
            conn.commit()
    finally:
        _safe_close(conn)


def delete_user_oauth_credentials(user_id: int, provider: str) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_user_oauth_credentials_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_oauth_credentials WHERE user_id = %s AND provider = %s",
                (user_id, provider),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)
