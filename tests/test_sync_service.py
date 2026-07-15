"""Tests for the optional bidirectional sync service."""

from __future__ import annotations

import json
import os
import time

import pytest

from bike_analyzer.backend.sync.config import (
    SyncMode,
    SyncSettings,
    get_sync_config,
    load_sync_config,
    reset_sync_config,
    save_sync_config,
)
from bike_analyzer.backend.sync.conflict_resolver import (
    ConflictResolver,
    ResolutionResult,
    resolve_conflict,
)
from bike_analyzer.backend.sync.db_helpers import (
    ensure_sync_tables,
    get_conflicts,
    get_entity_state,
    get_last_sync_ts,
    get_pending_entities,
    mark_conflict,
    mark_error,
    mark_pending,
    mark_synced,
    save_conflict,
    set_last_sync_ts,
    upsert_entity_state,
)
from bike_analyzer.backend.sync.models import (
    ChangeDelta,
    ConflictRecord,
    EntityType,
    SyncCheckResult,
    SyncEntityState,
    SyncStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_sync_state():
    reset_sync_config()
    yield
    reset_sync_config()


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "sync_test.db")
    os.environ["DB_PATH"] = p
    from bike_analyzer.backend.db import database as db_mod
    db_mod.DB_PATH = p
    db_mod.init_db()
    yield p


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestSyncConfig:
    def test_default_is_never(self):
        config = load_sync_config()
        assert config.mode == SyncMode.NEVER

    def test_save_and_load(self):
        settings = SyncSettings(
            mode=SyncMode.DAILY,
            daily_hour=3,
            cloud_url="https://cloud.example.com",
            auth_token="test-token",
        )
        save_sync_config(settings)
        loaded = load_sync_config()
        assert loaded.mode == SyncMode.DAILY
        assert loaded.daily_hour == 3
        assert loaded.cloud_url == "https://cloud.example.com"
        assert loaded.auth_token == "test-token"

    def test_reset(self):
        settings = SyncSettings(mode=SyncMode.WEEKLY)
        save_sync_config(settings)
        reset_sync_config()
        config = load_sync_config()
        assert config.mode == SyncMode.NEVER

    def test_roundtrip_preserves_enabled_entities(self):
        settings = SyncSettings(
            mode=SyncMode.REALTIME,
            enabled_entities=["ride", "athlete"],
        )
        save_sync_config(settings)
        loaded = load_sync_config()
        assert loaded.enabled_entities == ["ride", "athlete"]

    def test_invalid_mode_falls_back_to_never(self):
        from bike_analyzer.backend.sync.config import SyncSettings
        settings = SyncSettings.from_dict({"mode": "invalid_mode"})
        assert settings.mode == SyncMode.NEVER

    def test_get_sync_config_returns_settings(self):
        config = get_sync_config()
        assert isinstance(config, SyncSettings)
        assert config.mode == SyncMode.NEVER


# ---------------------------------------------------------------------------
# Conflict resolver tests
# ---------------------------------------------------------------------------

class TestConflictResolver:
    def test_local_wins_higher_reliability(self):
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 50.0},
            remote_data={"distance_km": 30.0},
            local_reliability=0.95,
            remote_reliability=0.60,
            local_modified="2026-07-15T10:00:00+00:00",
            remote_modified="2026-07-15T08:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "local"
        assert result.merged_data["distance_km"] == 50.0

    def test_remote_wins_higher_reliability(self):
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 30.0},
            remote_data={"distance_km": 50.0},
            local_reliability=0.50,
            remote_reliability=0.95,
            local_modified="2026-07-15T10:00:00+00:00",
            remote_modified="2026-07-15T08:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "remote"
        assert result.merged_data["distance_km"] == 50.0

    def test_tie_broken_by_last_modified(self):
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 30.0},
            remote_data={"distance_km": 50.0},
            local_reliability=0.80,
            remote_reliability=0.80,
            local_modified="2026-07-15T12:00:00+00:00",
            remote_modified="2026-07-15T10:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "local"
        assert result.merged_data["distance_km"] == 30.0

    def test_equal_reliability_and_modified_needs_review(self):
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 30.0},
            remote_data={"distance_km": 50.0},
            local_reliability=0.80,
            remote_reliability=0.80,
            local_modified="2026-07-15T10:00:00+00:00",
            remote_modified="2026-07-15T10:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "unresolved"
        assert result.needs_user_review is True

    def test_field_level_merge_when_non_overlapping(self):
        conflict = ConflictRecord(
            entity_type="athlete",
            entity_id=1,
            local_data={"name": "Alice", "ftp_watts": 250.0},
            remote_data={"name": "Alice", "weight_kg": 70.0},
            local_reliability=0.80,
            remote_reliability=0.80,
            local_modified="2026-07-15T10:00:00+00:00",
            remote_modified="2026-07-15T10:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "unresolved"
        assert result.merged_data is not None
        assert result.merged_data["name"] == "Alice"
        assert result.merged_data.get("ftp_watts") == 250.0

    def test_authoritative_local_wins(self):
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"distance_km": 30.0},
            remote_data={"distance_km": 50.0},
            local_reliability=0.95,
            remote_reliability=0.50,
            local_modified="2026-07-15T10:00:00+00:00",
            remote_modified="2026-07-15T12:00:00+00:00",
        )
        result = resolve_conflict(conflict)
        assert result.resolution == "local"
        assert result.merged_data["distance_km"] == 30.0

    def test_resolver_batch(self):
        resolver = ConflictResolver()
        conflicts = [
            ConflictRecord(
                entity_type="ride", entity_id=i,
                local_data={"v": 1}, remote_data={"v": 2},
                local_reliability=0.9, remote_reliability=0.5,
                local_modified="2026-07-15T10:00:00+00:00",
                remote_modified="2026-07-15T08:00:00+00:00",
            )
            for i in range(3)
        ]
        results = resolver.resolve_batch(conflicts)
        assert len(results) == 3
        assert all(r.resolution == "local" for r in results)


# ---------------------------------------------------------------------------
# DB helpers tests
# ---------------------------------------------------------------------------

class TestDbHelpers:
    def test_ensure_sync_tables(self, db_path):
        ensure_sync_tables()
        from bike_analyzer.backend.db.database import get_db_connection
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_entity_state'")
            assert cur.fetchone() is not None
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_settings'")
            assert cur.fetchone() is not None
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_conflicts'")
            assert cur.fetchone() is not None

    def test_upsert_and_get_entity_state(self, db_path):
        ensure_sync_tables()
        state = SyncEntityState(
            entity_type="ride",
            entity_id=42,
            source="device",
            reliability_score=0.9,
            sync_status=SyncStatus.LOCAL,
        )
        upsert_entity_state(state)
        loaded = get_entity_state("ride", 42)
        assert loaded is not None
        assert loaded.entity_id == 42
        assert loaded.source == "device"
        assert loaded.reliability_score == 0.9
        assert loaded.sync_status == SyncStatus.LOCAL

    def test_mark_synced(self, db_path):
        ensure_sync_tables()
        state = SyncEntityState(entity_type="ride", entity_id=1)
        upsert_entity_state(state)
        mark_synced("ride", 1, cloud_id="cloud-42")
        loaded = get_entity_state("ride", 1)
        assert loaded.sync_status == SyncStatus.SYNCED
        assert loaded.cloud_id == "cloud-42"

    def test_mark_pending(self, db_path):
        ensure_sync_tables()
        state = SyncEntityState(entity_type="ride", entity_id=1)
        upsert_entity_state(state)
        mark_pending("ride", 1)
        loaded = get_entity_state("ride", 1)
        assert loaded.sync_status == SyncStatus.PENDING

    def test_mark_conflict(self, db_path):
        ensure_sync_tables()
        state = SyncEntityState(entity_type="ride", entity_id=1)
        upsert_entity_state(state)
        mark_conflict("ride", 1, "version mismatch")
        loaded = get_entity_state("ride", 1)
        assert loaded.sync_status == SyncStatus.CONFLICT
        assert loaded.sync_error == "version mismatch"

    def test_mark_error(self, db_path):
        ensure_sync_tables()
        state = SyncEntityState(entity_type="ride", entity_id=1)
        upsert_entity_state(state)
        mark_error("ride", 1, "network error")
        loaded = get_entity_state("ride", 1)
        assert loaded.sync_status == SyncStatus.ERROR
        assert loaded.sync_error == "network error"

    def test_get_pending_entities(self, db_path):
        ensure_sync_tables()
        upsert_entity_state(SyncEntityState(entity_type="ride", entity_id=1, sync_status=SyncStatus.LOCAL))
        upsert_entity_state(SyncEntityState(entity_type="ride", entity_id=2, sync_status=SyncStatus.PENDING))
        upsert_entity_state(SyncEntityState(entity_type="ride", entity_id=3, sync_status=SyncStatus.SYNCED))
        pending = get_pending_entities()
        ids = {e.entity_id for e in pending}
        assert 1 in ids
        assert 2 in ids
        assert 3 not in ids

    def test_save_and_get_conflicts(self, db_path):
        ensure_sync_tables()
        conflict = ConflictRecord(
            entity_type="ride",
            entity_id=1,
            local_data={"v": 1},
            remote_data={"v": 2},
            local_reliability=0.9,
            remote_reliability=0.5,
            local_modified="2026-07-15T10:00:00+00:00",
            remote_modified="2026-07-15T08:00:00+00:00",
        )
        save_conflict(conflict)
        conflicts = get_conflicts(unresolved_only=True)
        assert len(conflicts) == 1
        assert conflicts[0].entity_id == 1

    def test_last_sync_ts(self, db_path):
        ensure_sync_tables()
        assert get_last_sync_ts() is None
        set_last_sync_ts("2026-07-15T10:00:00+00:00")
        assert get_last_sync_ts() == "2026-07-15T10:00:00+00:00"


# ---------------------------------------------------------------------------
# Models tests
# ---------------------------------------------------------------------------

class TestModels:
    def test_change_delta_roundtrip(self):
        delta = ChangeDelta(
            entity_type="ride",
            entity_id=42,
            operation="update",
            data={"distance_km": 50.0},
            source="device",
            reliability_score=0.95,
            last_modified="2026-07-15T10:00:00+00:00",
        )
        d = delta.to_dict()
        restored = ChangeDelta.from_dict(d)
        assert restored.entity_type == "ride"
        assert restored.entity_id == 42
        assert restored.data["distance_km"] == 50.0

    def test_sync_entity_state_defaults(self):
        state = SyncEntityState(entity_type="ride", entity_id=1)
        assert state.source == "device"
        assert state.reliability_score == 1.0
        assert state.sync_status == SyncStatus.LOCAL

    def test_sync_check_result(self):
        result = SyncCheckResult(
            last_sync_ts="2026-07-15T08:00:00+00:00",
            server_changes_count=3,
            server_changes=[{"type": "update"}],
        )
        assert result.server_changes_count == 3
        assert len(result.server_changes) == 1


# ---------------------------------------------------------------------------
# API routes tests
# ---------------------------------------------------------------------------

class TestSyncRoutes:
    def test_get_sync_status_requires_auth(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        from starlette.testclient import TestClient
        tc = TestClient(app)
        response = tc.get("/api/v1/sync/status")
        assert response.status_code == 401

    def test_get_sync_status_returns_data(self, db_path):
        from starlette.testclient import TestClient

        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"
        response = tc.get("/api/v1/sync/status")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "enabled" in data
        assert "pending_count" in data
        assert data["mode"] == "never"

    def test_update_sync_settings(self, db_path):
        from starlette.testclient import TestClient

        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"
        response = tc.put(
            "/api/v1/sync/settings",
            json={"mode": "daily", "daily_hour": 3, "cloud_url": "https://cloud.example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "daily"
        assert data["daily_hour"] == 3
        assert data["cloud_url"] == "https://cloud.example.com"

    def test_trigger_sync_disabled_returns_error(self, db_path):
        from starlette.testclient import TestClient

        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"
        response = tc.post("/api/v1/sync/trigger")
        assert response.status_code == 400

    def test_list_conflicts_empty(self, db_path):
        from starlette.testclient import TestClient

        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        db_mod.DB_PATH = db_path
        db_mod.init_db()
        app = create_app()
        tc = TestClient(app)
        token = create_access_token(subject="0", is_admin=True)
        tc.headers["Authorization"] = f"Bearer {token}"
        response = tc.get("/api/v1/sync/conflicts")
        assert response.status_code == 200
        data = response.json()
        assert data["conflicts"] == []


# ---------------------------------------------------------------------------
# SyncService integration test
# ---------------------------------------------------------------------------

class TestSyncService:
    @pytest.mark.asyncio
    async def test_service_disabled_by_default(self, db_path):
        from bike_analyzer.backend.sync.service import get_sync_service
        service = get_sync_service()
        assert not service.is_enabled()

    @pytest.mark.asyncio
    async def test_service_start_stop(self, db_path):
        from bike_analyzer.backend.sync.service import get_sync_service
        service = get_sync_service()
        await service.start()
        assert service._running is False  # mode=never, so no scheduled task
        await service.stop()

    @pytest.mark.asyncio
    async def test_run_sync_when_disabled(self, db_path):
        from bike_analyzer.backend.sync.service import get_sync_service
        service = get_sync_service()
        result = await service.run_sync()
        assert result.success is True
        assert result.pushed == 0
        assert result.pulled == 0


__all__ = [
    "TestSyncConfig",
    "TestConflictResolver",
    "TestDbHelpers",
    "TestModels",
    "TestSyncRoutes",
    "TestSyncService",
]


