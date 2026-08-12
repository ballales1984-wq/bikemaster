"""Sync management REST API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from bike_analyzer.backend.security import get_current_user
from bike_analyzer.backend.sync.config import (
    SyncMode,
    SyncSettings,
    get_sync_config,
    save_sync_config,
)
from bike_analyzer.backend.sync.db_helpers import (
    get_conflicts,
    get_pending_entities,
    resolve_conflict_db,
)
from bike_analyzer.backend.sync.service import get_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncSettingsUpdate(BaseModel):
    mode: str | None = None
    daily_hour: int | None = None
    weekly_day: int | None = None
    cloud_url: str | None = None
    auth_token: str | None = None
    device_id: str | None = None
    enabled_entities: list[str] | None = None
    auto_sync_on_startup: bool | None = None


@router.get("/status")
async def sync_status(current_user: dict = Depends(get_current_user)):
    """Return sync service status for the current user."""
    service = get_sync_service()
    config = get_sync_config()
    pending = get_pending_entities()
    conflicts = get_conflicts(unresolved_only=True)
    return {
        "mode": config.mode.value,
        "enabled": service.is_enabled(),
        "pending_count": len(pending),
        "conflict_count": len(conflicts),
        "cloud_connected": bool(service.client),
    }


@router.get("/settings")
async def get_sync_settings(current_user: dict = Depends(get_current_user)):
    """Return current sync settings."""
    config = get_sync_config()
    return config.to_dict()


@router.put("/settings")
async def update_sync_settings(
    payload: SyncSettingsUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update sync settings."""
    config = get_sync_config()
    data = config.to_dict()
    if payload.mode is not None:
        try:
            data["mode"] = SyncMode(payload.mode).value
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid sync mode") from None
    if payload.daily_hour is not None:
        if not 0 <= payload.daily_hour <= 23:
            raise HTTPException(status_code=422, detail="daily_hour must be 0-23")
        data["daily_hour"] = payload.daily_hour
    if payload.weekly_day is not None:
        if not 0 <= payload.weekly_day <= 6:
            raise HTTPException(status_code=422, detail="weekly_day must be 0-6")
        data["weekly_day"] = payload.weekly_day
    if payload.cloud_url is not None:
        data["cloud_url"] = payload.cloud_url
    if payload.auth_token is not None:
        data["auth_token"] = payload.auth_token
    if payload.device_id is not None:
        data["device_id"] = payload.device_id
    if payload.enabled_entities is not None:
        data["enabled_entities"] = payload.enabled_entities
    if payload.auto_sync_on_startup is not None:
        data["auto_sync_on_startup"] = payload.auto_sync_on_startup
    new_config = SyncSettings.from_dict(data)
    save_sync_config(new_config)
    return new_config.to_dict()


@router.post("/trigger")
async def trigger_sync(current_user: dict = Depends(get_current_user)):
    """Trigger an immediate sync cycle."""
    service = get_sync_service()
    if not service.is_enabled():
        raise HTTPException(status_code=400, detail="Sync is not enabled")
    try:
        result = await service.run_sync()
        return {
            "success": result.success,
            "pushed": result.pushed,
            "pulled": result.pulled,
            "conflicts": result.conflicts,
            "errors": result.errors,
        }
    except Exception as exc:
        logger.exception("Sync trigger failed")
        raise HTTPException(status_code=500, detail=str(exc)) from None


@router.get("/conflicts")
async def list_conflicts(current_user: dict = Depends(get_current_user)):
    """List unresolved sync conflicts."""
    conflicts = get_conflicts(unresolved_only=True)
    return {"conflicts": [c.__dict__ for c in conflicts]}


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: int,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Resolve a sync conflict."""
    resolution = str(payload.get("resolution", "")).strip().lower()
    if resolution not in ("local", "remote"):
        raise HTTPException(status_code=422, detail="resolution must be 'local' or 'remote'")
    resolved_data = payload.get("resolved_data", {})
    reason = str(payload.get("reason", ""))
    conflicts = get_conflicts(unresolved_only=False)
    conflict_ids = [c.id for c in conflicts]
    if conflict_id not in conflict_ids:
        raise HTTPException(status_code=404, detail="Conflict not found")
    try:
        resolve_conflict_db(
            conflict_id=conflict_id,
            resolution=resolution,
            resolved_data=resolved_data,
            reason=reason,
        )
        return {"status": "resolved"}
    except Exception as exc:
        logger.exception("Failed to resolve conflict %d", conflict_id)
        raise HTTPException(status_code=500, detail=str(exc)) from None
