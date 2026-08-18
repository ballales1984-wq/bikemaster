"""Sensor repository — SQLite persistence for sensor data and activity classification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch
from .hr_repository import get_hr_settings

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_sensor")
def log_sensor_data(
    athlete_id: int,
    samples: list[dict[str, Any]],
    *,
    tenant_id: int = 0,
) -> int:
    """Bulk-insert raw BLE sensor readings (heart-rate, GPS, accelerometer)."""
    if not samples:
        return 0
    rows: list[tuple[Any, ...]] = []
    for s in samples:
        ts = s.get("ts") or s.get("recorded_at") or datetime.now(UTC).isoformat()
        rows.append(
            (
                athlete_id,
                tenant_id,
                ts,
                s.get("heart_rate"),
                s.get("lat"),
                s.get("lng"),
                s.get("altitude"),
                s.get("accel_x"),
                s.get("accel_y"),
                s.get("accel_z"),
                s.get("speed_kmh"),
            )
        )
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """INSERT INTO sensor_data
               (athlete_id, tenant_id, ts, heart_rate, lat, lng, altitude,
                accel_x, accel_y, accel_z, speed_kmh)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return int(cur.rowcount)


@pg_dispatch("bike_analyzer.backend.db.postgres_sensor")
def classify_day(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict:
    """Compute the activity classification for a single calendar day.

    Combines HR 24h samples, GPS movement (rides) and metabolic summaries to
    derive an autonomous label: ``sleep``, ``recovery``, ``active`` or
    ``rest``.  Results are persisted into ``daily_activity_classification``.
    """
    date_start = for_date

    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT MIN(heart_rate) as resting_hr,
                      ROUND(AVG(heart_rate), 1) as avg_hr,
                      MAX(heart_rate) as max_hr,
                      COUNT(*) as sample_count
               FROM hr_24h_samples
               WHERE athlete_id = ? AND date(recorded_at) = ?""",
            (athlete_id, date_start),
        )
        hr_row = cur.fetchone()
        resting_hr = hr_row[0] if hr_row and hr_row[0] is not None else None
        avg_hr = hr_row[1] if hr_row and hr_row[1] is not None else None
        sample_count = hr_row[3] if hr_row and hr_row[3] is not None else 0

        cur.execute(
            """SELECT ROUND(SUM(distance_km), 2) as total_km,
                      SUM(duration_minutes) as total_min,
                      ROUND(SUM(calories), 0) as total_cal,
                      COUNT(*) as rides_count
               FROM rides
               WHERE athlete_id = ? AND date(date) = ?""",
            (athlete_id, date_start),
        )
        ride_row = cur.fetchone()
        distance_km = ride_row[0] if ride_row and ride_row[0] is not None else 0.0
        rides_count = ride_row[3] if ride_row and ride_row[3] is not None else 0
        calories = ride_row[2] if ride_row and ride_row[2] is not None else 0

        cur.execute(
            """SELECT steps_estimated, tdee_kcal, neat_kcal, intake_kcal
               FROM metabolic_daily_summaries
               WHERE athlete_id = ? AND date = ? AND tenant_id = ?""",
            (athlete_id, date_start, tenant_id),
        )
        meta_row = cur.fetchone()

    # Heuristic thresholds
    high_activity_steps = 2000
    high_activity_km = 1.0
    sleep_threshold_ratio = 0.55
    max_setting = _get_max_hr_setting(athlete_id)
    resting_setting = _get_resting_hr_setting(athlete_id)

    steps_estimated = int(meta_row[0]) if meta_row and meta_row[0] else 0

    # Determine label
    is_sleep_day = (
        resting_hr is not None
        and resting_setting is not None
        and sample_count > 0
        and avg_hr is not None
        and max_setting is not None
        and resting_hr >= int(resting_setting * 0.85)
        and avg_hr < max_setting * sleep_threshold_ratio
    )
    is_active = steps_estimated >= high_activity_steps or distance_km >= high_activity_km
    is_recovery = (
        not is_active and resting_setting is not None and resting_hr is not None and resting_hr <= resting_setting + 5
    )

    if is_sleep_day and not is_active:
        label = "sleep"
    elif is_active:
        label = "active"
    elif is_recovery:
        label = "recovery"
    else:
        label = "rest"

    confidence = 0.85 if is_active else (0.75 if is_recovery else 0.60)
    hours = round(calories / 50.0, 1) if calories else 0.0

    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO daily_activity_classification
               (athlete_id, tenant_id, date, label, hr_resting, hr_avg,
                hours, steps_estimated, distance_km, source, confidence, computed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id, date) DO UPDATE SET
               label = excluded.label,
               hr_resting = excluded.hr_resting,
               hr_avg = excluded.hr_avg,
               hours = excluded.hours,
               steps_estimated = excluded.steps_estimated,
               distance_km = excluded.distance_km,
               confidence = excluded.confidence,
               computed_at = excluded.computed_at""",
            (
                athlete_id,
                tenant_id,
                date_start,
                label,
                resting_hr,
                avg_hr,
                hours,
                steps_estimated,
                distance_km,
                "derived",
                confidence,
                now,
            ),
        )
        conn.commit()

    return {
        "date": date_start,
        "label": label,
        "hr_resting": resting_hr,
        "hr_avg": avg_hr,
        "hours": hours,
        "steps_estimated": steps_estimated,
        "distance_km": distance_km,
        "rides_count": rides_count,
        "confidence": round(confidence, 2),
    }


@pg_dispatch("bike_analyzer.backend.db.postgres_sensor")
def get_activity_summary(
    athlete_id: int,
    days: int = 30,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Return daily activity classifications for the last *days* days."""
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    with _get_db_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT date, label, hr_resting, hr_avg, hours,
                   steps_estimated, distance_km, confidence
            FROM daily_activity_classification
            WHERE athlete_id = ? AND date >= ?
        """
        params: list[Any] = [athlete_id, since]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY date ASC"
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {
            "date": r[0],
            "label": r[1],
            "hr_resting": r[2],
            "hr_avg": r[3],
            "hours": r[4],
            "steps_estimated": r[5],
            "distance_km": r[6],
            "confidence": r[7],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_sensor")
def get_activity_classification(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict | None:
    """Return the persisted activity classification for a single day."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT date, label, hr_resting, hr_avg, hours,
                      steps_estimated, distance_km, confidence
               FROM daily_activity_classification
               WHERE athlete_id = ? AND date = ? AND tenant_id = ?""",
            (athlete_id, for_date, tenant_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "date": row[0],
        "label": row[1],
        "hr_resting": row[2],
        "hr_avg": row[3],
        "hours": row[4],
        "steps_estimated": row[5],
        "distance_km": row[6],
        "confidence": row[7],
    }


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
