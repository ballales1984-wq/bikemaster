"""Tests for the async DB facade used by FastAPI routes.

Uses an on-disk async SQLite database so the multiple sessions opened by the
facade share the same schema/data.
"""

from __future__ import annotations

import asyncio
import os

import pytest

import bike_analyzer.backend.db.async_db as async_db_mod
from bike_analyzer.backend.api import async_db_facade
from bike_analyzer.backend.db.async_db import get_session_factory, init_async_db
from bike_analyzer.backend.db.models import AthleteModel, RideModel


@pytest.fixture
def db_url(tmp_path):
    path = tmp_path / "facade_test.sqlite"
    url = f"sqlite+aiosqlite:///{path}"
    os.environ["DATABASE_URL"] = url
    # Reset module-level cached engine/factory so the new URL takes effect.
    async_db_mod._engine = None
    async_db_mod._session_factory = None
    yield url
    os.environ.pop("DATABASE_URL", None)
    async_db_mod._engine = None
    async_db_mod._session_factory = None


@pytest.fixture
def seeded(db_url):
    asyncio.run(init_async_db())
    factory = get_session_factory()

    async def _seed():
        async with factory() as session:
            athlete = AthleteModel(
                id=1,
                name="Mario",
                age=34,
                weight_kg=72.0,
                height_cm=180.0,
                fat_percentage=12.0,
                years_active=5,
                weekly_sessions=4,
                monthly_hours=20.0,
                annual_hours=240.0,
                experience_level="Advanced",
                goals="granfondo",
                preferred_terrain="hills",
                weekly_volume_km=150.0,
                best_segments="col du chat",
                medical_notes="none",
                equipment="road",
                ftp_watts=280,
                password_hash="hash123",
                tenant_id=1,
            )
            session.add(athlete)
            ride = RideModel(
                id=10,
                athlete_id=1,
                tenant_id=1,
                date="2024-06-15",
                distance_km=35.0,
                duration_minutes=90.0,
                avg_speed_kmh=23.3,
                weight_kg=72.0,
                calories=800.0,
                heart_rate_avg=150.0,
                elevation_gain_m=400.0,
                gps_points='[{"lat": 45.0, "lon": 9.0, "timestamp": "2024-06-15T08:00:00"}]',
                external_source="strava",
                external_id="ext-1",
                title="Morning ride",
            )
            session.add(ride)
            await session.commit()

    asyncio.run(_seed())
    return factory


class TestInitAndSession:
    def test_init_db(self, db_url):
        asyncio.run(async_db_facade.init_db())
        assert async_db_mod._engine is not None

    def test_get_db_session(self, db_url):
        asyncio.run(init_async_db())
        session = asyncio.run(async_db_facade.get_db_session())
        assert session is not None
        asyncio.run(session.close())


class TestGetRide:
    def test_get_ride_found(self, seeded):
        result = asyncio.run(async_db_facade.get_ride(10))
        assert result is not None
        assert result["id"] == 10
        assert result["distance_km"] == 35.0
        assert result["gps_points"] == [
            {"lat": 45.0, "lon": 9.0, "timestamp": "2024-06-15T08:00:00"}
        ]

    def test_get_ride_missing(self, seeded):
        assert asyncio.run(async_db_facade.get_ride(999)) is None

    def test_get_ride_tenant_filter(self, seeded):
        # ride 10 belongs to tenant 1; querying with a different tenant misses.
        assert asyncio.run(async_db_facade.get_ride(10, tenant_id=2)) is None
        assert asyncio.run(async_db_facade.get_ride(10, tenant_id=1)) is not None


class TestGetRidesByAthlete:
    def test_get_rides_by_athlete(self, seeded):
        rows = asyncio.run(async_db_facade.get_rides_by_athlete(1))
        assert len(rows) == 1
        assert rows[0]["id"] == 10

    def test_get_rides_by_athlete_tenant_filter(self, seeded):
        assert asyncio.run(async_db_facade.get_rides_by_athlete(1, tenant_id=2)) == []
        assert len(asyncio.run(async_db_facade.get_rides_by_athlete(1, tenant_id=1))) == 1

    def test_get_rides_by_athlete_limit(self, seeded):
        rows = asyncio.run(async_db_facade.get_rides_by_athlete(1, limit=5))
        assert len(rows) == 1


class TestGetAthlete:
    def test_get_athlete_found(self, seeded):
        result = asyncio.run(async_db_facade.get_athlete(1))
        assert result is not None
        assert result["name"] == "Mario"
        assert result["age"] == 34
        assert result["ftp_watts"] == 280
        assert result["tenant_id"] == 1

    def test_get_athlete_missing(self, seeded):
        assert asyncio.run(async_db_facade.get_athlete(999)) is None

    def test_get_athlete_tenant_filter(self, seeded):
        assert asyncio.run(async_db_facade.get_athlete(1, tenant_id=2)) is None
        assert asyncio.run(async_db_facade.get_athlete(1, tenant_id=1)) is not None


class TestGetAthleteByName:
    def test_found(self, seeded):
        result = asyncio.run(async_db_facade.get_athlete_by_name("Mario"))
        assert result is not None
        assert result["id"] == 1

    def test_missing(self, seeded):
        assert asyncio.run(async_db_facade.get_athlete_by_name("Ghost")) is None

    def test_tenant_filter(self, seeded):
        assert asyncio.run(async_db_facade.get_athlete_by_name("Mario", tenant_id=9)) is None


class TestSaveAthlete:
    def test_insert_new(self, db_url):
        asyncio.run(init_async_db())
        new_id = asyncio.run(
            async_db_facade.save_athlete(
                {"name": "Luigi", "age": 29, "weight_kg": 68.0, "ftp_watts": 260},
                athlete_id=5,
            )
        )
        assert new_id == 5
        saved = asyncio.run(async_db_facade.get_athlete(5))
        assert saved["name"] == "Luigi"
        assert saved["ftp_watts"] == 260

    def test_update_existing(self, seeded):
        updated = asyncio.run(
            async_db_facade.save_athlete(
                {"name": "Mario Rossi", "weight_kg": 75.0}, athlete_id=1
            )
        )
        assert updated == 1
        saved = asyncio.run(async_db_facade.get_athlete(1))
        assert saved["name"] == "Mario Rossi"
        assert saved["weight_kg"] == 75.0
        # Untouched fields retain previous values.
        assert saved["age"] == 34


class TestSaveRide:
    def test_insert_new(self, db_url):
        asyncio.run(init_async_db())
        new_id = asyncio.run(
            async_db_facade.save_ride(
                {
                    "athlete_id": 2,
                    "tenant_id": 2,
                    "date": "2024-07-01",
                    "distance_km": 40.0,
                    "duration_minutes": 100.0,
                    "avg_speed_kmh": 24.0,
                    "gps_points": [{"lat": 1.0, "lon": 2.0}],
                    "title": "Evening ride",
                }
            )
        )
        assert isinstance(new_id, int)
        saved = asyncio.run(async_db_facade.get_ride(new_id))
        assert saved["distance_km"] == 40.0
        assert saved["gps_points"] == [{"lat": 1.0, "lon": 2.0}]

    def test_insert_without_gps(self, db_url):
        asyncio.run(init_async_db())
        new_id = asyncio.run(
            async_db_facade.save_ride(
                {"athlete_id": 3, "date": "2024-07-02", "distance_km": 10.0}
            )
        )
        saved = asyncio.run(async_db_facade.get_ride(new_id))
        assert saved["gps_points"] is None


class TestModelToDictHelpers:
    def test_model_to_dict_with_extra_and_none(self, seeded):
        factory = get_session_factory()

        async def _fetch():
            async with factory() as session:
                row = (
                    await session.execute(
                        __import__("sqlalchemy").select(RideModel).where(RideModel.id == 10)
                    )
                ).scalar_one()
                return async_db_facade._model_to_dict(row, extra={"flag": True})

        result = asyncio.run(_fetch())
        assert result["id"] == 10
        assert result["flag"] is True

    def test_ride_to_dict_malformed_gps(self, seeded):
        factory = get_session_factory()

        async def _fetch():
            async with factory() as session:
                row = (
                    await session.execute(
                        __import__("sqlalchemy").select(RideModel).where(RideModel.id == 10)
                    )
                ).scalar_one()
                row.gps_points = "not-json"
                return async_db_facade._ride_to_dict(row)

        result = asyncio.run(_fetch())
        assert result["gps_points"] is None
