"""Sync configuration – modes, defaults, and persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SyncMode(StrEnum):
    """User-controlled sync frequency."""

    NEVER = "never"
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    REALTIME = "realtime"


class SyncDirection(StrEnum):
    """Data flow direction for a given entity type."""

    BIDIRECTIONAL = "bidirectional"
    PUSH = "push"
    PULL = "pull"


class EntityType(StrEnum):
    """Entity categories eligible for sync."""

    RIDE = "ride"
    ATHLETE = "athlete"
    CHAT_MESSAGE = "chat_message"
    TRAINING_GOAL = "training_goal"
    PLANNED_WORKOUT = "planned_workout"
    FITNESS_STATE = "fitness_state"
    CALENDAR_EVENT = "calendar_event"
    POI = "poi"


# Entity → default sync direction (per deployment plan §3.3)
ENTITY_DIRECTIONS: dict[EntityType, SyncDirection] = {
    EntityType.RIDE: SyncDirection.PUSH,
    EntityType.ATHLETE: SyncDirection.BIDIRECTIONAL,
    EntityType.CHAT_MESSAGE: SyncDirection.PUSH,
    EntityType.TRAINING_GOAL: SyncDirection.PUSH,
    EntityType.PLANNED_WORKOUT: SyncDirection.PUSH,
    EntityType.FITNESS_STATE: SyncDirection.PUSH,
    EntityType.CALENDAR_EVENT: SyncDirection.PUSH,
    EntityType.POI: SyncDirection.PUSH,
}


@dataclass
class SyncSettings:
    """Persisted user sync preferences."""

    mode: SyncMode = SyncMode.NEVER
    daily_hour: int = 2
    weekly_day: int = 0
    cloud_url: str = ""
    auth_token: str = ""
    device_id: str = ""
    enabled_entities: list[str] = field(
        default_factory=lambda: [e.value for e in EntityType]
    )
    auto_sync_on_startup: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "daily_hour": self.daily_hour,
            "weekly_day": self.weekly_day,
            "cloud_url": self.cloud_url,
            "auth_token": self.auth_token,
            "device_id": self.device_id,
            "enabled_entities": self.enabled_entities,
            "auto_sync_on_startup": self.auto_sync_on_startup,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncSettings:
        mode = data.get("mode", SyncMode.NEVER.value)
        try:
            sync_mode = SyncMode(mode)
        except ValueError:
            sync_mode = SyncMode.NEVER
        return cls(
            mode=sync_mode,
            daily_hour=int(data.get("daily_hour", 2)),
            weekly_day=int(data.get("weekly_day", 0)),
            cloud_url=str(data.get("cloud_url", "")),
            auth_token=str(data.get("auth_token", "")),
            device_id=str(data.get("device_id", "")),
            enabled_entities=list(data.get("enabled_entities", [e.value for e in EntityType])),
            auto_sync_on_startup=bool(data.get("auto_sync_on_startup", False)),
        )


def _settings_table() -> dict[str, str]:
    return {}


_settings_cache: SyncSettings | None = None


def load_sync_config() -> SyncSettings:
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache
    try:
        from ..db.database import get_db_connection

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM sync_settings WHERE key = 'user_preferences'"
            )
            row = cur.fetchone()
            if row:
                data = json.loads(row["value"])
                if data.get("auth_token"):
                    try:
                        from ..db.token_crypto import decrypt_token
                        data["auth_token"] = decrypt_token(data["auth_token"])
                    except Exception:
                        pass
                _settings_cache = SyncSettings.from_dict(data)
                return _settings_cache
    except Exception:
        pass
    _settings_cache = SyncSettings()
    return _settings_cache


def save_sync_config(settings: SyncSettings) -> None:
    global _settings_cache
    _settings_cache = settings
    try:
        from ..db.database import get_db_connection

        data = settings.to_dict()
        if data.get("auth_token"):
            try:
                from ..db.token_crypto import encrypt_token
                data["auth_token"] = encrypt_token(data["auth_token"])
            except Exception:
                pass
        with get_db_connection() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS sync_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT
                )"""
            )
            conn.execute(
                "INSERT OR REPLACE INTO sync_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("user_preferences", json.dumps(data), _now_iso()),
            )
            conn.commit()
    except Exception as exc:
        logger.debug("Failed to persist sync settings: %s", exc)


def reset_sync_config() -> None:
    global _settings_cache
    _settings_cache = None
    try:
        from ..db.database import get_db_connection

        with get_db_connection() as conn:
            conn.execute("DELETE FROM sync_settings WHERE key = 'user_preferences'")
            conn.commit()
    except Exception:
        pass


def get_sync_config() -> SyncSettings:
    return load_sync_config()


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


__all__ = [
    "SyncMode",
    "SyncDirection",
    "EntityType",
    "SyncSettings",
    "ENTITY_DIRECTIONS",
    "load_sync_config",
    "save_sync_config",
    "get_sync_config",
    "reset_sync_config",
]
