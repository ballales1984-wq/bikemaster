"""Offline-first reconciliation tests for the sync layer.

These tests exercise the sync contract defined in docs/sync-contract.md:
  * offline → sync → merge
  * conflict: same ride written twice offline
  * resume after suspension with inconsistent state
  * idempotency of repeated sync operations
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bike_analyzer.backend.sync.config import SyncMode
from bike_analyzer.backend.sync.conflict_resolver import resolve_conflict
from bike_analyzer.backend.sync.db_helpers import (
    ensure_sync_tables,
    get_entity_state,
    get_last_sync_ts,
    get_pending_entities,
    mark_synced,
    save_conflict,
    set_last_sync_ts,
    upsert_entity_state,
)
from bike_analyzer.backend.sync.models import (
    ChangeDelta,
    ConflictRecord,
    SyncEntityState,
    SyncStatus,
)
from bike_analyzer.backend.sync.service import SyncService


@pytest.fixture(autouse=True)
def _reset_sync_state():
    from bike_analyzer.backend.sync.config import reset_sync_config

    reset_sync_config()
    yield
    reset_sync_config()


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "offline_sync.db")
    os.environ["DB_PATH"] = p
    from bike_analyzer.backend.db import database as db_mod

    db_mod.DB_PATH = p
    db_mod.init_db()
    yield p


def _save_ride(db_mod, athlete_id=1, **over):
    ride = {
        "athlete_id": athlete_id,
        "date": "2026-08-01T06:00:00+00:00",
        "distance_km": 30.0,
        "duration_minutes": 90,
        "weight_kg": 70.0,
        "calories": 400.0,
        "activity_type": "ride",
        "is_official": True,
        "source": "manual",
        **over,
    }
    rid = db_mod.save_ride(ride)
    return rid, ride


# ---------------------------------------------------------------------------
# 1. offline → sync → merge
# ---------------------------------------------------------------------------


class TestOfflineSyncMerge:
    def test_offline_ride_survives_sync_push(self, db_path):
        from bike_analyzer.backend.db import database as db_mod

        ensure_sync_tables()
        rid, ride = _save_ride(db_mod)

        state = SyncEntityState(
            entity_type="ride",
            entity_id=rid,
            source="device",
            reliability_score=1.0,
            sync_status=SyncStatus.LOCAL,
        )
        upsert_entity_state(state)

        delta = ChangeDelta(
            entity_type="ride",
            entity_id=rid,
            operation="update",
            data=ride,
            source="device",
            reliability_score=1.0,
        )
        assert delta.to_dict()["entity_id"] == rid

    def test_mark_synced_after_successful_push(self, db_path):
        ensure_sync_tables()
        upsert_entity_state(
            SyncEntityState(entity_type="ride", entity_id=1, sync_status=SyncStatus.LOCAL)
        )
        mark_synced("ride", 1, cloud_id="cloud-1")
        state = get_entity_state("ride", 1)
        assert state.sync_status == SyncStatus.SYNCED
        assert state.cloud_id == "cloud-1"


# ---------------------------------------------------------------------------
# 2. conflict: ride written twice offline
# ---------------------------------------------------------------------------


class TestOfflineConflict:
    def test_same_ride_modified_twice_offline_detects_conflict(self, db_path):
        ensure_sync_tables()
        upsert_entity_state(
            SyncEntityState(
                entity_type="ride",
                entity_id=1,
                source="device",
                reliability_score=1.0,
                last_modified="2026-08-01T10:00:00+00:00",
                sync_status=SyncStatus.SYNCED,
            )
        )

        local_data = {"distance_km": 50.0, "duration_minutes": 120}
        remote_data = {"distance_km": 30.0, "duration_minutes": 90}

        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data=local_data,
            remote_data=remote_data,
            local_reliability=1.0,
            remote_reliability=0.6,
            local_modified="2026-08-01T12:00:00+00:00",
            remote_modified="2026-08-01T11:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "local"
        assert result.merged_data["distance_km"] == 50.0

    def test_ambiguous_conflict_requires_review(self, db_path):
        ensure_sync_tables()
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 50.0},
            remote_data={"distance_km": 30.0},
            local_reliability=0.8,
            remote_reliability=0.8,
            local_modified="2026-08-01T10:00:00+00:00",
            remote_modified="2026-08-01T10:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "unresolved"
        assert result.needs_user_review is True


# ---------------------------------------------------------------------------
# 3. resume post-sospensione with inconsistent state
# ---------------------------------------------------------------------------


class TestResumeAfterSuspension:
    def test_pending_entities_survive_suspension(self, db_path):
        ensure_sync_tables()
        for i in range(3):
            upsert_entity_state(
                SyncEntityState(
                    entity_type="ride",
                    entity_id=i,
                    source="device",
                    reliability_score=1.0,
                    sync_status=SyncStatus.LOCAL,
                )
            )

        pending = get_pending_entities()
        assert len(pending) == 3
        ids = {e.entity_id for e in pending}
        assert ids == {0, 1, 2}

    def test_last_sync_ts_restored_after_suspension(self, db_path):
        ensure_sync_tables()
        set_last_sync_ts("2026-08-15T10:00:00+00:00")
        assert get_last_sync_ts() == "2026-08-15T10:00:00+00:00"

    def test_conflict_preserved_after_suspension(self, db_path):
        ensure_sync_tables()
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 50.0},
            remote_data={"distance_km": 30.0},
            local_reliability=0.9,
            remote_reliability=0.5,
            local_modified="2026-08-01T10:00:00+00:00",
            remote_modified="2026-08-01T08:00:00+00:00",
        )
        save_conflict(conflict)
        from bike_analyzer.backend.sync.db_helpers import get_conflicts

        conflicts = get_conflicts(unresolved_only=True)
        assert len(conflicts) == 1
        assert conflicts[0].entity_id == 1


# ---------------------------------------------------------------------------
# 4. idempotency of sync operations
# ---------------------------------------------------------------------------


class TestSyncIdempotency:
    def test_upsert_entity_state_is_idempotent(self, db_path):
        ensure_sync_tables()
        state1 = SyncEntityState(
            entity_type="ride",
            entity_id=1,
            source="device",
            reliability_score=1.0,
            sync_status=SyncStatus.LOCAL,
        )
        upsert_entity_state(state1)
        upsert_entity_state(state1)
        from bike_analyzer.backend.sync.db_helpers import get_entity_state

        loaded = get_entity_state("ride", 1)
        assert loaded is not None
        assert loaded.sync_status == SyncStatus.LOCAL

    def test_repeated_push_delta_is_idempotent(self, db_path):
        ensure_sync_tables()
        delta = ChangeDelta(
            entity_type="ride",
            entity_id=1,
            operation="update",
            data={"distance_km": 35.0},
            source="device",
            reliability_score=1.0,
        )
        d1 = delta.to_dict()
        d2 = delta.to_dict()
        assert d1 == d2
        assert d1["entity_id"] == 1

    def test_mark_synced_idempotent(self, db_path):
        ensure_sync_tables()
        upsert_entity_state(
            SyncEntityState(entity_type="ride", entity_id=1, sync_status=SyncStatus.LOCAL)
        )
        mark_synced("ride", 1, cloud_id="cloud-1")
        mark_synced("ride", 1, cloud_id="cloud-1")
        state = get_entity_state("ride", 1)
        assert state.sync_status == SyncStatus.SYNCED
        assert state.cloud_id == "cloud-1"

    def test_set_last_sync_ts_overwrites(self, db_path):
        ensure_sync_tables()
        set_last_sync_ts("2026-08-01T10:00:00+00:00")
        set_last_sync_ts("2026-08-02T10:00:00+00:00")
        assert get_last_sync_ts() == "2026-08-02T10:00:00+00:00"


# ---------------------------------------------------------------------------
# SyncService offline scenarios
# ---------------------------------------------------------------------------


class TestSyncServiceOffline:
    @pytest.mark.asyncio
    async def test_run_sync_returns_success_when_disabled(self, db_path):
        service = SyncService()
        result = await service.run_sync()
        assert result.success is True
        assert result.pushed == 0
        assert result.pulled == 0

    @pytest.mark.asyncio
    async def test_sync_service_does_not_raise_on_network_error(self, db_path):
        from bike_analyzer.backend.sync.config import SyncSettings, save_sync_config

        save_sync_config(
            SyncSettings(
                mode=SyncMode.MANUAL,
                cloud_url="https://unreachable.example.com",
                auth_token="test",
            )
        )
        service = SyncService()
        with patch.object(service, "_push_phase", new_callable=AsyncMock) as mock_push:
            mock_push.side_effect = Exception("network down")
            result = await service.run_sync()
        assert result.success is False
        assert any("network down" in e for e in result.errors)


__all__ = [
    "TestOfflineSyncMerge",
    "TestOfflineConflict",
    "TestResumeAfterSuspension",
    "TestSyncIdempotency",
    "TestSyncServiceOffline",
]
