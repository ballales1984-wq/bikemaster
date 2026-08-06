"""Tests for granfondo plan → calendar events integration.

Covers _granfondo_event_type mapping, save_granfondo_plan endpoint,
and the full flow from plan generation to persisted calendar events.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


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



@pytest.fixture
def athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "GF Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


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


class TestGranfondoEventTypeMapping:
    def test_race_maps_to_race(self):
        from bike_analyzer.backend.api.routes import _granfondo_event_type

        assert _granfondo_event_type("race") == "race"

    def test_recovery_maps_to_recovery(self):
        from bike_analyzer.backend.api.routes import _granfondo_event_type

        assert _granfondo_event_type("recovery") == "recovery"

    def test_training_maps_to_training(self):
        from bike_analyzer.backend.api.routes import _granfondo_event_type

        assert _granfondo_event_type("training") == "training"

    def test_interval_maps_to_training(self):
        from bike_analyzer.backend.api.routes import _granfondo_event_type

        assert _granfondo_event_type("interval") == "training"

    def test_endurance_maps_to_training(self):
        from bike_analyzer.backend.api.routes import _granfondo_event_type

        assert _granfondo_event_type("endurance") == "training"

    def test_long_maps_to_training(self):
        from bike_analyzer.backend.api.routes import _granfondo_event_type

        assert _granfondo_event_type("long") == "training"


class TestSaveGranfondoPlan:
    def test_save_plan_creates_events(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {
                        "date": "2024-08-05",
                        "title": "Base Ride",
                        "workout_type": "training",
                        "duration_minutes": 90,
                        "description": "Zone 2",
                    },
                    {
                        "date": "2024-08-06",
                        "title": "Interval",
                        "workout_type": "interval",
                        "duration_minutes": 60,
                        "description": "VO2 max",
                    },
                    {
                        "date": "2024-08-07",
                        "title": "Race Day",
                        "workout_type": "race",
                        "duration_minutes": 360,
                        "description": "Gran Fondo",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] == 3
        assert len(data["event_ids"]) == 3

    def test_saved_events_have_correct_types(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "Training", "workout_type": "training"},
                    {"date": "2024-08-06", "title": "Race", "workout_type": "race"},
                    {"date": "2024-08-07", "title": "Recovery", "workout_type": "recovery"},
                ],
            },
        )
        assert resp.status_code == 200
        event_ids = resp.json()["event_ids"]
        events = [tc.get(f"/api/v1/calendar/events/{eid}").json() for eid in event_ids]
        type_map = {e["title"]: e["event_type"] for e in events}
        assert type_map["Training"] == "training"
        assert type_map["Race"] == "race"
        assert type_map["Recovery"] == "recovery"

    def test_saved_events_default_to_athlete_tenant(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "T", "workout_type": "training"},
                ],
            },
        )
        assert resp.status_code == 200
        event_id = resp.json()["event_ids"][0]
        event = tc.get(f"/api/v1/calendar/events/{event_id}").json()
        assert event["athlete_id"] == aid

    def test_save_empty_plan_rejected(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={"athlete_id": aid, "plan": []},
        )
        assert resp.status_code == 422

    def test_save_plan_exceeds_max_workouts(self, athlete_client):
        tc, aid = athlete_client
        plan = [
            {"date": f"2024-08-{i:02d}", "title": f"W{i}", "workout_type": "training"}
            for i in range(1, 202)
        ]
        resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={"athlete_id": aid, "plan": plan},
        )
        assert resp.status_code == 422

    def test_save_plan_unauthorized(self, db_path):
        from bike_analyzer.backend.api.app_factory import create_app
        from bike_analyzer.backend.db import database as db_mod

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "plan": [
                    {"date": "2024-08-05", "title": "T", "workout_type": "training"},
                ],
            },
        )
        assert resp.status_code == 401

    def test_save_plan_for_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        resp = tc2.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "Hacked", "workout_type": "training"},
                ],
            },
        )
        assert resp.status_code == 403


class TestGranfondoCalendarIntegration:
    def test_plan_events_visible_in_month_list(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "Week 1 Ride", "workout_type": "training"},
                    {"date": "2024-08-12", "title": "Week 2 Ride", "workout_type": "training"},
                ],
            },
        )
        resp = tc.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=8")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 2

    def test_plan_events_visible_in_range(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "Ride 1", "workout_type": "training"},
                    {"date": "2024-08-25", "title": "Ride 2", "workout_type": "training"},
                ],
            },
        )
        resp = tc.get(f"/api/v1/calendar/events/range?athlete_id={aid}&start=2024-08-01&end=2024-08-31")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 2

    def test_events_persist_across_requests(self, athlete_client):
        tc, aid = athlete_client
        save_resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "Persist", "workout_type": "training"},
                ],
            },
        )
        event_id = save_resp.json()["event_ids"][0]
        resp1 = tc.get(f"/api/v1/calendar/events/{event_id}")
        resp2 = tc.get(f"/api/v1/calendar/events/{event_id}")
        assert resp1.json()["title"] == "Persist"
        assert resp2.json()["title"] == "Persist"

    def test_events_can_be_toggled_complete(self, athlete_client):
        tc, aid = athlete_client
        save_resp = tc.post(
            "/api/v1/training/granfondo/save",
            json={
                "athlete_id": aid,
                "plan": [
                    {"date": "2024-08-05", "title": "Complete Me", "workout_type": "training"},
                ],
            },
        )
        event_id = save_resp.json()["event_ids"][0]
        resp = tc.post(f"/api/v1/calendar/events/{event_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True
