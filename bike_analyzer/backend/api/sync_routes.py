"""REST API endpoints for sync management.

These endpoints are called by the frontend to control and monitor
the optional bidirectional sync service. They do NOT implement the
cloud sync protocol itself — they manage the local sync orchestrator.

Cloud endpoints (GET/POST /sync/check, /sync/push, /sync/pull) are
called by the SyncClient inside the sync service, not exposed here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..security import get_current_user
from ..sync.config import SyncMode, SyncSettings, get_sync_config, load_sync_config, save_sync_config
from ..sync.db_helpers import get_conflicts, get_pending_entities, get_last_sync_ts
from ..sync.models import ConflictRecord, SyncResult
from ..sync.service import get_sync_service
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class SyncSettingsUpdate(BaseModel):
    mode: str | None = Field(default=None, pattern="^(never|manual|daily|weekly|realtime)$")
    daily_hour: int | None = Field(default=None, ge=0, le=23)
    weekly_day: int | None = Field(default=None, ge=0, le=6)
    cloud_url: str | None = Field(default=None, max_length=500)
    auth_token: str | None = Field(default=None, max_length=500)
    device_id: str | None = Field(default=None, max_length=100)
    enabled_entities: list[str] | None = None
    auto_sync_on_startup: bool | None = None


class ConflictResolutionRequest(BaseModel):
    resolution: str = Field(..., pattern="^(local|remote)$")
    reason: str | None = Field(default=None, max_length=500)


class SyncStatusResponse(BaseModel):
    mode: str
    enabled: bool
    last_sync_ts: str | None
    pending_count: int
    conflict_count: int
    cloud_connected: bool


# ---------------------------------------------------------------------------
# Status & configuration
# ---------------------------------------------------------------------------

@router.get("/sync/status")
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    """Return current sync configuration and status."""
    from ..sync.db_helpers import get_conflicts, get_pending_entities, get_last_sync_ts

    config = get_sync_config()
    pending = get_pending_entities()
    conflicts = get_conflicts(unresolved_only=True)
    client = get_sync_service().client
    cloud_connected = False
    if client is not None:
        try:
            health = await client.health()
            cloud_connected = health.get("status") == "ok"
        except Exception:
            pass

    return SyncStatusResponse(
        mode=config.mode.value,
        enabled=config.mode != SyncMode.NEVER and bool(config.cloud_url),
        last_sync_ts=get_last_sync_ts(),
        pending_count=len(pending),
        conflict_count=len(conflicts),
        cloud_connected=cloud_connected,
    ).model_dump()


@router.get("/sync/settings")
async def get_sync_settings(current_user: dict = Depends(get_current_user)):
    """Return current sync settings."""
    config = get_sync_config()
    return config.to_dict()


@router.put("/sync/settings")
async def update_sync_settings(
    updates: SyncSettingsUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update sync settings."""
    config = get_sync_config()
    update_data = updates.model_dump(exclude_none=True)

    if "mode" in update_data:
        try:
            config.mode = SyncMode(update_data["mode"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid sync mode")

    if "daily_hour" in update_data:
        config.daily_hour = update_data["daily_hour"]
    if "weekly_day" in update_data:
        config.weekly_day = update_data["weekly_day"]
    if "cloud_url" in update_data:
        config.cloud_url = update_data["cloud_url"]
    if "auth_token" in update_data:
        config.auth_token = update_data["auth_token"]
    if "device_id" in update_data:
        config.device_id = update_data["device_id"]
    if "enabled_entities" in update_data:
        config.enabled_entities = update_data["enabled_entities"]
    if "auto_sync_on_startup" in update_data:
        config.auto_sync_on_startup = update_data["auto_sync_on_startup"]

    save_sync_config(config)
    return config.to_dict()


# ---------------------------------------------------------------------------
# Sync execution
# ---------------------------------------------------------------------------

@router.post("/sync/trigger")
async def trigger_sync(current_user: dict = Depends(get_current_user)):
    """Trigger a manual sync cycle."""
    service = get_sync_service()
    if not service.is_enabled():
        raise HTTPException(status_code=400, detail="Sync is not enabled. Configure cloud_url and set mode != 'never'.")
    result = await service.run_sync()
    return _sync_result_to_dict(result)


@router.post("/sync/trigger-background")
async def trigger_sync_background(current_user: dict = Depends(get_current_user)):
    """Trigger sync in the background (non-blocking)."""
    service = get_sync_service()
    if not service.is_enabled():
        raise HTTPException(status_code=400, detail="Sync is not enabled.")
    import asyncio

    asyncio.create_task(service.run_sync())
    return {"status": "scheduled"}


# ---------------------------------------------------------------------------
# Conflict management
# ---------------------------------------------------------------------------

@router.get("/sync/conflicts")
async def list_conflicts(current_user: dict = Depends(get_current_user)):
    """List all unresolved sync conflicts."""
    from ..sync.db_helpers import get_conflicts

    conflicts = get_conflicts(unresolved_only=True)
    return {
        "conflicts": [
            {
                "id": i + 1,
                "entity_type": c.entity_type,
                "entity_id": c.entity_id,
                "local_data": _safe_preview(c.local_data),
                "remote_data": _safe_preview(c.remote_data),
                "local_reliability": c.local_reliability,
                "remote_reliability": c.remote_reliability,
                "local_modified": c.local_modified,
                "remote_modified": c.remote_modified,
                "resolution": c.resolution,
            }
            for i, c in enumerate(conflicts)
        ]
    }


@router.post("/sync/conflicts/{conflict_index}/resolve")
async def resolve_conflict_endpoint(
    conflict_index: int,
    request: ConflictResolutionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resolve a specific conflict (user chooses local or remote)."""
    from ..sync.db_helpers import get_conflicts

    conflicts = get_conflicts(unresolved_only=True)
    if conflict_index < 0 or conflict_index >= len(conflicts):
        raise HTTPException(status_code=404, detail="Conflict not found")

    conflict = conflicts[conflict_index]
    side = request.resolution  # 'local' or 'remote'
    if side not in ("local", "remote"):
        raise HTTPException(status_code=400, detail="Resolution must be 'local' or 'remote'")

    chosen_data = conflict.local_data if side == "local" else conflict.remote_data
    from ..sync.service import _write_local_entity

    _write_local_entity(conflict.entity_type, conflict.entity_id, chosen_data)
    from ..sync.db_helpers import mark_synced, resolve_conflict_db

    mark_synced(conflict.entity_type, conflict.entity_id)
    resolve_conflict_db(
        conflict_id=conflict_index + 1,
        resolution=side,
        resolved_data=chosen_data,
        reason=request.reason or f"User resolved: {side}",
    )
    return {"resolved": True, "resolution": side}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_result_to_dict(result: SyncResult) -> dict[str, Any]:
    return {
        "success": result.success,
        "mode": result.mode,
        "pushed": result.pushed,
        "pulled": result.pulled,
        "conflicts": result.conflicts,
        "errors": result.errors,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


def _safe_preview(data: dict[str, Any], max_len: int = 200) -> dict[str, Any]:
    """Truncate long string values for API responses."""
    preview = {}
    for k, v in data.items():
        if isinstance(v, str) and len(v) > max_len:
            preview[k] = v[:max_len] + "..."
        elif isinstance(v, dict):
            preview[k] = _safe_preview(v, max_len)
        else:
            preview[k] = v
    return preview


__all__ = ["router"]
