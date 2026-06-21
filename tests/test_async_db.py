"""Comprehensive tests for async_db module."""

from datetime import UTC, datetime

import pytest

from bike_analyzer.backend.db import async_db


@pytest.fixture(autouse=True)
def reset_module_and_settings(monkeypatch):
    """Reset module-level state and settings before each test."""
    import bike_analyzer.backend.settings as settings_mod
    settings_mod._settings = None
    async_db._engine = None
    async_db._async_session_factory = None
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("DB_PATH", ":memory:")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("GROQ_API_KEY", "test-key-for-unit-tests")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield
    async_db._engine = None
    async_db._async_session_factory = None


def test_get_engine_lazy():
    async_db._engine = None
    engine = async_db._get_engine()
    assert engine is not None


def test_get_engine_caching():
    async_db._engine = None
    engine1 = async_db._get_engine()
    engine2 = async_db._get_engine()
    assert engine1 is engine2


def test_disabled_async_session_factory():
    result = async_db._disabled_async_session_factory()
    assert result is None


def test_get_session_factory_returns_callable():
    async_db._async_session_factory = None
    factory = async_db.get_session_factory()
    assert callable(factory)


def test_get_session_factory_caching():
    async_db._async_session_factory = None
    factory1 = async_db.get_session_factory()
    factory2 = async_db.get_session_factory()
    assert factory1 is factory2


async def test_init_async_db():
    await async_db.init_async_db()
    engine = async_db._engine
    assert engine is not None


async def test_get_async_session():
    await async_db.init_async_db()
    session = await async_db.get_async_session()
    assert session is not None
    await session.close()


async def _setup_db():
    """Helper to ensure DB is initialized with tables."""
    await async_db.init_async_db()


async def test_save_and_get_ride_async():
    await _setup_db()
    ride = {
        "athlete_id": 1,
        "date": "2024-06-15",
        "distance_km": 25.5,
        "duration_minutes": 60,
        "avg_speed_kmh": 25.5,
        "weight_kg": 75,
        "calories": 400,
        "heart_rate_avg": 150,
        "elevation_gain_m": 300,
    }
    ride_id = await async_db.save_ride_async(ride)
    assert ride_id is not None
    assert isinstance(ride_id, int)

    fetched = await async_db.get_ride_async(ride_id)
    assert fetched is not None
    assert fetched["athlete_id"] == 1
    assert fetched["date"] == "2024-06-15"
    assert fetched["distance_km"] == 25.5


async def test_save_ride_async_with_gps_points():
    await _setup_db()
    gps_data = [{"lat": 45.0, "lon": 7.0}, {"lat": 45.1, "lon": 7.1}]
    ride = {
        "athlete_id": 2,
        "date": "2024-06-16",
        "distance_km": 10.0,
        "gps_points": gps_data,
    }
    ride_id = await async_db.save_ride_async(ride)

    fetched = await async_db.get_ride_async(ride_id)
    assert fetched is not None
    assert fetched["gps_points"] == gps_data


async def test_save_ride_async_default_values():
    await _setup_db()
    ride = {"date": "2024-06-17"}
    ride_id = await async_db.save_ride_async(ride)

    fetched = await async_db.get_ride_async(ride_id)
    assert fetched is not None
    assert fetched["athlete_id"] is None
    assert fetched["distance_km"] == 0
    assert fetched["duration_minutes"] == 0
    assert fetched["avg_speed_kmh"] == 0
    assert fetched["calories"] == 0


async def test_get_ride_async_not_found():
    await _setup_db()
    result = await async_db.get_ride_async(99999)
    assert result is None


async def test_get_all_rides_async_empty():
    await _setup_db()
    rides = await async_db.get_all_rides_async()
    assert rides == []


async def test_get_all_rides_async_multiple():
    await _setup_db()
    await async_db.save_ride_async({"date": "2024-06-10", "distance_km": 10.0})
    await async_db.save_ride_async({"date": "2024-06-12", "distance_km": 20.0})
    await async_db.save_ride_async({"date": "2024-06-08", "distance_km": 15.0})

    rides = await async_db.get_all_rides_async()
    assert len(rides) == 3
    dates = [r["date"] for r in rides]
    assert dates == ["2024-06-12", "2024-06-10", "2024-06-08"]


async def test_get_rides_by_athlete_async_empty():
    await _setup_db()
    rides = await async_db.get_rides_by_athlete_async(999)
    assert rides == []


async def test_get_rides_by_athlete_async_multiple():
    await _setup_db()
    await async_db.save_ride_async({"athlete_id": 1, "date": "2024-06-10", "distance_km": 10.0})
    await async_db.save_ride_async({"athlete_id": 1, "date": "2024-06-12", "distance_km": 20.0})
    await async_db.save_ride_async({"athlete_id": 2, "date": "2024-06-11", "distance_km": 15.0})

    rides = await async_db.get_rides_by_athlete_async(1)
    assert len(rides) == 2
    dates = [r["date"] for r in rides]
    assert dates == ["2024-06-12", "2024-06-10"]


async def test_delete_ride_async_success():
    await _setup_db()
    ride_id = await async_db.save_ride_async({"date": "2024-06-15"})

    result = await async_db.delete_ride_async(ride_id)
    assert result is True

    fetched = await async_db.get_ride_async(ride_id)
    assert fetched is None


async def test_delete_ride_async_not_found():
    await _setup_db()
    result = await async_db.delete_ride_async(99999)
    assert result is False


async def test_save_athlete_async():
    await _setup_db()
    athlete = {
        "name": "Test Athlete",
        "age": 25,
        "weight_kg": 70,
        "experience_level": "Intermediate",
    }
    athlete_id = await async_db.save_athlete_async(athlete)
    assert athlete_id is not None
    assert isinstance(athlete_id, int)


async def test_save_athlete_async_default_values():
    await _setup_db()
    athlete = {"name": "Min Athlete"}
    athlete_id = await async_db.save_athlete_async(athlete)

    from sqlalchemy import select

    from bike_analyzer.backend.db.models import AthleteModel

    session = await async_db.get_async_session()
    async with session as s:
        result = await s.execute(
            select(AthleteModel).where(AthleteModel.id == athlete_id)
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.age == 30
        assert row.weight_kg == 70
        assert row.years_active == 1
        assert row.weekly_sessions == 3
        assert row.experience_level == "Beginner"


async def test_close_async_db():
    await _setup_db()
    assert async_db._engine is not None

    await async_db.close_async_db()
    assert async_db._engine is None
    assert async_db._async_session_factory is None


async def test_close_async_db_when_already_closed():
    async_db._engine = None
    async_db._async_session_factory = None

    await async_db.close_async_db()
    assert async_db._engine is None


def test_ride_model_to_dict_with_gps():
    class MockRow:
        id = 1
        athlete_id = 1
        date = "2024-06-15"
        distance_km = 25.0
        duration_minutes = 60
        avg_speed_kmh = 25.0
        weight_kg = 70
        calories = 400
        heart_rate_avg = 150
        elevation_gain_m = 200
        gps_points = '[{"lat": 45.0, "lon": 7.0}]'
        created_at = datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC)

    result = async_db._ride_model_to_dict(MockRow())
    assert result["id"] == 1
    assert result["gps_points"] == [{"lat": 45.0, "lon": 7.0}]


def test_ride_model_to_dict_without_gps():
    class MockRow:
        id = 2
        athlete_id = None
        date = "2024-06-16"
        distance_km = 10.0
        duration_minutes = 30
        avg_speed_kmh = 20.0
        weight_kg = 70
        calories = 150
        heart_rate_avg = None
        elevation_gain_m = None
        gps_points = None
        created_at = datetime(2024, 6, 16, 10, 0, 0, tzinfo=UTC)

    result = async_db._ride_model_to_dict(MockRow())
    assert result["id"] == 2
    assert result["gps_points"] is None


async def test_full_crud_flow():
    await _setup_db()

    athlete_id = await async_db.save_athlete_async({"name": "Flow Athlete"})

    ride = {
        "athlete_id": athlete_id,
        "date": "2024-06-20",
        "distance_km": 30.0,
        "duration_minutes": 90,
        "avg_speed_kmh": 20.0,
        "weight_kg": 75,
        "calories": 500,
        "heart_rate_avg": 160,
        "elevation_gain_m": 400,
        "gps_points": [{"lat": 1.0, "lon": 2.0}],
    }
    ride_id = await async_db.save_ride_async(ride)

    fetched_ride = await async_db.get_ride_async(ride_id)
    assert fetched_ride["athlete_id"] == athlete_id
    assert fetched_ride["gps_points"] == [{"lat": 1.0, "lon": 2.0}]

    deleted = await async_db.delete_ride_async(ride_id)
    assert deleted is True
    assert await async_db.get_ride_async(ride_id) is None


async def test_save_ride_no_gps_points():
    await _setup_db()
    ride = {
        "athlete_id": 1,
        "date": "2024-06-18",
        "distance_km": 50.0,
    }
    ride_id = await async_db.save_ride_async(ride)

    fetched = await async_db.get_ride_async(ride_id)
    assert fetched["gps_points"] is None


async def test_save_ride_empty_gps_points_list():
    await _setup_db()
    ride = {
        "athlete_id": 1,
        "date": "2024-06-19",
        "gps_points": [],
    }
    ride_id = await async_db.save_ride_async(ride)

    fetched = await async_db.get_ride_async(ride_id)
    assert fetched["gps_points"] is None


def test_module_not_found_fallback():
    import unittest.mock as mock

    async_db._engine = None
    async_db._async_session_factory = None

    def fake_create_async_engine(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'aiosqlite.driver'")

    with mock.patch.object(
        async_db, "create_async_engine", side_effect=fake_create_async_engine
    ):
        engine = async_db._get_engine()
        assert hasattr(engine, "dialect")
        assert engine.dialect == "sqlite+aiosqlite-unavailable"


def test_module_not_found_re_raises_other_errors():
    import unittest.mock as mock

    async_db._engine = None
    async_db._async_session_factory = None

    def fake_create_async_engine(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'some_other_module'")

    with (
        mock.patch.object(
            async_db, "create_async_engine", side_effect=fake_create_async_engine
        ),
        pytest.raises(ModuleNotFoundError),
    ):
        async_db._get_engine()


async def test_get_session_factory_returns_disabled_when_aiosqlite_unavailable(monkeypatch):
    from types import SimpleNamespace

    async_db._engine = None
    async_db._async_session_factory = None

    monkeypatch.setattr(async_db, "_get_engine", lambda: SimpleNamespace(dialect="sqlite+aiosqlite-unavailable", url="sqlite+aiosqlite:///"))
    factory = async_db.get_session_factory()
    assert factory is async_db._disabled_async_session_factory