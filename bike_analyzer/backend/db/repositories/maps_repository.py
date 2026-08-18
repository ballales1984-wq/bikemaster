"""Maps repository — SQLite persistence for maps/SerpApi usage tracking."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_maps")
def get_maps_usage(month: str | None = None) -> int:
    if month is None:
        month = datetime.now(UTC).strftime("%Y-%m")
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count FROM serpapi_usage WHERE month = ?", (month,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_maps")
def record_maps_call(month: str | None = None, n: int = 1) -> None:
    if month is None:
        month = datetime.now(UTC).strftime("%Y-%m")
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO serpapi_usage (month, count) VALUES (?, ?)
               ON CONFLICT(month) DO UPDATE SET count = count + excluded.count""",
            (month, n),
        )
        conn.commit()
