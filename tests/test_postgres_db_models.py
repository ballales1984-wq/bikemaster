"""Regression tests for the unified sync ORM layer (postgres_db + models).

These tests validate the consolidation of ``TrainingGoalModel`` /
``PlannedWorkoutModel`` into ``db/models.py`` (single source of truth,
re-exported by ``db/postgres_db.py``) and guard against two previously
latent bugs:

* ``get_session`` must be a proper context manager (usable with ``with``);
* ``TrainingGoalModel`` must accept the full goal dict built by the API
  (including ``description`` and ``target_elevation_m``).
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bike_analyzer.backend.db import models, postgres_db


def _memory_session_factory():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(
        engine,
        tables=[
            models.TrainingGoalModel.__table__,
            models.PlannedWorkoutModel.__table__,
        ],
    )
    return sessionmaker(bind=engine)


def test_models_are_single_source_of_truth():
    # postgres_db re-exports the exact same classes defined in models.py
    assert postgres_db.TrainingGoalModel is models.TrainingGoalModel
    assert postgres_db.PlannedWorkoutModel is models.PlannedWorkoutModel
    assert postgres_db.Base is models.Base


def test_training_goal_tablenames():
    assert models.TrainingGoalModel.__tablename__ == "training_goals"
    assert models.PlannedWorkoutModel.__tablename__ == "planned_workouts"


def test_training_goal_accepts_full_dict():
    """The full goal dict built by the API must construct without TypeError."""
    session_factory = _memory_session_factory()
    goal = {
        "athlete_id": 1,
        "title": "Gran Fondo",
        "description": "obiettivo stagione",
        "goal_type": "granfondo",
        "target_date": "2026-09-01",
        "target_distance_km": 150.0,
        "target_elevation_m": 3000.0,
        "status": "active",
    }
    with session_factory() as session:
        db_goal = models.TrainingGoalModel(**goal)
        session.add(db_goal)
        session.commit()
        assert db_goal.id is not None
        assert db_goal.target_elevation_m == 3000.0
        assert db_goal.description == "obiettivo stagione"


def test_planned_workout_defaults():
    session_factory = _memory_session_factory()
    with session_factory() as session:
        workout = models.PlannedWorkoutModel(
            athlete_id=1,
            goal_id=1,
            date="2026-06-01",
            title="Base aerobica",
            workout_type="endurance",
        )
        session.add(workout)
        session.commit()
        assert workout.duration_minutes == 60
        assert workout.target_intensity == 0.5
        assert workout.completed is False


def test_get_session_without_engine_raises():
    """When no engine is configured, get_session must raise on enter (not at call)."""
    import pytest

    if postgres_db.engine is not None:
        pytest.skip("DATABASE_URL configured; sync engine present")
    ctx = postgres_db.get_session()  # constructing must not raise
    with pytest.raises(RuntimeError):
        with ctx:
            pass


def test_helpers_without_engine_are_safe():
    if postgres_db.engine is not None:
        import pytest

        pytest.skip("DATABASE_URL configured; sync engine present")
    assert postgres_db.save_training_goal(1, {"title": "x"}) == 0
    assert postgres_db.get_training_goals(1) == []
