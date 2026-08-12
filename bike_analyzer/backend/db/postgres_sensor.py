"""PostgreSQL-backed persistence for sensor data and activity classifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_sensor_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_data (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                heart_rate INTEGER,
                lat REAL,
                lng REAL,
                altitude REAL,
                accel_x REAL,
                accel_y REAL,
                accel_z REAL,
                speed_kmh REAL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_activity_classification (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                date TEXT NOT NULL,
                label TEXT NOT NULL,
                hr_resting INTEGER,
                hr_avg REAL,
                hours REAL DEFAULT 0,
                steps_estimated INTEGER DEFAULT 0,
                distance_km REAL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'derived',
                confidence REAL DEFAULT 0.5,
                computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(athlete_id, date)
            )
            """
        )
        conn.commit()


def log_sensor_data(
    athlete_id: int,
    samples: list[dict[str, any]],
    *,
    tenant_id: int = 0,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    if not samples:
        return 0
    rows = []
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
    conn = _connect()
    try:
        _ensure_sensor_tables(conn)
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO sensor_data
                (athlete_id, tenant_id, ts, heart_rate, lat, lng, altitude,
                 accel_x, accel_y, accel_z, speed_kmh)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            conn.commit()
            return cur.rowcount
    finally:
        _safe_close(conn)


def classify_day(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_sensor_tables(conn)
        date_start = for_date

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MIN(heart_rate) as resting_hr,
                       ROUND(AVG(heart_rate), 1) as avg_hr,
                       MAX(heart_rate) as max_hr,
                       COUNT(*) as sample_count
                FROM hr_24h_samples
                WHERE athlete_id = %s AND date(recorded_at) = %s
                """,
                (athlete_id, date_start),
            )
            hr_row = cur.fetchone()
            resting_hr = hr_row["resting_hr"] if hr_row and hr_row["resting_hr"] is not None else None
            avg_hr = hr_row["avg_hr"] if hr_row and hr_row["avg_hr"] is not None else None
            sample_count = hr_row["sample_count"] if hr_row and hr_row["sample_count"] is not None else 0

            cur.execute(
                """
                SELECT ROUND(SUM(distance_km), 2) as total_km,
                       SUM(duration_minutes) as total_min,
                       ROUND(SUM(calories), 0) as total_cal,
                       COUNT(*) as rides_count
                FROM rides
                WHERE athlete_id = %s AND date(date) = %s
                """,
                (athlete_id, date_start),
            )
            ride_row = cur.fetchone()
            distance_km = ride_row["total_km"] if ride_row and ride_row["total_km"] is not None else 0.0
            rides_count = ride_row["rides_count"] if ride_row and ride_row["rides_count"] is not None else 0
            calories = ride_row["total_cal"] if ride_row and ride_row["total_cal"] is not None else 0

            cur.execute(
                """
                SELECT steps_estimated, tdee_kcal, neat_kcal, intake_kcal
                FROM metabolic_daily_summaries
                WHERE athlete_id = %s AND date = %s AND tenant_id = %s
                """,
                (athlete_id, date_start, tenant_id),
            )
            meta_row = cur.fetchone()

        high_activity_steps = 2000
        high_activity_km = 1.0
        sleep_threshold_ratio = 0.55
        max_setting = _get_max_hr_setting(athlete_id)
        resting_setting = _get_resting_hr_setting(athlete_id)

        steps_estimated = int(meta_row["steps_estimated"]) if meta_row and meta_row["steps_estimated"] else 0

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
            not is_active
            and resting_setting is not None
            and resting_hr is not None
            and resting_hr <= resting_setting + 5
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
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_activity_classification
                (athlete_id, tenant_id, date, label, hr_resting, hr_avg,
                 hours, steps_estimated, distance_km, source, confidence, computed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id, date) DO UPDATE SET
                label = excluded.label,
                hr_resting = excluded.hr_resting,
                hr_avg = excluded.hr_avg,
                hours = excluded.hours,
                steps_estimated = excluded.steps_estimated,
                distance_km = excluded.distance_km,
                confidence = excluded.confidence,
                computed_at = excluded.computed_at
                """,
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
    finally:
        _safe_close(conn)


def get_activity_summary(
    athlete_id: int,
    days: int = 30,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_sensor_tables(conn)
        since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    """
                    SELECT date, label, hr_resting, hr_avg, hours,
                           steps_estimated, distance_km, confidence
                    FROM daily_activity_classification
                    WHERE athlete_id = %s AND date >= %s AND tenant_id = %s
                    ORDER BY date ASC
                    """,
                    (athlete_id, since, tenant_id),
                )
            else:
                cur.execute(
                    """
                    SELECT date, label, hr_resting, hr_avg, hours,
                           steps_estimated, distance_km, confidence
                    FROM daily_activity_classification
                    WHERE athlete_id = %s AND date >= %s
                    ORDER BY date ASC
                    """,
                    (athlete_id, since),
                )
            rows = cur.fetchall()
        return [
            {
                "date": r["date"],
                "label": r["label"],
                "hr_resting": r["hr_resting"],
                "hr_avg": r["hr_avg"],
                "hours": r["hours"],
                "steps_estimated": r["steps_estimated"],
                "distance_km": r["distance_km"],
                "confidence": r["confidence"],
            }
            for r in rows
        ]
    finally:
        _safe_close(conn)


def get_activity_classification(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_sensor_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, label, hr_resting, hr_avg, hours,
                       steps_estimated, distance_km, confidence
                FROM daily_activity_classification
                WHERE athlete_id = %s AND date = %s AND tenant_id = %s
                """,
                (athlete_id, for_date, tenant_id),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "date": row["date"],
            "label": row["label"],
            "hr_resting": row["hr_resting"],
            "hr_avg": row["hr_avg"],
            "hours": row["hours"],
            "steps_estimated": row["steps_estimated"],
            "distance_km": row["distance_km"],
            "confidence": row["confidence"],
        }
    finally:
        _safe_close(conn)


def _get_max_hr_setting(athlete_id: int) -> int | None:
    from .postgres_hr import get_hr_settings
    settings = get_hr_settings(athlete_id)
    if not settings:
        return None
    val = settings.get("max_hr")
    return int(val) if val is not None else None


def _get_resting_hr_setting(athlete_id: int) -> int | None:
    from .postgres_hr import get_hr_settings
    settings = get_hr_settings(athlete_id)
    if not settings:
        return None
    val = settings.get("resting_hr")
    return int(val) if val is not None else None
