"""Optional bidirectional sync service for BikeMaster.

Architecture:
    config.py      – SyncMode enum and user-configurable sync settings.
    models.py      – Data classes for sync records, deltas, and conflicts.
    db_helpers.py  – SQLite helpers for sync metadata tables.
    conflict_resolver.py – Conflict resolution using reliability_score + last_modified.
    client.py      – HTTP client for cloud sync API (push/pull/check).
    service.py     – Main sync orchestrator integrating all components.
    routes.py      – REST API endpoints for sync management (called by frontend).
"""

from __future__ import annotations

from .config import (
    SyncMode,
    SyncSettings,
    get_sync_config,
    load_sync_config,
    reset_sync_config,
    save_sync_config,
)
from .conflict_resolver import (
    ConflictResolution,
    ConflictResolver,
    resolve_conflict,
)
from .models import (
    ChangeDelta,
    ConflictRecord,
    EntityType,
    SyncCheckResult,
    SyncDirection,
    SyncEntityState,
    SyncPushResult,
    SyncResult,
)
from .service import SyncService, get_sync_service

__all__ = [
    "SyncMode",
    "SyncDirection",
    "EntityType",
    "SyncSettings",
    "SyncEntityState",
    "ChangeDelta",
    "ConflictRecord",
    "SyncCheckResult",
    "SyncPushResult",
    "SyncResult",
    "ConflictResolution",
    "SyncService",
    "get_sync_service",
    "load_sync_config",
    "save_sync_config",
    "get_sync_config",
    "reset_sync_config",
    "resolve_conflict",
    "ConflictResolver",
]
