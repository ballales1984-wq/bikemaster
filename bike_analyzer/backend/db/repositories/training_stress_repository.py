"""Training stress repository — SQLite persistence for training stress days."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def upsert_training_stress_day(
    athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float, tenant_id: int = 0
) -> None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cur.execute(
            """INSERT INTO training_stress_days
            (athlete_id, date, tss, atl, ctl, tsb, created_at, updated_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
            tss=excluded.tss, atl=excluded.atl, ctl=excluded.ctl,
            tsb=excluded.tsb, updated_at=excluded.updated_at, tenant_id=excluded.tenant_id""",
            (athlete_id, date, tss, atl, ctl, tsb, now, now, tenant_id),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def get_training_stress_days(athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY date DESC LIMIT ?",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? "
                "ORDER BY date DESC LIMIT ?",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
        return [{"date": r[0], "tss": r[1], "atl": r[2], "ctl": r[3], "tsb": r[4]} for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def get_latest_training_stress(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY date DESC LIMIT 1",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? "
                "ORDER BY date DESC LIMIT 1",
                (athlete_id,),
            )
        row = cur.fetchone()
        if row:
            return {
                "date": row[0],
                "tss": row[1],
                "atl": row[2],
                "ctl": row[3],
                "tsb": row[4],
            }
        return None
