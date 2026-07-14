"""Tests for synchronous DB layer (postgres_db).

Covers:
- get_session context manager (with and without engine)
- save_training_goal CRUD
- get_training_goals with optional status filter
- Graceful degradation when DATABASE_URL is unset
"""

from __future__ import annotations

import os

import pytest

from bike_analyzer.backend.db import postgres_db
from bike_analyzer.backend.db.models import Base, PlannedWorkoutModel, TrainingGoalModel


@pytest.fixture(autouse=True)
def _isolate_db_module(tmp_path):
    """Reload postgres_db to pick up a fresh settings/database_url state."""
    import importlib

    import bike_analyzer.backend.db.postgres_db as mod

    db_file = str(tmp_path / "test_postgres.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    importlib.reload(mod)
    Base.metadata.create_all(mod.engine)
    yield mod
    os.environ.pop("DATABASE_URL", None)


class TestGetSession:
    def test_context_manager_yields_active_session(self):
        with postgres_db.get_session() as session:
            assert session is not None

    def test_get_session_without_engine_raises(self):
        os.environ.pop("DATABASE_URL", None)
        import importlib

        import bike_analyzer.backend.db.postgres_db as mod

        importlib.reload(mod)
        with pytest.raises(RuntimeError, match="SQLAlchemy not available or DATABASE_URL not configured"):
            with mod.get_session():
                pass


class TestSaveTrainingGoal:
    def test_returns_id(self):
        goal_id = postgres_db.save_training_goal(
            athlete_id=1,
            goal={
                "title": "Gran Fondo",
                "description": "stagione",
                "goal_type": "granfondo",
                "target_date": "2026-09-01",
                "target_distance_km": 150.0,
                "target_elevation_m": 3000.0,
                "status": "active",
            },
        )
        assert goal_id > 0

    def test_save_and_retrieve_roundtrip(self):
        postgres_db.save_training_goal(
            athlete_id=2,
            goal={
                "title": "Maratona",
                "goal_type": "marathon",
                "target_date": "2026-10-01",
                "target_distance_km": 42.0,
                "status": "active",
            },
        )
        goals = postgres_db.get_training_goals(athlete_id=2)
        assert len(goals) == 1
        assert goals[0]["title"] == "Maratona"
        assert goals[0]["goal_type"] == "marathon"
        assert goals[0]["athlete_id"] == 2

    def test_get_training_goals_filters_by_status(self):
        postgres_db.save_training_goal(athlete_id=3, goal={"title": "G1", "status": "active"})
        postgres_db.save_training_goal(athlete_id=3, goal={"title": "G2", "status": "completed"})
        active = postgres_db.get_training_goals(athlete_id=3, status="active")
        assert len(active) == 1
        assert active[0]["title"] == "G1"

    def test_get_training_goals_empty_for_unknown_athlete(self):
        goals = postgres_db.get_training_goals(athlete_id=999)
        assert goals == []

    def test_save_returns_zero_when_no_engine(self):
        os.environ.pop("DATABASE_URL", None)
        import importlib

        import bike_analyzer.backend.db.postgres_db as mod

        importlib.reload(mod)
        goal_id = mod.save_training_goal(athlete_id=1, goal={"title": "X"})
        assert goal_id == 0

    def test_get_training_goals_returns_empty_when_no_engine(self):
        os.environ.pop("DATABASE_URL", None)
        import importlib

        import bike_analyzer.backend.db.postgres_db as mod

        importlib.reload(mod)
        goals = mod.get_training_goals(athlete_id=1)
        assert goals == []


class TestModelReexports:
    def test_training_goal_model_reexported(self):
        assert postgres_db.TrainingGoalModel is TrainingGoalModel

    def test_planned_workout_model_reexported(self):
        assert postgres_db.PlannedWorkoutModel is PlannedWorkoutModel

    def test_base_reexported(self):
        assert postgres_db.Base is Base

    def test_training_goal_tablename(self):
        assert postgres_db.TrainingGoalModel.__tablename__ == "training_goals"

    def test_planned_workout_tablename(self):
        assert postgres_db.PlannedWorkoutModel.__tablename__ == "planned_workouts"
