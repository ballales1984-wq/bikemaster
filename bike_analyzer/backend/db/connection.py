"""Database connection management for SQLite.

Provides the ``get_db_connection`` context manager used across the
SQLite persistence layer.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any

from ..settings import get_settings

_s = get_settings()
DB_PATH = _s.db_path
_INITIAL_DB_PATH = DB_PATH


@contextmanager
def get_db_connection():
    """Context manager per connessioni SQLite con WAL e retry su lock.

    Configura la connessione con:
    - ``journal_mode=WAL`` per letture concorrenti durante la scrittura.
    - ``busy_timeout=5000`` per attendere il rilascio del lock.
    - ``foreign_keys=ON`` per integrita' referenziale.
    - ``row_factory=sqlite3.Row`` per accesso per colonna.

    In caso di ``OperationalError`` con messaggio ``locked`` ritenta fino a
    3 volte con backoff lineare (0.1s, 0.2s, 0.3s). Il commit e' automatico
    se il blocco ``with`` completa senza eccezioni.
    """
    import time

    max_retries = 3
    retry_delay = 0.1
    conn = None
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            break
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise

    if conn is None:
        raise RuntimeError(f"Failed to connect to database at {DB_PATH} after {max_retries} retries")

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
