"""PostgreSQL-backed persistence for BLE devices."""

from __future__ import annotations

from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_ble_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ble_devices (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                device_id TEXT NOT NULL,
                name TEXT NOT NULL,
                device_type TEXT NOT NULL DEFAULT 'weight_scale',
                service_uuid TEXT,
                characteristic_uuid TEXT,
                mac_address TEXT,
                paired BOOLEAN DEFAULT TRUE,
                settings TEXT DEFAULT '{}',
                last_connected_at TIMESTAMPTZ,
                last_synced_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(athlete_id, device_id)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_ble_devices_athlete_id
            ON ble_devices(athlete_id)
            """
        )
        conn.commit()


def register_ble_device(
    athlete_id: int,
    device_id: str,
    name: str,
    *,
    tenant_id: int = 0,
    device_type: str = "weight_scale",
    service_uuid: str | None = None,
    characteristic_uuid: str | None = None,
    mac_address: str | None = None,
    settings: str | None = None,
) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        now = datetime.now(UTC).isoformat()
        settings_json = settings or "{}"
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ble_devices
                (athlete_id, tenant_id, device_id, name, device_type,
                 service_uuid, characteristic_uuid, mac_address,
                 paired, settings, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id, device_id) DO UPDATE SET
                    name = excluded.name,
                    device_type = excluded.device_type,
                    service_uuid = excluded.service_uuid,
                    characteristic_uuid = excluded.characteristic_uuid,
                    mac_address = excluded.mac_address,
                    paired = excluded.paired,
                    settings = excluded.settings,
                    updated_at = excluded.updated_at
                RETURNING id
                """,
                (
                    athlete_id,
                    tenant_id,
                    device_id,
                    name,
                    device_type,
                    service_uuid,
                    characteristic_uuid,
                    mac_address,
                    True,
                    settings_json,
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"]
    finally:
        _safe_close(conn)


def get_ble_devices(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM ble_devices WHERE athlete_id = %s AND tenant_id = %s ORDER BY created_at DESC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM ble_devices WHERE athlete_id = %s ORDER BY created_at DESC",
                    (athlete_id,),
                )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def get_ble_device(device_id: int, athlete_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ble_devices WHERE id = %s AND athlete_id = %s", (device_id, athlete_id))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def update_ble_device(device_id: int, athlete_id: int, **updates) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    allowed = {
        "name", "device_type", "service_uuid", "characteristic_uuid",
        "mac_address", "paired", "settings", "last_connected_at",
        "last_synced_at",
    }
    set_clause = ", ".join(f"{k} = %s" for k in updates if k in allowed)
    if not set_clause:
        return get_ble_device(device_id, athlete_id)
    values = [updates[k] for k in updates if k in allowed]
    values.extend([device_id, athlete_id])
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        with conn.cursor() as cur:
            cur.execute(f"UPDATE ble_devices SET {set_clause} WHERE id = %s AND athlete_id = %s", values)
            conn.commit()
        return get_ble_device(device_id, athlete_id)
    finally:
        _safe_close(conn)


def unregister_ble_device(device_id: int, athlete_id: int) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ble_devices WHERE id = %s AND athlete_id = %s", (device_id, athlete_id))
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def mark_ble_device_connected(device_id: int, athlete_id: int) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ble_devices SET last_connected_at = %s WHERE id = %s AND athlete_id = %s",
                (now, device_id, athlete_id),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def mark_ble_device_synced(device_id: int, athlete_id: int) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_ble_tables(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ble_devices SET last_synced_at = %s WHERE id = %s AND athlete_id = %s",
                (now, device_id, athlete_id),
            )
            conn.commit()
    finally:
        _safe_close(conn)
