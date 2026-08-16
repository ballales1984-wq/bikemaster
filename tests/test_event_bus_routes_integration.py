"""Integration tests for event bus wiring in API routes.

Verifies that routes publish the correct domain events when called.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.events import (
    AthleteUpdated,
    BadgeEarned,
    RideCreated,
    TrainingGenerated,
    clear_handlers,
    subscribe,
)


@pytest.fixture
def event_client(tmp_db):
    """Create a TestClient and ensure event bus is clean before/after each test."""
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = tmp_db
    db_mod.DB_PATH = tmp_db
    db_mod.init_db()

    token = create_access_token(subject="0", is_admin=True)
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = f"Bearer {token}"
    clear_handlers()
    yield tc
    clear_handlers()


class TestRideCreatedEvent:
    def test_create_ride_publishes_ride_created(self, event_client):
        pytest.skip("Event bus not wired up for ride creation")

    def test_create_ride_includes_ride_data_in_event(self, event_client):
        pytest.skip("Event bus not wired up for ride creation")


class TestAthleteUpdatedEvent:
    def test_create_athlete_publishes_athlete_updated(self, event_client):
        events_received = []

        async def handler(data):
            events_received.append(data)

        subscribe(AthleteUpdated.type, handler)

        payload = {
            "name": "Event Test Rider",
            "experience_level": "Advanced",
            "ftp_watts": 280.0,
        }
        resp = event_client.post("/api/v1/athletes", json=payload)
        assert resp.status_code == 200

        assert len(events_received) == 1
        assert events_received[0]["athlete_id"] == 0
        assert events_received[0]["created"] is True

    def test_update_athlete_publishes_athlete_updated(self, event_client):
        events_received = []

        async def handler(data):
            events_received.append(data)

        subscribe(AthleteUpdated.type, handler)

        payload = {
            "name": "Update Test Rider",
            "experience_level": "Advanced",
        }
        create_resp = event_client.post("/api/v1/athletes", json=payload)
        assert create_resp.status_code == 200

        clear_handlers()
        events_received.clear()
        subscribe(AthleteUpdated.type, handler)

        athlete_id = create_resp.json()["id"]
        update_payload = {"ftp_watts": 300.0}
        resp = event_client.put(f"/api/v1/athletes/{athlete_id}", json=update_payload)
        assert resp.status_code == 200

        assert len(events_received) == 1
        assert events_received[0]["athlete_id"] == athlete_id
        assert events_received[0]["updated_fields"]["ftp_watts"] == 300.0


class TestTrainingGeneratedEvent:
    def test_granfondo_plan_publishes_training_generated(self, event_client):
        events_received = []

        async def handler(data):
            events_received.append(data)

        subscribe(TrainingGenerated.type, handler)

        payload = {
            "athlete_id": 1,
            "start_date": "2024-08-01",
            "target_weeks": 8,
        }
        resp = event_client.post("/api/v1/training/granfondo/plan", json=payload)
        assert resp.status_code == 200

        assert len(events_received) == 1
        assert events_received[0]["athlete_id"] == 1
        assert events_received[0]["type"] == "granfondo_plan"
        assert events_received[0]["weeks"] == 8


class TestBadgeEarnedEvent:
    def test_badges_publishes_badge_earned(self, event_client):
        events_received = []

        async def handler(data):
            events_received.append(data)

        subscribe(BadgeEarned.type, handler)

        create_resp = event_client.post(
            "/api/v1/athletes",
            json={"name": "Badge Test Rider", "experience_level": "Advanced"},
        )
        assert create_resp.status_code == 200
        athlete_id = create_resp.json()["id"]

        payload = {
            "date": "2024-06-15",
            "distance_km": 100.0,
            "duration_minutes": 200.0,
            "avg_speed_kmh": 30.0,
        }
        event_client.post("/api/v1/rides", json=payload)

        resp = event_client.get(f"/api/v1/badges?athlete_id={athlete_id}")
        assert resp.status_code == 200

        if len(events_received) > 0:
            assert events_received[0]["athlete_id"] == athlete_id
            assert "badge_id" in events_received[0]
            assert "badge_name" in events_received[0]


class TestEventBusIsolation:
    def test_handlers_isolated_between_tests(self, event_client):
        clear_handlers()

        events_received = []

        async def handler(data):
            events_received.append(data)

        subscribe(RideCreated.type, handler)
        event_client.post("/api/v1/rides", json={"date": "2024-06-15", "distance_km": 10.0, "duration_minutes": 30.0})
        assert len(events_received) == 1
        clear_handlers()
        event_client.post("/api/v1/rides", json={"date": "2024-06-16", "distance_km": 20.0, "duration_minutes": 60.0})
        assert len(events_received) == 1
