"""BLE repository — SQLite persistence for BLE devices."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
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
    """Register or update a BLE device for an athlete."""
    now = datetime.now(UTC).isoformat()
    settings_json = settings or "{}"
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ble_devices
               (athlete_id, tenant_id, device_id, name, device_type,
                service_uuid, characteristic_uuid, mac_address,
                paired, settings, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
               ON CONFLICT(athlete_id, device_id) DO UPDATE SET
                   name=excluded.name,
                   device_type=excluded.device_type,
                   service_uuid=excluded.service_uuid,
                   characteristic_uuid=excluded.characteristic_uuid,
                   mac_address=excluded.mac_address,
                   paired=1,
                   settings=excluded.settings,
                   updated_at=excluded.updated_at""",
            (
                athlete_id,
                tenant_id,
                device_id,
                name,
                device_type,
                service_uuid,
                characteristic_uuid,
                mac_address,
                settings_json,
                now,
                now,
            ),
        )
        conn.commit()
        cur.execute("SELECT id FROM ble_devices WHERE athlete_id = ? AND device_id = ?", (athlete_id, device_id))
        row = cur.fetchone()
        return int(row[0]) if row else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
def get_ble_devices(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    """List all BLE devices registered for an athlete."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM ble_devices WHERE athlete_id = ? AND tenant_id = ? ORDER BY created_at DESC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute("SELECT * FROM ble_devices WHERE athlete_id = ? ORDER BY created_at DESC", (athlete_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
def get_ble_device(device_id: int, athlete_id: int) -> dict | None:
    """Get a single BLE device by its DB id, ensuring athlete ownership."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ble_devices WHERE id = ? AND athlete_id = ?", (device_id, athlete_id))
        row = cur.fetchone()
    return dict(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
def update_ble_device(device_id: int, athlete_id: int, **updates) -> dict | None:
    """Update fields of a BLE device."""
    allowed = {
        "name",
        "device_type",
        "service_uuid",
        "characteristic_uuid",
        "mac_address",
        "paired",
        "settings",
        "last_connected_at",
        "last_synced_at",
    }
    set_clause = ", ".join(f"{k} = ?" for k in updates if k in allowed)
    if not set_clause:
        return get_ble_device(device_id, athlete_id)
    values = [updates[k] for k in updates if k in allowed]
    values.extend([device_id, athlete_id])
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE ble_devices SET {set_clause} WHERE id = ? AND athlete_id = ?", values)
        conn.commit()
    return get_ble_device(device_id, athlete_id)


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
def unregister_ble_device(device_id: int, athlete_id: int) -> bool:
    """Remove a BLE device registration."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM ble_devices WHERE id = ? AND athlete_id = ?", (device_id, athlete_id))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
def mark_ble_device_connected(device_id: int, athlete_id: int) -> None:
    """Update last_connected_at timestamp."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        conn.execute(
            "UPDATE ble_devices SET last_connected_at = ? WHERE id = ? AND athlete_id = ?",
            (now, device_id, athlete_id),
        )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_ble")
def mark_ble_device_synced(device_id: int, athlete_id: int) -> None:
    """Update last_synced_at timestamp."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        conn.execute(
            "UPDATE ble_devices SET last_synced_at = ? WHERE id = ? AND athlete_id = ?",
            (now, device_id, athlete_id),
        )
        conn.commit()
