"""BLE repository - data access abstraction for BLE devices."""

from __future__ import annotations

from ...db.database import (
    get_ble_device,
    get_ble_devices,
    log_athlete_metric,
    mark_ble_device_synced,
    register_ble_device,
    unregister_ble_device,
    update_ble_device,
)


class BLERepository:
    @staticmethod
    def get_ble_devices(athlete_id: int, tenant_id: int = 0):
        return get_ble_devices(athlete_id, tenant_id=tenant_id)

    @staticmethod
    def register_ble_device(athlete_id: int, device_id: str, name: str, tenant_id: int = 0, **kwargs):
        return register_ble_device(
            athlete_id=athlete_id,
            device_id=device_id,
            name=name,
            tenant_id=tenant_id,
            **kwargs,
        )

    @staticmethod
    def get_ble_device(device_id: int, athlete_id: int):
        return get_ble_device(device_id, athlete_id)

    @staticmethod
    def update_ble_device(device_id: int, athlete_id: int, **update_data):
        return update_ble_device(device_id, athlete_id, **update_data)

    @staticmethod
    def unregister_ble_device(device_id: int, athlete_id: int):
        return unregister_ble_device(device_id, athlete_id)

    @staticmethod
    def log_athlete_metric(athlete_id: int, metric_type: str, value: float, tenant_id: int = 0, **kwargs):
        return log_athlete_metric(
            athlete_id=athlete_id,
            metric_type=metric_type,
            value=value,
            tenant_id=tenant_id,
            **kwargs,
        )

    @staticmethod
    def mark_ble_device_synced(device_id: int, athlete_id: int):
        return mark_ble_device_synced(device_id, athlete_id)
