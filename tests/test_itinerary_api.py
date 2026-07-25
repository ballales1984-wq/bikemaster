"""Comprehensive tests for itinerary API endpoints.

Covers CRUD, stages, access control, admin vs athlete, and tenant isolation
for /api/v1/itineraries.
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
    athlete_id = db_mod.save_athlete({"name": "Itin Rider", "experience_level": "Intermediate"})
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


class TestItineraryCreate:
    def test_create_basic(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={
                "name": "Alps Tour",
                "description": "Weekend in the mountains",
                "start_date": "2024-07-01",
                "end_date": "2024-07-05",
                "total_km": 300.0,
                "total_elevation_m": 5000.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alps Tour"
        assert data["total_km"] == 300.0
        assert data["total_elevation_m"] == 5000.0
        assert "id" in data

    def test_create_minimal(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "Short"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Short"

    def test_create_without_dates(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "No Dates", "total_km": 100.0},
        )
        assert resp.status_code == 200

    def test_create_missing_name(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"description": "No name"},
        )
        assert resp.status_code == 422

    def test_create_name_too_short(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "A"},
        )
        assert resp.status_code == 422

    def test_create_name_too_long(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "X" * 151},
        )
        assert resp.status_code == 422

    def test_create_negative_distance(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "Bad Dist", "total_km": -10.0},
        )
        assert resp.status_code == 422

    def test_create_exceeds_max_distance(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "Too Far", "total_km": 200000.0},
        )
        assert resp.status_code == 422

    def test_create_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.post(
            "/api/v1/itineraries",
            json={"name": "No Auth"},
        )
        assert resp.status_code == 401


class TestItineraryList:
    def test_list_empty(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/itineraries")
        assert resp.status_code == 200
        assert resp.json()["itineraries"] == []

    def test_list_own_itineraries(self, athlete_client):
        tc, aid = athlete_client
        tc.post("/api/v1/itineraries", json={"name": "Trip 1"})
        tc.post("/api/v1/itineraries", json={"name": "Trip 2"})
        resp = tc.get("/api/v1/itineraries")
        assert resp.status_code == 200
        assert len(resp.json()["itineraries"]) == 2

    def test_list_does_not_show_other_athlete(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        tc.post("/api/v1/itineraries", json={"name": "Mine"})
        tc2.post("/api/v1/itineraries", json={"name": "Theirs"})
        resp = tc.get("/api/v1/itineraries")
        assert resp.status_code == 200
        names = {i["name"] for i in resp.json()["itineraries"]}
        assert "Mine" in names
        assert "Theirs" not in names

    def test_admin_sees_all(self, admin_client, athlete_client):
        tc_admin, admin_id = admin_client
        tc_athlete, aid = athlete_client
        tc_athlete.post("/api/v1/itineraries", json={"name": "Athlete Trip"})
        resp = tc_admin.get("/api/v1/itineraries")
        assert resp.status_code == 200
        names = {i["name"] for i in resp.json()["itineraries"]}
        assert "Athlete Trip" in names


class TestItineraryGet:
    def test_get_existing(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Get Me"})
        itin_id = created.json()["id"]
        resp = tc.get(f"/api/v1/itineraries/{itin_id}")
        assert resp.status_code == 200
        assert resp.json()["itinerary"]["name"] == "Get Me"

    def test_get_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/itineraries/99999")
        assert resp.status_code == 404

    def test_get_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Mine"})
        itin_id = created.json()["id"]
        resp = tc2.get(f"/api/v1/itineraries/{itin_id}")
        assert resp.status_code == 403

    def test_get_includes_stages(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/itineraries",
            json={"name": "Stage Trip", "start_date": "2024-07-01", "end_date": "2024-07-03"},
        )
        itin_id = created.json()["id"]
        tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 1, "title": "Day 1", "distance_km": 100.0, "elevation_gain_m": 1500.0},
        )
        tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 2, "title": "Day 2", "distance_km": 120.0, "elevation_gain_m": 2000.0},
        )
        resp = tc.get(f"/api/v1/itineraries/{itin_id}")
        assert resp.status_code == 200
        stages = resp.json()["stages"]
        assert len(stages) == 2
        assert stages[0]["title"] == "Day 1"
        assert stages[1]["title"] == "Day 2"


class TestItineraryStageCreate:
    def test_create_stage(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Stage Trip"})
        itin_id = created.json()["id"]
        resp = tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 1, "title": "Start", "distance_km": 50.0, "elevation_gain_m": 500.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Start"
        assert data["stage_day"] == 1
        assert data["distance_km"] == 50.0
        assert "id" in data

    def test_create_stage_minimal(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Stage Trip"})
        itin_id = created.json()["id"]
        resp = tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["stage_day"] == 1

    def test_create_stage_not_found_itinerary(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post(
            "/api/v1/itineraries/99999/stages",
            json={"stage_day": 1, "title": "Ghost"},
        )
        assert resp.status_code == 404

    def test_create_stage_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Mine"})
        itin_id = created.json()["id"]
        resp = tc2.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 1, "title": "Hacked"},
        )
        assert resp.status_code == 403

    def test_create_stage_invalid_day(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Stage Trip"})
        itin_id = created.json()["id"]
        resp = tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 0, "title": "Bad Day"},
        )
        assert resp.status_code == 422

    def test_create_stage_exceeds_max_day(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Stage Trip"})
        itin_id = created.json()["id"]
        resp = tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 367, "title": "Bad Day"},
        )
        assert resp.status_code == 422

    def test_create_multiple_stages_ordered(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post("/api/v1/itineraries", json={"name": "Ordered"})
        itin_id = created.json()["id"]
        tc.post(f"/api/v1/itineraries/{itin_id}/stages", json={"stage_day": 3, "title": "Day 3"})
        tc.post(f"/api/v1/itineraries/{itin_id}/stages", json={"stage_day": 1, "title": "Day 1"})
        tc.post(f"/api/v1/itineraries/{itin_id}/stages", json={"stage_day": 2, "title": "Day 2"})
        resp = tc.get(f"/api/v1/itineraries/{itin_id}")
        stages = resp.json()["stages"]
        assert [s["title"] for s in stages] == ["Day 1", "Day 2", "Day 3"]

    def test_admin_can_create_stage_for_any_itinerary(self, admin_client):
        tc, admin_id = admin_client
        created = tc.post("/api/v1/itineraries", json={"name": "Admin Trip"})
        itin_id = created.json()["id"]
        resp = tc.post(
            f"/api/v1/itineraries/{itin_id}/stages",
            json={"stage_day": 1, "title": "Admin Stage"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Admin Stage"


class TestItineraryEndToEnd:
    def test_full_itinerary_lifecycle(self, athlete_client):
        tc, aid = athlete_client
        # Create
        resp = tc.post(
            "/api/v1/itineraries",
            json={
                "name": "Full Lifecycle",
                "description": "End-to-end test",
                "start_date": "2024-08-01",
                "end_date": "2024-08-05",
                "total_km": 400.0,
                "total_elevation_m": 6000.0,
            },
        )
        assert resp.status_code == 200
        itin_id = resp.json()["id"]

        # Add stages
        tc.post(f"/api/v1/itineraries/{itin_id}/stages", json={"stage_day": 1, "title": "Day 1", "distance_km": 80.0, "elevation_gain_m": 1200.0})
        tc.post(f"/api/v1/itineraries/{itin_id}/stages", json={"stage_day": 2, "title": "Day 2", "distance_km": 100.0, "elevation_gain_m": 1500.0})

        # Read
        resp = tc.get(f"/api/v1/itineraries/{itin_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["itinerary"]["name"] == "Full Lifecycle"
        assert len(data["stages"]) == 2

        # List
        resp = tc.get("/api/v1/itineraries")
        assert len(resp.json()["itineraries"]) == 1
