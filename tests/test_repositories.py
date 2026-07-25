"""Tests for the analytics repositories (async session-factory path).

These repositories are the data-access layer used by the async DB flow. The
tests spin up an on-disk async SQLite database (shared across the multiple
sessions each repository opens) and exercise save/get/list/upsert/clear paths.
"""

from __future__ import annotations

import asyncio
import os

import pytest
pytestmark = pytest.mark.slow

import bike_analyzer.backend.db.async_db as async_db_mod
from bike_analyzer.backend.analytics.repositories import (
    athlete_repository,
    chat_history_repository,
    fitness_state_repository,
    poi_repository,
    ride_repository,
    training_stress_repository,
    user_repository,
)
from bike_analyzer.backend.db.async_db import get_session_factory, init_async_db


@pytest.fixture
def session_factory(tmp_path):
    path = tmp_path / "repos_test.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    async_db_mod._engine = None
    async_db_mod._session_factory = None

    asyncio.run(init_async_db())
    factory = get_session_factory()

    # Tables not covered by init_async_db (separate metadata registries).
    engine = async_db_mod._get_engine()

    async def _create_extra():
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: training_stress_repository.TRAINING_STRESS_DAYS_TABLE.create(c, checkfirst=True)
            )
            await conn.run_sync(
                lambda c: chat_history_repository._Base.metadata.create_all(c, checkfirst=True)
            )

    asyncio.run(_create_extra())
    yield factory
    os.environ.pop("DATABASE_URL", None)
    async_db_mod._engine = None
    async_db_mod._session_factory = None


# --------------------------------------------------------------------------- #
# RideRepository
# --------------------------------------------------------------------------- #
class TestRideRepository:
    def test_save_and_get(self, session_factory):
        repo = ride_repository.RideRepository(session_factory=session_factory)
        rid = asyncio.run(
            repo.save(
                {
                    "athlete_id": 1,
                    "tenant_id": 1,
                    "date": "2024-06-15",
                    "distance_km": 35.0,
                    "duration_minutes": 90.0,
                    "gps_points": [{"lat": 1.0, "lon": 2.0}],
                    "title": "Ride",
                }
            )
        )
        assert isinstance(rid, int)
        fetched = asyncio.run(repo.get_by_id(rid))
        assert fetched["distance_km"] == 35.0
        assert fetched["gps_points"] == [{"lat": 1.0, "lon": 2.0}]

    def test_get_missing(self, session_factory):
        repo = ride_repository.RideRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_by_id(999)) is None

    def test_get_with_tenant_filter(self, session_factory):
        repo = ride_repository.RideRepository(session_factory=session_factory)
        rid = asyncio.run(repo.save({"athlete_id": 2, "tenant_id": 5, "date": "2024-06-16", "distance_km": 10.0}))
        assert asyncio.run(repo.get_by_id(rid, tenant_id=5)) is not None
        assert asyncio.run(repo.get_by_id(rid, tenant_id=6)) is None

    def test_list_all_by_athlete(self, session_factory):
        repo = ride_repository.RideRepository(session_factory=session_factory)
        asyncio.run(repo.save({"athlete_id": 3, "tenant_id": 1, "date": "2024-06-10", "distance_km": 10.0}))
        asyncio.run(repo.save({"athlete_id": 3, "tenant_id": 1, "date": "2024-06-20", "distance_km": 20.0}))
        rows = asyncio.run(repo.list_all(athlete_id=3, tenant_id=1))
        assert len(rows) == 2
        # ordered by date desc -> most recent first
        assert rows[0]["date"] == "2024-06-20"

    def test_list_all_tenant_filter(self, session_factory):
        repo = ride_repository.RideRepository(session_factory=session_factory)
        asyncio.run(repo.save({"athlete_id": 4, "tenant_id": 7, "date": "2024-06-10", "distance_km": 10.0}))
        assert asyncio.run(repo.list_all(athlete_id=4, tenant_id=8)) == []


# --------------------------------------------------------------------------- #
# AthleteRepository
# --------------------------------------------------------------------------- #
class TestAthleteRepository:
    def test_save_and_get(self, session_factory):
        repo = athlete_repository.AthleteRepository(session_factory=session_factory)
        aid = asyncio.run(repo.save({"name": "Anna", "age": 28, "weight_kg": 60.0, "ftp_watts": 240}, tenant_id=1))
        assert isinstance(aid, int)
        fetched = asyncio.run(repo.get_by_id(aid))
        assert fetched["name"] == "Anna"
        assert fetched["ftp_watts"] == 240

    def test_get_by_name(self, session_factory):
        repo = athlete_repository.AthleteRepository(session_factory=session_factory)
        asyncio.run(repo.save({"name": "Bob", "age": 40}, tenant_id=1))
        found = asyncio.run(repo.get_by_name("Bob"))
        assert found is not None
        assert found["name"] == "Bob"

    def test_get_missing(self, session_factory):
        repo = athlete_repository.AthleteRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_by_id(12345)) is None
        assert asyncio.run(repo.get_by_name("nobody")) is None

    def test_list_all(self, session_factory):
        repo = athlete_repository.AthleteRepository(session_factory=session_factory)
        asyncio.run(repo.save({"name": "C1"}, tenant_id=1))
        asyncio.run(repo.save({"name": "C2"}, tenant_id=1))
        assert len(asyncio.run(repo.list_all())) == 2


# --------------------------------------------------------------------------- #
# UserRepository
# --------------------------------------------------------------------------- #
class TestUserRepository:
    def test_save_and_get(self, session_factory):
        repo = user_repository.UserRepository(session_factory=session_factory)
        uid = asyncio.run(
            repo.save(
                {
                    "username": "alice",
                    "email": "alice@example.com",
                    "password_hash": "x",
                    "is_admin": True,
                    "is_active": True,
                }
            )
        )
        assert isinstance(uid, int)
        assert asyncio.run(repo.get_by_id(uid))["username"] == "alice"
        assert asyncio.run(repo.get_by_username("alice"))["email"] == "alice@example.com"
        assert asyncio.run(repo.get_by_email("alice@example.com"))["username"] == "alice"

    def test_get_missing(self, session_factory):
        repo = user_repository.UserRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_by_id(99999)) is None
        assert asyncio.run(repo.get_by_username("ghost")) is None
        assert asyncio.run(repo.get_by_email("ghost@x.com")) is None

    def test_list_all(self, session_factory):
        repo = user_repository.UserRepository(session_factory=session_factory)
        asyncio.run(repo.save({"username": "u1"}))
        asyncio.run(repo.save({"username": "u2"}))
        assert len(asyncio.run(repo.list_all())) == 2


# --------------------------------------------------------------------------- #
# POIRepository
# --------------------------------------------------------------------------- #
class TestPOIRepository:
    def test_create_and_get(self, session_factory):
        repo = poi_repository.POIRepository(session_factory=session_factory)
        pid = asyncio.run(
            repo.create(
                {
                    "name": "Fontana",
                    "description": "Acqua",
                    "lat": 45.0,
                    "lon": 9.0,
                    "type": "water",
                    "photos": ["p1.jpg"],
                    "tags": ["cool"],
                    "tenant_id": 1,
                }
            )
        )
        fetched = asyncio.run(repo.get_by_id(pid))
        assert fetched["name"] == "Fontana"
        assert fetched["photos"] == ["p1.jpg"]
        assert fetched["tags"] == ["cool"]

    def test_get_missing(self, session_factory):
        repo = poi_repository.POIRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_by_id(99999)) is None

    def test_get_nearby(self, session_factory):
        repo = poi_repository.POIRepository(session_factory=session_factory)
        asyncio.run(
            repo.create({"name": "Near", "description": "d", "lat": 45.0, "lon": 9.0, "type": "x", "tenant_id": 1})
        )
        asyncio.run(
            repo.create({"name": "Far", "description": "d", "lat": 50.0, "lon": 9.0, "type": "x", "tenant_id": 1})
        )
        nearby = asyncio.run(repo.get_nearby(45.0, 9.0, radius_km=5.0))
        names = {p["name"] for p in nearby}
        assert "Near" in names
        assert "Far" not in names

    def test_get_nearby_empty(self, session_factory):
        repo = poi_repository.POIRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_nearby(0.0, 0.0, radius_km=1.0)) == []


# --------------------------------------------------------------------------- #
# TrainingStressRepository
# --------------------------------------------------------------------------- #
class TestTrainingStressRepository:
    def test_upsert_and_history(self, session_factory):
        repo = training_stress_repository.TrainingStressRepository(session_factory=session_factory)
        asyncio.run(repo.upsert_day(1, "2024-06-01", tss=50, atl=40, ctl=45, tsb=5, tenant_id=1))
        asyncio.run(repo.upsert_day(1, "2024-06-02", tss=60, atl=42, ctl=46, tsb=4, tenant_id=1))
        history = asyncio.run(repo.get_history(1, tenant_id=1))
        assert len(history) == 2
        assert history[0]["date"] == "2024-06-02"  # most recent first

    def test_latest(self, session_factory):
        repo = training_stress_repository.TrainingStressRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_latest(1)) is None
        asyncio.run(repo.upsert_day(1, "2024-06-03", tss=10, atl=10, ctl=10, tsb=10, tenant_id=1))
        latest = asyncio.run(repo.get_latest(1))
        assert latest["date"] == "2024-06-03"

    def test_history_tenant_filter(self, session_factory):
        repo = training_stress_repository.TrainingStressRepository(session_factory=session_factory)
        asyncio.run(repo.upsert_day(1, "2024-06-04", tss=10, atl=10, ctl=10, tsb=10, tenant_id=9))
        assert asyncio.run(repo.get_history(1, tenant_id=8)) == []


# --------------------------------------------------------------------------- #
# FitnessStateRepository
# --------------------------------------------------------------------------- #
class TestFitnessStateRepository:
    def test_save_and_latest(self, session_factory):
        repo = fitness_state_repository.FitnessStateRepository(session_factory=session_factory)
        sid = asyncio.run(
            repo.save(
                {
                    "athlete_id": 1,
                    "tenant_id": 1,
                    "date": "2024-06-01",
                    "fitness": 50.0,
                    "fatigue": 30.0,
                    "form": 20.0,
                    "atl": 30.0,
                    "ctl": 50.0,
                    "tsb": 20.0,
                    "risk_indicators": ["overreaching"],
                    "recommendation": "rest",
                }
            )
        )
        assert isinstance(sid, int)
        latest = asyncio.run(repo.get_latest(1, tenant_id=1))
        assert latest["fitness"] == 50.0
        assert latest["risk_indicators"] == ["overreaching"]

    def test_get_latest_missing(self, session_factory):
        repo = fitness_state_repository.FitnessStateRepository(session_factory=session_factory)
        assert asyncio.run(repo.get_latest(999)) is None

    def test_get_history(self, session_factory):
        repo = fitness_state_repository.FitnessStateRepository(session_factory=session_factory)
        asyncio.run(repo.save({"athlete_id": 2, "tenant_id": 1, "date": "2024-06-01", "ctl": 50.0}))
        asyncio.run(repo.save({"athlete_id": 2, "tenant_id": 1, "date": "2024-06-02", "ctl": 52.0}))
        history = asyncio.run(repo.get_history(2, days=30, tenant_id=1))
        assert len(history) == 2

    def test_requires_async(self):
        repo = fitness_state_repository.FitnessStateRepository()
        with pytest.raises(RuntimeError, match="Async session factory required"):
            asyncio.run(repo.save({"athlete_id": 1}))


# --------------------------------------------------------------------------- #
# ChatHistoryRepository
# --------------------------------------------------------------------------- #
class TestChatHistoryRepository:
    def test_save_and_recent(self, session_factory):
        repo = chat_history_repository.ChatHistoryRepository(session_factory=session_factory)
        asyncio.run(repo.save(athlete_id=1, role="user", content="Ciao", tenant_id=1))
        asyncio.run(repo.save(athlete_id=1, role="assistant", content="Salve", tenant_id=1))
        recent = asyncio.run(repo.get_recent(1, tenant_id=1))
        assert len(recent) == 2
        assert recent[0]["role"] == "assistant"  # most recent first

    def test_tenant_filter(self, session_factory):
        repo = chat_history_repository.ChatHistoryRepository(session_factory=session_factory)
        asyncio.run(repo.save(athlete_id=1, role="user", content="x", tenant_id=1))
        assert asyncio.run(repo.get_recent(1, tenant_id=2)) == []

    def test_clear(self, session_factory):
        repo = chat_history_repository.ChatHistoryRepository(session_factory=session_factory)
        asyncio.run(repo.save(athlete_id=1, role="user", content="x", tenant_id=1))
        count = asyncio.run(repo.clear(1, tenant_id=1))
        assert count == 1
        assert asyncio.run(repo.get_recent(1, tenant_id=1)) == []

    def test_prune_retention(self, session_factory):
        repo = chat_history_repository.ChatHistoryRepository(session_factory=session_factory)
        asyncio.run(repo.save(athlete_id=1, role="user", content="old", tenant_id=1))
        # retention_days default 90 -> nothing older than 90 days is pruned here
        pruned = asyncio.run(repo.prune(1, retention_days=90, tenant_id=1))
        assert pruned == 0

    def test_requires_async(self):
        repo = chat_history_repository.ChatHistoryRepository()
        with pytest.raises(RuntimeError, match="Async session factory required"):
            asyncio.run(repo.save(athlete_id=1, role="user", content="x"))


class MockSyncConn:
    """Minimal stand-in for the legacy synchronous DB layer used by the
    repository ``sync_conn`` fallback path."""

    def save_ride(self, ride):
        return 99

    def get_ride(self, ride_id, tenant_id=None):
        return {"id": ride_id, "distance_km": 5.0}

    def get_all_rides(self, athlete_id=None, tenant_id=None):
        return [{"id": 1}]

    def get_rides_by_athlete(self, athlete_id, tenant_id=None):
        return [{"id": 1}]

    def delete_ride(self, ride_id, tenant_id=None):
        return True

    def save_athlete(self, athlete, athlete_id=None, tenant_id=0):
        return 7

    def get_athlete(self, athlete_id, tenant_id=None):
        return {"id": athlete_id, "name": "x"}

    def get_athlete_by_name(self, name, tenant_id=None):
        return {"id": 1, "name": name}

    def get_all_athletes(self):
        return [{"id": 1}]

    def save_poi(self, poi):
        return 3

    def get_poi(self, poi_id):
        return {"id": poi_id, "name": "p"}

    def get_nearby_pois(self, lat, lon, radius_km):
        return []

    def upsert_training_stress_day(self, athlete_id, date, tss, atl, ctl, tsb, tenant_id=0):
        return None

    def get_training_stress_days(self, athlete_id, limit=90, tenant_id=None):
        return [{"date": "2024-01-01"}]

    def get_latest_training_stress(self, athlete_id, tenant_id=None):
        return {"date": "2024-01-01"}


class TestRideRepositorySync:
    def test_save_sync(self):
        repo = ride_repository.RideRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.save({"athlete_id": 1})) == 99

    def test_get_by_id_sync(self):
        repo = ride_repository.RideRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_by_id(1))["id"] == 1

    def test_list_all_sync(self):
        repo = ride_repository.RideRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.list_all()) == [{"id": 1}]


class TestAthleteRepositorySync:
    def test_save_sync(self):
        repo = athlete_repository.AthleteRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.save({"name": "x"})) == 7

    def test_get_by_id_sync(self):
        repo = athlete_repository.AthleteRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_by_id(1))["id"] == 1

    def test_get_by_name_sync(self):
        repo = athlete_repository.AthleteRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_by_name("bob"))["name"] == "bob"

    def test_list_all_sync(self):
        repo = athlete_repository.AthleteRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.list_all()) == [{"id": 1}]


class TestPOIRepositorySync:
    def test_create_sync(self):
        repo = poi_repository.POIRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.create({"name": "p"})) == 3

    def test_get_by_id_sync(self):
        repo = poi_repository.POIRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_by_id(1))["id"] == 1

    def test_get_nearby_sync(self):
        repo = poi_repository.POIRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_nearby(0.0, 0.0)) == []


class TestTrainingStressRepositorySync:
    def test_upsert_sync(self):
        repo = training_stress_repository.TrainingStressRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.upsert_day(1, "2024-01-01", 10, 10, 10, 10)) is None

    def test_get_history_sync(self):
        repo = training_stress_repository.TrainingStressRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_history(1)) == [{"date": "2024-01-01"}]

    def test_get_latest_sync(self):
        repo = training_stress_repository.TrainingStressRepository(sync_conn=MockSyncConn())
        assert asyncio.run(repo.get_latest(1)) == {"date": "2024-01-01"}
