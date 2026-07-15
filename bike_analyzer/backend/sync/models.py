"""Data models for the sync service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .config import EntityType, SyncDirection


class SyncStatus(str, Enum):
    """Per-entity sync state."""

    LOCAL = "local"
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class SyncEntityState:
    """Tracks sync state for a single entity row."""

    entity_type: str
    entity_id: int
    source: str = "device"
    reliability_score: float = 1.0
    last_modified: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    sync_status: SyncStatus = SyncStatus.LOCAL
    sync_error: str | None = None
    cloud_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ChangeDelta:
    """A batch of local changes to push to the cloud."""

    entity_type: str
    entity_id: int
    operation: str  # 'create' | 'update' | 'delete'
    data: dict[str, Any]
    source: str = "device"
    reliability_score: float = 1.0
    last_modified: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    external_source: str | None = None
    external_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "operation": self.operation,
            "data": self.data,
            "source": self.source,
            "reliability_score": self.reliability_score,
            "last_modified": self.last_modified,
            "external_source": self.external_source,
            "external_id": self.external_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeDelta:
        return cls(
            entity_type=str(data.get("entity_type", "")),
            entity_id=int(data.get("entity_id", 0)),
            operation=str(data.get("operation", "update")),
            data=dict(data.get("data", {})),
            source=str(data.get("source", "device")),
            reliability_score=float(data.get("reliability_score", 1.0)),
            last_modified=str(data.get("last_modified", datetime.now(UTC).isoformat())),
            external_source=data.get("external_source"),
            external_id=data.get("external_id"),
        )


@dataclass
class ConflictRecord:
    """A merge conflict between local and remote data."""

    entity_type: str
    entity_id: int
    local_data: dict[str, Any]
    remote_data: dict[str, Any]
    local_reliability: float
    remote_reliability: float
    local_modified: str
    remote_modified: str
    resolution: str = "unresolved"  # 'local' | 'remote' | 'unresolved'
    resolved_data: dict[str, Any] | None = None
    resolution_reason: str = ""


@dataclass
class SyncCheckResult:
    """Response from GET /sync/check."""

    last_sync_ts: str | None
    server_changes_count: int
    server_changes: list[dict[str, Any]] = field(default_factory=list)
    server_version: str | None = None


@dataclass
class SyncPushResult:
    """Response from POST /sync/push."""

    accepted: int
    conflicts: list[ConflictRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Aggregate result of a full sync cycle."""

    success: bool
    mode: str
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str | None = None


class ConflictResolution:
    """Constants for conflict resolution outcomes."""

    LOCAL_WINS = "local"
    REMOTE_WINS = "remote"
    UNRESOLVED = "unresolved"


__all__ = [
    "SyncStatus",
    "SyncEntityState",
    "ChangeDelta",
    "ConflictRecord",
    "SyncCheckResult",
    "SyncPushResult",
    "SyncResult",
    "ConflictResolution",
    "EntityType",
    "SyncDirection",
]
