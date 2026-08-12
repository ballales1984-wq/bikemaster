"""PostgreSQL-backed persistence for heart-rate samples and monitoring settings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_hr_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_24h_samples (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                heart_rate INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                device_id TEXT,
                recorded_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_monitoring_settings (
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                max_hr INTEGER,
                resting_hr INTEGER,
                hr_zones JSONB,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY(athlete_id)
            )
            """
        )
        conn.commit()


def log_hr_sample(
    athlete_id: int,
    heart_rate: int,
    *,
    source: str = "ble",
    device_id: str | None = None,
    recorded_at: str | None = None,
    tenant_id: int = 0,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    if heart_rate <= 0 or heart_rate > 300:
        return 0
    if not recorded_at:
        recorded_at = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hr_24h_samples
                (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, now),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def log_hr_samples(
    athlete_id: int,
    samples: list[dict[str, any]],
    *,
    source: str = "ble",
    tenant_id: int = 0,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    if not samples:
        return 0
    now = datetime.now(UTC).isoformat()
    rows = []
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
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO hr_24h_samples
                (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            conn.commit()
            return cur.rowcount
    finally:
        _safe_close(conn)


def get_hr_24h_samples(
    athlete_id: int,
    hours: int = 24,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    """
                    SELECT id, heart_rate, source, device_id, recorded_at
                    FROM hr_24h_samples
                    WHERE athlete_id = %s AND tenant_id = %s
                      AND recorded_at >= %s
                    ORDER BY recorded_at ASC
                    """,
                    (athlete_id, tenant_id, since),
                )
            else:
                cur.execute(
                    """
                    SELECT id, heart_rate, source, device_id, recorded_at
                    FROM hr_24h_samples
                    WHERE athlete_id = %s
                      AND recorded_at >= %s
                    ORDER BY recorded_at ASC
                    """,
                    (athlete_id, since),
                )
            rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "heart_rate": r["heart_rate"],
                "source": r["source"],
                "device_id": r["device_id"],
                "recorded_at": r["recorded_at"],
            }
            for r in rows
        ]
    finally:
        _safe_close(conn)


def get_hr_daily_summary(
    athlete_id: int,
    days: int = 30,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    """
                    SELECT date(recorded_at) as day,
                           MIN(heart_rate) as resting_hr,
                           ROUND(AVG(heart_rate), 1) as avg_hr,
                           MAX(heart_rate) as max_hr,
                           COUNT(*) as sample_count
                    FROM hr_24h_samples
                    WHERE athlete_id = %s AND tenant_id = %s
                      AND date(recorded_at) >= %s
                    GROUP BY date(recorded_at) ORDER BY day ASC
                    """,
                    (athlete_id, tenant_id, since),
                )
            else:
                cur.execute(
                    """
                    SELECT date(recorded_at) as day,
                           MIN(heart_rate) as resting_hr,
                           ROUND(AVG(heart_rate), 1) as avg_hr,
                           MAX(heart_rate) as max_hr,
                           COUNT(*) as sample_count
                    FROM hr_24h_samples
                    WHERE athlete_id = %s
                      AND date(recorded_at) >= %s
                    GROUP BY date(recorded_at) ORDER BY day ASC
                    """,
                    (athlete_id, since),
                )
            rows = cur.fetchall()
        return [
            {
                "day": r["day"],
                "resting_hr": r["resting_hr"],
                "avg_hr": r["avg_hr"],
                "max_hr": r["max_hr"],
                "min_hr": r["resting_hr"],
                "sample_count": r["sample_count"],
            }
            for r in rows
        ]
    finally:
        _safe_close(conn)


def get_hr_settings(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM hr_monitoring_settings WHERE athlete_id = %s AND tenant_id = %s",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM hr_monitoring_settings WHERE athlete_id = %s",
                    (athlete_id,),
                )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def upsert_hr_settings(athlete_id: int, settings: dict, *, tenant_id: int = 0) -> dict:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
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
        clean.setdefault("updated_at", now)
        cols = list(clean.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        col_names = ", ".join(cols)
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in ("athlete_id", "tenant_id"))
        if not updates:
            updates = "updated_at = excluded.updated_at"
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO hr_monitoring_settings ({col_names})
                VALUES ({placeholders})
                ON CONFLICT(athlete_id) DO UPDATE SET {updates}
                """,
                [clean[c] for c in cols],
            )
            conn.commit()
        return get_hr_settings(athlete_id, tenant_id) or dict(clean)
    finally:
        _safe_close(conn)


def delete_hr_settings(athlete_id: int, tenant_id: int | None = None) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "DELETE FROM hr_monitoring_settings WHERE athlete_id = %s AND tenant_id = %s",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "DELETE FROM hr_monitoring_settings WHERE athlete_id = %s",
                    (athlete_id,),
                )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def delete_hr_samples(athlete_id: int, *, tenant_id: int | None = None, older_than: str | None = None) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_hr_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None and older_than:
                cur.execute(
                    "DELETE FROM hr_24h_samples WHERE athlete_id = %s AND tenant_id = %s AND recorded_at < %s",
                    (athlete_id, tenant_id, older_than),
                )
            elif tenant_id is not None:
                cur.execute(
                    "DELETE FROM hr_24h_samples WHERE athlete_id = %s AND tenant_id = %s",
                    (athlete_id, tenant_id),
                )
            elif older_than:
                cur.execute(
                    "DELETE FROM hr_24h_samples WHERE athlete_id = %s AND recorded_at < %s",
                    (athlete_id, older_than),
                )
            else:
                cur.execute(
                    "DELETE FROM hr_24h_samples WHERE athlete_id = %s",
                    (athlete_id,),
                )
            conn.commit()
            return cur.rowcount
    finally:
        _safe_close(conn)
