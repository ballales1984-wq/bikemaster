"""Heart rate repository — SQLite persistence for 24h heart rate samples and settings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def log_hr_sample(
    athlete_id: int,
    heart_rate: int,
    *,
    source: str = "ble",
    device_id: str | None = None,
    recorded_at: str | None = None,
    tenant_id: int = 0,
) -> int:
    """Append a single heart-rate sample to the 24h tracking table.

    ``recorded_at`` is stored as an ISO-8601 UTC timestamp so samples can be
    aggregated by hour / day when rendering the 24h chart.
    """
    if heart_rate <= 0 or heart_rate > 300:
        return 0
    if not recorded_at:
        recorded_at = datetime.now(UTC).isoformat()
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hr_24h_samples
               (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, now),
        )
        conn.commit()
        return int(cur.lastrowid)


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def log_hr_samples(
    athlete_id: int,
    samples: list[dict[str, Any]],
    *,
    source: str = "ble",
    tenant_id: int = 0,
) -> int:
    """Bulk-insert heart-rate samples for 24h tracking.

    Each sample dict accepts: ``heart_rate`` (int), ``recorded_at`` (ISO),
    ``device_id`` (optional str).
    """
    if not samples:
        return 0
    now = datetime.now(UTC).isoformat()
    rows: list[tuple[Any, ...]] = []
    for s in samples:
        hr = s.get("heart_rate")
        if hr is None or hr < 0 or hr > 300:
            continue
        rows.append(
            (
                athlete_id,
                tenant_id,
                int(hr),
                s.get("source", source),
                s.get("device_id"),
                s.get("recorded_at") or now,
                now,
            )
        )
    if not rows:
        return 0
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """INSERT INTO hr_24h_samples
               (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return int(cur.rowcount)


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def get_hr_24h_samples(
    athlete_id: int,
    hours: int = 24,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Return raw heart-rate samples for the last *hours* hours (oldest-first)."""
    since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                """SELECT id, heart_rate, source, device_id, recorded_at
                   FROM hr_24h_samples
                   WHERE athlete_id = ? AND tenant_id = ?
                     AND recorded_at >= ?
                   ORDER BY recorded_at ASC""",
                (athlete_id, tenant_id, since),
            )
        else:
            cur.execute(
                """SELECT id, heart_rate, source, device_id, recorded_at
                   FROM hr_24h_samples
                   WHERE athlete_id = ?
                     AND recorded_at >= ?
                   ORDER BY recorded_at ASC""",
                (athlete_id, since),
            )
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "heart_rate": r[1],
            "source": r[2],
            "device_id": r[3],
            "recorded_at": r[4],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def get_hr_daily_summary(
    athlete_id: int,
    days: int = 30,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Return per-day resting / average / max / min HR for the last *days* days."""
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    with _get_db_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT date(recorded_at) as day,
                   MIN(heart_rate) as resting_hr,
                   ROUND(AVG(heart_rate), 1) as avg_hr,
                   MAX(heart_rate) as max_hr,
                   COUNT(*) as sample_count
            FROM hr_24h_samples
            WHERE athlete_id = ?
              AND date(recorded_at) >= ?
        """
        params: list[Any] = [athlete_id, since]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " GROUP BY date(recorded_at) ORDER BY day ASC"
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {
            "day": r[0],
            "resting_hr": r[1],
            "avg_hr": r[2],
            "max_hr": r[3],
            "min_hr": r[1],
            "sample_count": r[4],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def get_hr_settings(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Return HR 24h monitoring settings for an athlete."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM hr_monitoring_settings WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM hr_monitoring_settings WHERE athlete_id = ?",
                (athlete_id,),
            )
        row = cur.fetchone()
    if not row:
        return None
    return dict(row)


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def upsert_hr_settings(athlete_id: int, settings: dict, *, tenant_id: int = 0) -> dict:
    """Create or update HR 24h monitoring settings."""
    now = datetime.now(UTC).isoformat()
    allowed = {
        "enabled",
        "interval_seconds",
        "source",
        "device_id",
        "max_hr",
        "resting_hr",
        "tenant_id",
    }
    clean = {k: v for k, v in settings.items() if k in allowed}
    clean.setdefault("athlete_id", athlete_id)
    clean.setdefault("tenant_id", tenant_id)
    clean.setdefault("created_at", now)
    clean.setdefault("updated_at", now)
    cols = list(clean.keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in ("athlete_id", "tenant_id"))
    if not updates:
        updates = "updated_at = excluded.updated_at"
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""INSERT INTO hr_monitoring_settings ({col_names})
                VALUES ({placeholders})
                ON CONFLICT(athlete_id) DO UPDATE SET {updates}""",
            [clean[c] for c in cols],
        )
        conn.commit()
    return get_hr_settings(athlete_id, tenant_id) or dict(clean)


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def delete_hr_settings(athlete_id: int, tenant_id: int | None = None) -> bool:
    """Delete HR 24h monitoring settings for an athlete."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "DELETE FROM hr_monitoring_settings WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "DELETE FROM hr_monitoring_settings WHERE athlete_id = ?",
                (athlete_id,),
            )
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_hr")
def delete_hr_samples(athlete_id: int, *, tenant_id: int | None = None, older_than: str | None = None) -> int:
    """Delete HR samples, optionally filtered by age (ISO string). Returns deleted count."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None and older_than:
            cur.execute(
                "DELETE FROM hr_24h_samples WHERE athlete_id = ? AND tenant_id = ? AND recorded_at < ?",
                (athlete_id, tenant_id, older_than),
            )
        elif tenant_id is not None:
            cur.execute(
                "DELETE FROM hr_24h_samples WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        elif older_than:
            cur.execute(
                "DELETE FROM hr_24h_samples WHERE athlete_id = ? AND recorded_at < ?",
                (athlete_id, older_than),
            )
        else:
            cur.execute("DELETE FROM hr_24h_samples WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return int(cur.rowcount)


def _get_max_hr_setting(athlete_id: int) -> int | None:
    settings = get_hr_settings(athlete_id)
    if not settings:
        return None
    val = settings.get("max_hr")
    return int(val) if val is not None else None


def _get_resting_hr_setting(athlete_id: int) -> int | None:
    settings = get_hr_settings(athlete_id)
    if not settings:
        return None
    val = settings.get("resting_hr")
    return int(val) if val is not None else None
