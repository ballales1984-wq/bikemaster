"""Comprehensive tests for calendar API endpoints.

Covers CRUD, access control, tenant isolation, date validation, and
event-type constraints for /api/v1/calendar/events.
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
    athlete_id = db_mod.save_athlete({"name": "Cal Rider", "experience_level": "Intermediate"})
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


class TestCalendarEventCreate:
    def test_create_training_event(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Morning Ride",
                "event_type": "training",
                "date": "2024-06-15",
                "duration_minutes": 90,
                "description": "Zone 2 base",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Morning Ride"
        assert data["event_type"] == "training"
        assert data["date"] == "2024-06-15"
        assert data["duration_minutes"] == 90
        assert data["completed"] is False
        assert "id" in data

    def test_create_race_event(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Gran Fondo",
                "event_type": "race",
                "date": "2024-09-20",
                "duration_minutes": 360,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "race"

    def test_create_recovery_event(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Rest Day",
                "event_type": "recovery",
                "date": "2024-06-16",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "recovery"

    def test_create_goal_deadline_event(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "FTP Test Deadline",
                "event_type": "goal_deadline",
                "date": "2024-07-01",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "goal_deadline"

    def test_create_with_coordinates(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Mountain Ride",
                "event_type": "training",
                "date": "2024-06-15",
                "lat": 45.5,
                "lon": 7.2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Mountain Ride"

    def test_create_invalid_event_type(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Bad Event",
                "event_type": "invalid_type",
                "date": "2024-06-15",
            },
        )
        assert resp.status_code == 422

    def test_create_invalid_date_format(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Bad Date",
                "event_type": "training",
                "date": "15-06-2024",
            },
        )
        assert resp.status_code == 422

    def test_create_missing_title(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "event_type": "training",
                "date": "2024-06-15",
            },
        )
        assert resp.status_code == 422

    def test_create_missing_date(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "No Date",
                "event_type": "training",
            },
        )
        assert resp.status_code == 422

    def test_create_invalid_lat(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Bad Lat",
                "event_type": "training",
                "date": "2024-06-15",
                "lat": 91.0,
            },
        )
        assert resp.status_code == 422

    def test_create_invalid_lon(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Bad Lon",
                "event_type": "training",
                "date": "2024-06-15",
                "lon": 181.0,
            },
        )
        assert resp.status_code == 422

    def test_create_negative_duration(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Neg Duration",
                "event_type": "training",
                "date": "2024-06-15",
                "duration_minutes": -1,
            },
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
            "/api/v1/calendar/events",
            json={
                "athlete_id": 1,
                "title": "No Auth",
                "event_type": "training",
                "date": "2024-06-15",
            },
        )
        assert resp.status_code == 401


class TestCalendarEventList:
    def test_list_by_month_empty(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=1")
        assert resp.status_code == 200
        assert resp.json()["events"] == []

    def test_list_by_month_with_events(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "June Ride", "event_type": "training", "date": "2024-06-15"},
        )
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "June Race", "event_type": "race", "date": "2024-06-20"},
        )
        resp = tc.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=6")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 2
        titles = {e["title"] for e in events}
        assert "June Ride" in titles
        assert "June Race" in titles

    def test_list_by_month_filters_other_months(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "June", "event_type": "training", "date": "2024-06-15"},
        )
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "July", "event_type": "training", "date": "2024-07-15"},
        )
        resp = tc.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=6")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["title"] == "June"

    def test_list_by_range_empty(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/calendar/events/range?athlete_id={aid}&start=2024-01-01&end=2024-01-31")
        assert resp.status_code == 200
        assert resp.json()["events"] == []

    def test_list_by_range_with_events(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Range 1", "event_type": "training", "date": "2024-06-10"},
        )
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Range 2", "event_type": "training", "date": "2024-06-25"},
        )
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Out of Range", "event_type": "training", "date": "2024-07-10"},
        )
        resp = tc.get(f"/api/v1/calendar/events/range?athlete_id={aid}&start=2024-06-01&end=2024-06-30")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 2
        titles = {e["title"] for e in events}
        assert "Range 1" in titles
        assert "Range 2" in titles
        assert "Out of Range" not in titles

    def test_list_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Mine", "event_type": "training", "date": "2024-06-15"},
        )
        resp = tc2.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=6")
        assert resp.status_code == 403

    def test_list_admin_can_see_all(self, admin_client, athlete_client):
        tc_admin, admin_id = admin_client
        tc_athlete, aid = athlete_client
        tc_athlete.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Athlete Event", "event_type": "training", "date": "2024-06-15"},
        )
        resp = tc_admin.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=6")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["title"] == "Athlete Event"

    def test_list_by_month_missing_params(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/calendar/events")
        assert resp.status_code == 422


class TestCalendarEventGet:
    def test_get_existing(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Get Me", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.get(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"

    def test_get_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/calendar/events/99999")
        assert resp.status_code == 404

    def test_get_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Mine", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc2.get(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 403


class TestCalendarEventUpdate:
    def test_update_title(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Original", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Updated Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_event_type(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Race Prep", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"event_type": "race"})
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "race"

    def test_update_completed(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Done", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"completed": True})
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_update_duration(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Long", "event_type": "training", "date": "2024-06-15", "duration_minutes": 60},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"duration_minutes": 120})
        assert resp.status_code == 200
        assert resp.json()["duration_minutes"] == 120

    def test_update_date(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Reschedule", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"date": "2024-06-20"})
        assert resp.status_code == 200
        assert resp.json()["date"] == "2024-06-20"

    def test_update_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.put("/api/v1/calendar/events/99999", json={"title": "Nope"})
        assert resp.status_code == 404

    def test_update_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Mine", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc2.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Hacked"})
        assert resp.status_code == 403

    def test_update_invalid_event_type(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Test", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"event_type": "invalid"})
        assert resp.status_code == 422


class TestCalendarEventDelete:
    def test_delete_existing(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Delete Me", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.delete(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.delete("/api/v1/calendar/events/99999")
        assert resp.status_code == 404

    def test_delete_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Mine", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc2.delete(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 403

    def test_delete_removes_from_db(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Gone", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        tc.delete(f"/api/v1/calendar/events/{event_id}")
        resp = tc.get(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 404


class TestCalendarEventComplete:
    def test_toggle_complete_true(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Toggle", "event_type": "training", "date": "2024-06-15", "completed": False},
        )
        event_id = created.json()["id"]
        resp = tc.post(f"/api/v1/calendar/events/{event_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_toggle_complete_twice(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Double Toggle", "event_type": "training", "date": "2024-06-15", "completed": False},
        )
        event_id = created.json()["id"]
        tc.post(f"/api/v1/calendar/events/{event_id}/complete")
        resp = tc.post(f"/api/v1/calendar/events/{event_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is False

    def test_toggle_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post("/api/v1/calendar/events/99999/complete")
        assert resp.status_code == 404

    def test_toggle_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Mine", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc2.post(f"/api/v1/calendar/events/{event_id}/complete")
        assert resp.status_code == 403


class TestCalendarTenantIsolation:
    def test_tenant_sees_own_events_only(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        aid1 = db_mod.save_athlete({"name": "T1", "experience_level": "Intermediate"})
        db_mod.update_athlete(aid1, {"tenant_id": aid1})
        aid2 = db_mod.save_athlete({"name": "T2", "experience_level": "Intermediate"})
        db_mod.update_athlete(aid2, {"tenant_id": aid2})

        token1 = create_access_token(subject=str(aid1), is_admin=False, tenant_id=aid1)
        token2 = create_access_token(subject=str(aid2), is_admin=False, tenant_id=aid2)

        tc1 = TestClient(create_app())
        tc1.headers["Authorization"] = f"Bearer {token1}"
        tc2 = TestClient(create_app())
        tc2.headers["Authorization"] = f"Bearer {token2}"

        tc1.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid1, "title": "T1 Event", "event_type": "training", "date": "2024-06-15"},
        )
        tc2.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid2, "title": "T2 Event", "event_type": "training", "date": "2024-06-15"},
        )

        resp1 = tc1.get(f"/api/v1/calendar/events?athlete_id={aid1}&year=2024&month=6")
        assert len(resp1.json()["events"]) == 1
        assert resp1.json()["events"][0]["title"] == "T1 Event"

        resp2 = tc2.get(f"/api/v1/calendar/events?athlete_id={aid2}&year=2024&month=6")
        assert len(resp2.json()["events"]) == 1
        assert resp2.json()["events"][0]["title"] == "T2 Event"


class TestCalendarAdminAccess:
    def test_admin_can_create_for_any_athlete(self, admin_client):
        tc, admin_id = admin_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": 1,
                "title": "Admin Created",
                "event_type": "training",
                "date": "2024-06-15",
            },
        )
        assert resp.status_code == 200

    def test_admin_can_update_any_event(self, admin_client):
        tc, admin_id = admin_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": 1,
                "title": "Admin Event",
                "event_type": "training",
                "date": "2024-06-15",
            },
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Admin Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Admin Updated"

    def test_admin_can_delete_any_event(self, admin_client):
        tc, admin_id = admin_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": 1,
                "title": "Admin Delete",
                "event_type": "training",
                "date": "2024-06-15",
            },
        )
        event_id = created.json()["id"]
        resp = tc.delete(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 200

    def test_admin_can_toggle_any_event(self, admin_client):
        tc, admin_id = admin_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": 1,
                "title": "Admin Toggle",
                "event_type": "training",
                "date": "2024-06-15",
                "completed": False,
            },
        )
        event_id = created.json()["id"]
        resp = tc.post(f"/api/v1/calendar/events/{event_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True
