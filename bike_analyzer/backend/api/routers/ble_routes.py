"""BLE API routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from ..routes import _current_athlete_id, get_current_user
from ..schemas import BleDeviceOut, BleDeviceRegister, BleDeviceSync, BleDeviceUpdate

router = APIRouter(prefix="/ble", tags=["ble"])


@router.get("/devices")
async def list_ble_devices(current_user: dict = Depends(get_current_user)):
    """List all BLE devices registered for the current athlete."""
    from ...db.database import get_ble_devices

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    devices = get_ble_devices(athlete_id, tenant_id=tenant_id)
    return {"devices": [BleDeviceOut.model_validate(d).model_dump() for d in devices]}


@router.post("/devices")
async def register_ble_device(current_user: dict = Depends(get_current_user), payload: BleDeviceRegister = Body(...)):
    """Register a new BLE device (or update if already known)."""
    from ...db.database import register_ble_device

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    device_id = register_ble_device(
        athlete_id=athlete_id,
        device_id=payload.device_id,
        name=payload.name,
        tenant_id=tenant_id,
        device_type=payload.device_type,
        service_uuid=payload.service_uuid,
        characteristic_uuid=payload.characteristic_uuid,
        mac_address=payload.mac_address,
    )
    return {"id": device_id, "device_id": payload.device_id, "name": payload.name}


@router.put("/devices/{device_id}")
async def update_ble_device(
    current_user: dict = Depends(get_current_user),
    device_id: int = ...,
    payload: BleDeviceUpdate = ...,
):
    """Update a BLE device (name, paired status, settings)."""
    from ...db.database import get_ble_device, update_ble_device

    athlete_id = _current_athlete_id(current_user)
    existing = get_ble_device(device_id, athlete_id)
    if not existing:
        raise HTTPException(status_code=404, detail="BLE device not found")
    update_data = payload.model_dump(exclude_none=True)
    updated = update_ble_device(device_id, athlete_id, **update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="BLE device not found")
    return BleDeviceOut.model_validate(updated).model_dump()


@router.delete("/devices/{device_id}")
async def delete_ble_device(current_user: dict = Depends(get_current_user), device_id: int = ...):
    """Unregister (delete) a BLE device."""
    from ...db.database import get_ble_device, unregister_ble_device

    athlete_id = _current_athlete_id(current_user)
    existing = get_ble_device(device_id, athlete_id)
    if not existing:
        raise HTTPException(status_code=404, detail="BLE device not found")
    unregister_ble_device(device_id, athlete_id)
    return {"status": "deleted", "id": device_id}


@router.post("/devices/{device_id}/sync")
async def sync_ble_device(
    current_user: dict = Depends(get_current_user),
    device_id: int = ...,
    payload: BleDeviceSync | None = Body(default=None),
):
    """Trigger a sync/read from a BLE device."""
    from ...db.database import get_ble_device, log_athlete_metric, mark_ble_device_synced

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    existing = get_ble_device(device_id, athlete_id)
    if not existing:
        raise HTTPException(status_code=404, detail="BLE device not found")
    device_type = existing.get("device_type", "generic")
    note = f"ble:{existing.get('device_id', '')}"
    has_value = payload is not None and payload.value is not None
    unit = payload.unit if payload else None
    if device_type == "weight_scale":
        metric_type = "weight_kg" if unit != "lb" else "weight_lb"
        unit = unit or "kg"
    elif device_type == "heart_rate":
        metric_type = "heart_rate_bpm"
        unit = unit or "bpm"
    elif device_type == "blood_pressure":
        metric_type = "blood_pressure_systolic"
        unit = unit or "mmHg"
    else:
        metric_type = "ble_generic"
        unit = unit or "value"
    metric_id = 0
    if has_value:
        metric_id = log_athlete_metric(
            athlete_id=athlete_id,
            metric_type=metric_type,
            value=payload.value,
            tenant_id=tenant_id,
            unit=unit,
            note=note,
            source="ble",
            recorded_at=payload.recorded_at,
        )
    mark_ble_device_synced(device_id, athlete_id)
    return {
        "status": "synced",
        "device_id": device_id,
        "type": device_type,
        "metric_id": metric_id,
    }
