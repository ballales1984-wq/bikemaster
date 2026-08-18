"""Fitness repository — SQLite persistence for fitness states."""

from __future__ import annotations

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_fitness")
def get_fitness_states_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM fitness_states WHERE athlete_id = ? AND tenant_id = ? ORDER BY date ASC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM fitness_states WHERE athlete_id = ? ORDER BY date ASC",
                (athlete_id,),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]
