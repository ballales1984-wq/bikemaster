"""Main sync service orchestrator.

Implements the full bidirectional sync cycle:
1. check  – query cloud for changes since last sync
2. push   – send local deltas to cloud
3. pull   – receive remote changes and merge locally
4. resolve – handle any conflicts using reliability_score + last_modified

Sync is always optional: any cloud error is caught and logged without
affecting local operation.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from ..utils.logger import get_logger
from .client import SyncClient
from .config import (
    SyncMode,
    get_sync_config,
)
from .conflict_resolver import ConflictResolution, resolve_conflict
from .db_helpers import (
    ensure_sync_tables,
    get_conflicts,
    get_entity_state,
    get_last_sync_ts,
    get_pending_entities,
    mark_conflict,
    mark_error,
    mark_synced,
    resolve_conflict_db,
    save_conflict,
    set_last_sync_ts,
    upsert_entity_state,
)
from .models import (
    ChangeDelta,
    ConflictRecord,
    SyncCheckResult,
    SyncEntityState,
    SyncResult,
    SyncStatus,
)

logger = get_logger(__name__)

_sync_service: SyncService | None = None
_sync_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _sync_lock
    if _sync_lock is None:
        _sync_lock = asyncio.Lock()
    return _sync_lock


def get_sync_service() -> SyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service


class SyncService:
    """Orchestrates bidirectional sync between local SQLite and cloud PostgreSQL."""

    def __init__(self) -> None:
        self._client: SyncClient | None = None
        self._scheduled_task: asyncio.Task | None = None
        self._running = False

    @property
    def client(self) -> SyncClient | None:
        if self._client is None:
            config = get_sync_config()
            if config.cloud_url and config.auth_token:
                self._client = SyncClient(
                    base_url=config.cloud_url,
                    auth_token=config.auth_token,
                )
        return self._client

    def is_enabled(self) -> bool:
        config = get_sync_config()
        return config.mode != SyncMode.NEVER and bool(config.cloud_url)

    async def start(self) -> None:
        if self._running:
            return
        ensure_sync_tables()
        config = get_sync_config()
        if config.auto_sync_on_startup and self.is_enabled():
            asyncio.create_task(self._auto_sync())
        if config.mode in (SyncMode.DAILY, SyncMode.WEEKLY):
            self._running = True
            self._scheduled_task = asyncio.create_task(self._schedule_loop())
        logger.info("Sync service started (mode=%s)", config.mode.value)

    async def stop(self) -> None:
        self._running = False
        if self._scheduled_task:
            self._scheduled_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduled_task
            self._scheduled_task = None
        logger.info("Sync service stopped")

    async def run_sync(self) -> SyncResult:
        """Execute a full sync cycle (check → push → pull → resolve)."""
        config = get_sync_config()
        result = SyncResult(success=True, mode=config.mode.value)
        started = datetime.now(UTC)

        if not self.is_enabled():
            result.finished_at = datetime.now(UTC).isoformat()
            return result

        async with _get_lock():
            try:
                await self._push_phase(result)
                await self._pull_phase(result)
                await self._resolve_phase(result)
                if not result.errors:
                    set_last_sync_ts(datetime.now(UTC).isoformat())
            except Exception as exc:
                logger.exception("Sync cycle failed")
                result.success = False
                result.errors.append(str(exc))

        result.finished_at = datetime.now(UTC).isoformat()
        logger.info(
            "Sync complete: pushed=%d pulled=%d conflicts=%d errors=%d",
            result.pushed, result.pulled, result.conflicts, len(result.errors),
        )
        return result

    async def _push_phase(self, result: SyncResult) -> None:
        client = self.client
        if client is None:
            return

        pending = _get_pushable_entities()
        if not pending:
            return

        deltas = [_build_delta(entity) for entity in pending if _build_delta(entity) is not None]
        if not deltas:
            return

        push_result = await client.push(deltas)
        if isinstance(push_result, dict) and "error" in push_result:
            result.errors.append(f"push: {push_result['error']}")
            for d in deltas:
                mark_error(d.entity_type, d.entity_id, push_result["error"])
            return

        result.pushed = push_result.accepted
        for delta in deltas:
            mark_synced(delta.entity_type, delta.entity_id)
        for conflict in push_result.conflicts:
            save_conflict(conflict)
            mark_conflict(conflict.entity_type, conflict.entity_id, "Server returned conflict")
            result.conflicts += 1
        for err in push_result.errors:
            result.errors.append(f"push: {err}")

    async def _pull_phase(self, result: SyncResult) -> None:
        client = self.client
        if client is None:
            return

        last_ts = get_last_sync_ts()
        check = await client.check(last_ts)
        if isinstance(check, dict) and "error" in check:
            result.errors.append(f"check: {check['error']}")
            return
        if not isinstance(check, SyncCheckResult):
            return
        if not check.server_changes:
            return

        pull_result = await client.pull(since=last_ts)
        if isinstance(pull_result, dict) and "error" in pull_result:
            result.errors.append(f"pull: {pull_result['error']}")
            return
        if not isinstance(pull_result, list):
            return

        for change in pull_result:
            await self._apply_remote_change(change, result)

    async def _apply_remote_change(self, change: dict[str, Any], result: SyncResult) -> None:
        entity_type = str(change.get("entity_type", ""))
        entity_id = int(change.get("entity_id", 0))
        if not entity_type or not entity_id:
            return

        existing_state = get_entity_state(entity_type, entity_id)
        if existing_state and existing_state.sync_status == SyncStatus.CONFLICT:
            return

        remote_data = dict(change.get("data", {}))
        remote_rel = float(change.get("reliability_score", 0.5))
        remote_modified = str(change.get("last_modified", ""))

        if existing_state:
            local_data = _load_local_entity(entity_type, entity_id)
            if local_data:
                conflict = ConflictRecord(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    local_data=local_data,
                    remote_data=remote_data,
                    local_reliability=existing_state.reliability_score,
                    remote_reliability=remote_rel,
                    local_modified=existing_state.last_modified,
                    remote_modified=remote_modified,
                )
                resolution = resolve_conflict(conflict)
                if resolution.needs_user_review:
                    save_conflict(
                        ConflictRecord(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            local_data=local_data,
                            remote_data=remote_data,
                            local_reliability=existing_state.reliability_score,
                            remote_reliability=remote_rel,
                            local_modified=existing_state.last_modified,
                            remote_modified=remote_modified,
                            resolution="unresolved",
                        )
                    )
                    mark_conflict(entity_type, entity_id, "Ambiguous merge")
                    result.conflicts += 1
                    return
                if resolution.resolution == ConflictResolution.REMOTE_WINS:
                    _write_local_entity(entity_type, entity_id, resolution.merged_data or remote_data)
                    _update_entity_state_after_merge(entity_type, entity_id, remote_rel, remote_modified)
                    result.pulled += 1
                else:
                    mark_synced(entity_type, entity_id, change.get("cloud_id"))
            else:
                _write_local_entity(entity_type, entity_id, remote_data)
                _update_entity_state_after_merge(entity_type, entity_id, remote_rel, remote_modified)
                result.pulled += 1
        else:
            _write_local_entity(entity_type, entity_id, remote_data)
            state = SyncEntityState(
                entity_type=entity_type,
                entity_id=entity_id,
                source=str(change.get("source", "cloud")),
                reliability_score=remote_rel,
                last_modified=remote_modified,
                sync_status=SyncStatus.SYNCED,
                cloud_id=change.get("cloud_id"),
            )
            upsert_entity_state(state)
            result.pulled += 1

    async def _resolve_phase(self, result: SyncResult) -> None:
        unresolved = get_conflicts(unresolved_only=True)
        if not unresolved:
            return

        resolver = resolve_conflict
        for conflict in unresolved:
            resolution = resolver(conflict)
            if resolution.needs_user_review:
                continue
            if resolution.resolution == ConflictResolution.LOCAL_WINS and resolution.merged_data:
                _write_local_entity(conflict.entity_type, conflict.entity_id, resolution.merged_data)
                mark_synced(conflict.entity_type, conflict.entity_id)
            elif resolution.resolution == ConflictResolution.REMOTE_WINS and resolution.merged_data:
                _write_local_entity(conflict.entity_type, conflict.entity_id, resolution.merged_data)
                mark_synced(conflict.entity_type, conflict.entity_id)
            resolve_conflict_db(
                conflict_id=_find_conflict_db_id(conflict),
                resolution=resolution.resolution,
                resolved_data=resolution.merged_data or {},
                reason=resolution.reason,
            )
            result.conflicts -= 1

    async def _auto_sync(self) -> None:
        await asyncio.sleep(5)
        await self.run_sync()

    async def _schedule_loop(self) -> None:
        while self._running:
            now = datetime.now(UTC)
            config = get_sync_config()
            should_sync = False
            if config.mode == SyncMode.DAILY and now.hour == config.daily_hour:
                should_sync = True
            elif config.mode == SyncMode.WEEKLY and now.weekday() == config.weekly_day and now.hour == config.daily_hour:
                should_sync = True
            if should_sync:
                try:
                    await self.run_sync()
                except Exception:
                    logger.exception("Scheduled sync failed")
            await asyncio.sleep(60)


def _get_pushable_entities() -> list[SyncEntityState]:
    config = get_sync_config()
    enabled = set(config.enabled_entities)
    pending = get_pending_entities()
    return [e for e in pending if e.entity_type in enabled]


def _build_delta(entity: SyncEntityState) -> ChangeDelta | None:
    try:
        data = _load_local_entity(entity.entity_type, entity.entity_id)
        if data is None:
            return None
        return ChangeDelta(
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            operation="update" if entity.sync_status == SyncStatus.SYNCED else "upsert",
            data=data,
            source=entity.source,
            reliability_score=entity.reliability_score,
            last_modified=entity.last_modified,
        )
    except Exception as exc:
        logger.debug("Failed to build delta for %s/%d: %s", entity.entity_type, entity.entity_id, exc)
        return None


def _load_local_entity(entity_type: str, entity_id: int) -> dict[str, Any] | None:
    try:
        from ..db.database import get_db_connection

        table_map = {
            "ride": "rides",
            "athlete": "athletes",
            "chat_message": "chat_history",
            "training_goal": "training_goals",
            "planned_workout": "planned_workouts",
            "fitness_state": "fitness_states",
            "calendar_event": "calendar_events",
            "poi": "pois",
        }
        table = table_map.get(entity_type)
        if not table:
            return None
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None
    except Exception as exc:
        logger.debug("Failed to load local entity %s/%d: %s", entity_type, entity_id, exc)
        return None


def _write_local_entity(entity_type: str, entity_id: int, data: dict[str, Any]) -> None:
    try:
        from ..db.database import get_db_connection

        table_map = {
            "ride": "rides",
            "athlete": "athletes",
            "chat_message": "chat_history",
            "training_goal": "training_goals",
            "planned_workout": "planned_workouts",
            "fitness_state": "fitness_states",
            "calendar_event": "calendar_events",
            "poi": "pois",
        }
        table = table_map.get(entity_type)
        if not table:
            return
        allowed_columns = {
            "ride": {
                "date",
                "distance_km",
                "duration_minutes",
                "avg_speed_kmh",
                "weight_kg",
                "calories",
                "heart_rate_avg",
                "elevation_gain_m",
                "gps_points",
                "external_source",
                "external_id",
                "title",
                "activity_type",
                "is_official",
                "source",
                "updated_at",
            },
            "athlete": {
                "name",
                "email",
                "picture",
                "age",
                "weight_kg",
                "height_cm",
                "fat_percentage",
                "years_active",
                "weekly_sessions",
                "monthly_hours",
                "annual_hours",
                "experience_level",
                "goals",
                "preferred_terrain",
                "weekly_volume_km",
                "best_segments",
                "medical_notes",
                "equipment",
                "ftp_watts",
                "body_water_percentage",
                "muscle_mass_percentage",
                "bmr_kcal",
                "fat_mass_kg",
                "subcutaneous_fat_kg",
                "subcutaneous_fat_percentage",
                "visceral_fat_level",
                "visceral_fat_percentage",
                "visceral_fat_kg",
                "muscle_mass_kg",
                "bone_mass_kg",
                "protein_percentage",
                "protein_kg",
                "body_age",
                "apparent_age",
                "bmi",
                "lean_body_mass_kg",
            },
            "chat_message": {"role", "content", "created_at"},
            "training_goal": {
                "title",
                "description",
                "goal_type",
                "target_date",
                "target_distance_km",
                "target_elevation_m",
                "status",
                "created_at",
            },
            "planned_workout": {
                "date",
                "title",
                "workout_type",
                "duration_minutes",
                "target_intensity",
                "completed",
                "completed_at",
            },
            "fitness_state": {
                "date",
                "computed_at",
                "fitness",
                "fatigue",
                "form",
                "atl",
                "ctl",
                "tsb",
                "recovery_hours_needed",
                "weekly_tss",
                "monthly_tss",
                "trend_7d",
                "trend_30d",
                "risk_indicators",
                "recommendation",
            },
            "calendar_event": {
                "title",
                "event_type",
                "date",
                "duration_minutes",
                "description",
                "completed",
                "weather_temp",
                "weather_humidity",
                "weather_description",
                "created_at",
            },
            "poi": {
                "name",
                "description",
                "lat",
                "lon",
                "type",
                "photos",
                "video_url",
                "difficulty_note",
                "tags",
                "itinerary_id",
                "created_by",
                "tenant_id",
                "created_at",
            },
        }
        allowed = allowed_columns.get(entity_type, set())
        cols = [k for k in data.keys() if k != "id" and k in allowed]
        if not cols:
            return
        placeholders = ", ".join("?" * len(cols))
        col_names = ", ".join(cols)
        values = [data[c] for c in cols]
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT OR REPLACE INTO {table} (id, {col_names}) VALUES (?, {placeholders})",
                (entity_id, *values),
            )
            conn.commit()
    except Exception as exc:
        logger.debug("Failed to write local entity %s/%d: %s", entity_type, entity_id, exc)


def _update_entity_state_after_merge(
    entity_type: str, entity_id: int, reliability: float, last_modified: str
) -> None:
    state = get_entity_state(entity_type, entity_id)
    if state is None:
        state = SyncEntityState(
            entity_type=entity_type,
            entity_id=entity_id,
            sync_status=SyncStatus.SYNCED,
        )
    state.reliability_score = max(state.reliability_score, reliability)
    state.last_modified = last_modified
    state.sync_status = SyncStatus.SYNCED
    state.sync_error = None
    state.updated_at = datetime.now(UTC).isoformat()
    upsert_entity_state(state)


def _find_conflict_db_id(conflict: ConflictRecord) -> int:
    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM sync_conflicts WHERE entity_type = ? AND entity_id = ? AND resolution = 'unresolved' LIMIT 1",
            (conflict.entity_type, conflict.entity_id),
        )
        row = cur.fetchone()
        return row["id"] if row else 0


import contextlib

__all__ = ["SyncService", "get_sync_service"]
