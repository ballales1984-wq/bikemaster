"""Comprehensive tests for BLE device API endpoints.

Covers CRUD, sync, access control, tenant isolation, and schema validation
for /api/v1/api/v1/ble/devices.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


@pytest.fixture
def athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "BLE Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


@pytest.fixture
def admin_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    admin_id = db_mod.save_athlete({"name": "Admin", "experience_level": "Advanced"})
    db_mod.update_athlete(admin_id, {"tenant_id": admin_id, "is_admin": True})
    token = create_access_token(subject=str(admin_id), is_admin=True, tenant_id=admin_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, admin_id


@pytest.fixture
def second_athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    aid = db_mod.save_athlete({"name": "Other Rider", "experience_level": "Beginner"})
    db_mod.update_athlete(aid, {"tenant_id": aid})
    token = create_access_token(subject=str(aid), is_admin=False, tenant_id=aid)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, aid


class TestBleDeviceCreate:
    def test_register_weight_scale(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={
                "device_id": "scale-001",
                "name": "My Scale",
                "device_type": "weight_scale",
                "service_uuid": "0000181d-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a9d-0000-1000-8000-00805f9b34fb",
                "mac_address": "AA:BB:CC:DD:EE:FF",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == "scale-001"
        assert data["name"] == "My Scale"
        assert "id" in data

    def test_register_heart_rate(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={
                "device_id": "hr-001",
                "name": "HR Monitor",
                "device_type": "heart_rate",
            },
        )
        assert resp.status_code == 200

    def test_register_blood_pressure(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={
                "device_id": "bp-001",
                "name": "BP Monitor",
                "device_type": "blood_pressure",
            },
        )
        assert resp.status_code == 200

    def test_register_generic(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={
                "device_id": "gen-001",
                "name": "Generic Sensor",
                "device_type": "generic",
            },
        )
        assert resp.status_code == 200

    def test_register_invalid_device_type(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={
                "device_id": "bad-001",
                "name": "Bad Device",
                "device_type": "invalid_type",
            },
        )
        assert resp.status_code == 422

    def test_register_missing_device_id(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={"name": "No ID"},
        )
        assert resp.status_code == 422

    def test_register_missing_name(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "dev-001"},
        )
        assert resp.status_code == 422

    def test_register_duplicate_updates(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "dup-001", "name": "Original"},
        )
        resp = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "dup-001", "name": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_register_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "dev-001", "name": "No Auth"},
        )
        assert resp.status_code == 401


class TestBleDeviceList:
    def test_list_empty(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/ble/devices")
        assert resp.status_code == 200
        assert resp.json()["devices"] == []

    def test_list_own_devices(self, athlete_client):
        tc, aid = athlete_client
        tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Device 1"})
        tc.post("/api/v1/ble/devices", json={"device_id": "dev-2", "name": "Device 2"})
        resp = tc.get("/api/v1/ble/devices")
        assert resp.status_code == 200
        assert len(resp.json()["devices"]) == 2

    def test_list_does_not_show_other_athlete(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Mine"})
        tc2.post("/api/v1/ble/devices", json={"device_id": "dev-2", "name": "Theirs"})
        resp = tc.get("/api/v1/ble/devices")
        assert resp.status_code == 200
        names = {d["name"] for d in resp.json()["devices"]}
        assert "Mine" in names
        assert "Theirs" not in names

    def test_admin_can_see_own_devices(self, admin_client):
        tc, admin_id = admin_client
        tc.post("/api/v1/ble/devices", json={"device_id": "admin-dev", "name": "Admin Device"})
        resp = tc.get("/api/v1/ble/devices")
        assert resp.status_code == 200
        assert len(resp.json()["devices"]) == 1


class TestBleDeviceUpdate:
    def test_update_name(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Original"})
        device_id = created.json()["id"]
        resp = tc.put(
            f"/api/v1/ble/devices/{device_id}",
            json={"name": "Renamed"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_update_paired_status(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Device"})
        device_id = created.json()["id"]
        resp = tc.put(
            f"/api/v1/ble/devices/{device_id}",
            json={"paired": True},
        )
        assert resp.status_code == 200
        assert resp.json()["paired"] is True

    def test_update_settings(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Device"})
        device_id = created.json()["id"]
        resp = tc.put(
            f"/api/v1/ble/devices/{device_id}",
            json={"settings": '{"threshold": 10}'},
        )
        assert resp.status_code == 200
        assert resp.json()["settings"] == '{"threshold": 10}'

    def test_update_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.put(
            "/api/v1/ble/devices/99999",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    def test_update_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Mine"})
        device_id = created.json()["id"]
        resp = tc2.put(
            f"/api/v1/ble/devices/{device_id}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 404

    def test_update_partial_fields(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "dev-1", "name": "Original", "paired": False},
        )
        device_id = created.json()["id"]
        resp = tc.put(
            f"/api/v1/ble/devices/{device_id}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["paired"] is True


class TestBleDeviceDelete:
    def test_delete_existing(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "del-1", "name": "Delete Me"})
        device_id = created.json()["id"]
        resp = tc.delete(f"/api/v1/ble/devices/{device_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.delete("/api/v1/ble/devices/99999")
        assert resp.status_code == 404

    def test_delete_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Mine"})
        device_id = created.json()["id"]
        resp = tc2.delete(f"/api/v1/ble/devices/{device_id}")
        assert resp.status_code == 404

    def test_delete_removes_from_list(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "del-2", "name": "Gone"})
        device_id = created.json()["id"]
        tc.delete(f"/api/v1/ble/devices/{device_id}")
        resp = tc.get("/api/v1/ble/devices")
        assert resp.status_code == 200
        assert len(resp.json()["devices"]) == 0


class TestBleDeviceSync:
    def test_sync_weight_scale(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "scale-sync", "name": "Sync Scale", "device_type": "weight_scale"},
        )
        device_id = created.json()["id"]
        resp = tc.post(f"/api/v1/ble/devices/{device_id}/sync")
        assert resp.status_code == 200
        assert resp.json()["status"] == "synced"

    def test_sync_heart_rate(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "hr-sync", "name": "Sync HR", "device_type": "heart_rate"},
        )
        device_id = created.json()["id"]
        resp = tc.post(f"/api/v1/ble/devices/{device_id}/sync")
        assert resp.status_code == 200

    def test_sync_blood_pressure(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "bp-sync", "name": "Sync BP", "device_type": "blood_pressure"},
        )
        device_id = created.json()["id"]
        resp = tc.post(f"/api/v1/ble/devices/{device_id}/sync")
        assert resp.status_code == 200

    def test_sync_generic(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "gen-sync", "name": "Sync Generic", "device_type": "generic"},
        )
        device_id = created.json()["id"]
        resp = tc.post(f"/api/v1/ble/devices/{device_id}/sync")
        assert resp.status_code == 200

    def test_sync_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post("/api/v1/ble/devices/99999/sync")
        assert resp.status_code == 404

    def test_sync_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post("/api/v1/ble/devices", json={"device_id": "dev-1", "name": "Mine"})
        device_id = created.json()["id"]
        resp = tc2.post(f"/api/v1/ble/devices/{device_id}/sync")
        assert resp.status_code == 404

    def test_sync_with_value_weight(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "scale-val", "name": "Scale Val", "device_type": "weight_scale"},
        )
        device_id = created.json()["id"]
        resp = tc.post(
            f"/api/v1/ble/devices/{device_id}/sync",
            json={"value": 70.5, "unit": "kg", "recorded_at": "2026-08-01T10:00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["metric_id"] > 0
        metrics = tc.get(
            "/api/v1/athletes/me/metric-log",
            params={"metric_type": "weight_kg"},
        ).json()
        assert len(metrics["series"]) > 0

    def test_sync_without_value_backcompat(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/ble/devices",
            json={"device_id": "scale-bc", "name": "Scale BC", "device_type": "weight_scale"},
        )
        device_id = created.json()["id"]
        resp = tc.post(f"/api/v1/ble/devices/{device_id}/sync")
        assert resp.status_code == 200
        assert resp.json()["metric_id"] == 0


class TestBleDeviceSchemas:
    def test_register_valid(self):
        from bike_analyzer.backend.api.schemas import BleDeviceRegister

        d = BleDeviceRegister(
            device_id="scale-001",
            name="My Scale",
            device_type="weight_scale",
            service_uuid="0000181d-0000-1000-8000-00805f9b34fb",
        )
        assert d.device_type == "weight_scale"

    def test_register_invalid_device_type(self):
        from bike_analyzer.backend.api.schemas import BleDeviceRegister

        with pytest.raises(Exception):
            BleDeviceRegister(device_id="bad", name="Bad", device_type="invalid")

    def test_update_valid(self):
        from bike_analyzer.backend.api.schemas import BleDeviceUpdate

        u = BleDeviceUpdate(name="New Name", paired=True)
        assert u.name == "New Name"
        assert u.paired is True

    def test_update_all_optional(self):
        from bike_analyzer.backend.api.schemas import BleDeviceUpdate

        u = BleDeviceUpdate()
        assert u.name is None
        assert u.paired is None
        assert u.settings is None

    def test_sync_payload_with_value(self):
        from bike_analyzer.backend.api.schemas import BleDeviceSync

        s = BleDeviceSync(value=72.5, unit="kg", recorded_at="2026-08-01T10:00:00")
        assert s.value == 72.5
        assert s.unit == "kg"

    def test_sync_payload_optional(self):
        from bike_analyzer.backend.api.schemas import BleDeviceSync

        s = BleDeviceSync()
        assert s.value is None
        assert s.unit is None
