"""Tests for PostgreSQL database layer with SQLAlchemy."""
import pytest
from sqlalchemy.exc import IntegrityError

from bike_analyzer.backend.db.postgres_db import (
    SQLALCHEMY_AVAILABLE,
    AthleteModel,
    Base,
    PlannedWorkoutModel,
    RideModel,
    TrainingGoalModel,
    TrainingLoadModel,
    complete_workout,
    get_db_session,
    get_engine,
    get_planned_workouts,
    get_session,
    get_training_goals,
    get_training_loads,
    init_postgres_db,
    save_planned_workout,
    save_training_goal,
    save_training_load,
)


@pytest.fixture
def postgres_module():
    """Import and reset postgres_db module state."""
    import bike_analyzer.backend.db.postgres_db as pg_module

    pg_module._engine = None
    pg_module._Session = None
    yield pg_module
    pg_module._engine = None
    pg_module._Session = None


@pytest.fixture
def in_memory_engine(postgres_module):
    """Create in-memory SQLite engine for testing."""
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy not available")
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_engine):
    """Create a database session for testing."""
    session = get_db_session()
    yield session
    session.close()


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestModels:
    """Test SQLAlchemy model definitions."""

    def test_base_has_metadata(self):
        assert hasattr(Base, "metadata")

    def test_base_has_tables(self):
        tables = Base.metadata.tables
        assert "rides" in tables
        assert "athletes" in tables
        assert "training_loads" in tables
        assert "training_goals" in tables
        assert "planned_workouts" in tables

    def test_ride_model_table_name(self):
        assert RideModel.__tablename__ == "rides"

    def test_ride_model_columns(self):
        from sqlalchemy import inspect

        mapper = inspect(RideModel)
        columns = {c.key for c in mapper.columns}
        assert "id" in columns
        assert "athlete_id" in columns
        assert "date" in columns
        assert "distance_km" in columns
        assert "duration_minutes" in columns
        assert "avg_speed_kmh" in columns
        assert "weight_kg" in columns
        assert "calories" in columns
        assert "heart_rate_avg" in columns
        assert "elevation_gain_m" in columns
        assert "gps_points" in columns
        assert "created_at" in columns

    def test_athlete_model_table_name(self):
        assert AthleteModel.__tablename__ == "athletes"

    def test_athlete_model_columns(self):
        from sqlalchemy import inspect

        mapper = inspect(AthleteModel)
        columns = {c.key for c in mapper.columns}
        assert "id" in columns
        assert "name" in columns
        assert "age" in columns
        assert "weight_kg" in columns
        assert "height_cm" in columns
        assert "fat_percentage" in columns
        assert "years_active" in columns
        assert "weekly_sessions" in columns
        assert "monthly_hours" in columns
        assert "annual_hours" in columns
        assert "experience_level" in columns
        assert "goals" in columns
        assert "preferred_terrain" in columns
        assert "weekly_volume_km" in columns
        assert "best_segments" in columns
        assert "medical_notes" in columns
        assert "equipment" in columns
        assert "ftp_watts" in columns
        assert "created_at" in columns

    def test_training_load_model_table_name(self):
        assert TrainingLoadModel.__tablename__ == "training_loads"

    def test_training_load_model_columns(self):
        from sqlalchemy import inspect

        mapper = inspect(TrainingLoadModel)
        columns = {c.key for c in mapper.columns}
        assert "id" in columns
        assert "athlete_id" in columns
        assert "date" in columns
        assert "tss" in columns
        assert "atl" in columns
        assert "ctl" in columns
        assert "tsb" in columns
        assert "created_at" in columns

    def test_training_load_model_indexes(self):
        table_args = TrainingLoadModel.__table_args__
        index_found = False
        for arg in table_args:
            if hasattr(arg, "name") and "idx_training_loads_athlete_date" in arg.name:
                index_found = True
                break
        assert index_found, "Expected idx_training_loads_athlete_date index"

    def test_training_goal_model_table_name(self):
        assert TrainingGoalModel.__tablename__ == "training_goals"

    def test_training_goal_model_columns(self):
        from sqlalchemy import inspect

        mapper = inspect(TrainingGoalModel)
        columns = {c.key for c in mapper.columns}
        assert "id" in columns
        assert "athlete_id" in columns
        assert "title" in columns
        assert "description" in columns
        assert "goal_type" in columns
        assert "target_date" in columns
        assert "target_distance_km" in columns
        assert "target_elevation_m" in columns
        assert "status" in columns
        assert "created_at" in columns

    def test_planned_workout_model_table_name(self):
        assert PlannedWorkoutModel.__tablename__ == "planned_workouts"

    def test_planned_workout_model_columns(self):
        from sqlalchemy import inspect

        mapper = inspect(PlannedWorkoutModel)
        columns = {c.key for c in mapper.columns}
        assert "id" in columns
        assert "athlete_id" in columns
        assert "goal_id" in columns
        assert "date" in columns
        assert "title" in columns
        assert "workout_type" in columns
        assert "duration_minutes" in columns
        assert "target_intensity" in columns
        assert "completed" in columns
        assert "completed_at" in columns

    def test_all_models_inherited_from_base(self):
        models = [RideModel, AthleteModel, TrainingLoadModel, TrainingGoalModel, PlannedWorkoutModel]
        for model in models:
            assert issubclass(model, Base)


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestEngineManagement:
    """Test engine and session management."""

    def test_get_engine_returns_engine(self, postgres_module):
        engine = get_engine("sqlite:///:memory:")
        assert engine is not None
        assert str(engine.url).startswith("sqlite")

    def test_get_engine_reuses_existing(self, postgres_module, in_memory_engine):
        engine1 = get_engine("sqlite:///:memory:")
        engine2 = get_engine("sqlite:///:different:/")
        assert engine1 is engine2

    def test_get_engine_raises_without_sqlalchemy(self, postgres_module, monkeypatch):
        original = postgres_module.SQLALCHEMY_AVAILABLE
        monkeypatch.setattr(postgres_module, "SQLALCHEMY_AVAILABLE", False)
        postgres_module._engine = None
        postgres_module._Session = None
        with pytest.raises(ImportError, match="SQLAlchemy"):
            get_engine()
        monkeypatch.setattr(postgres_module, "SQLALCHEMY_AVAILABLE", original)

    def test_init_postgres_db_creates_tables(self, postgres_module):
        from sqlalchemy import inspect

        engine = init_postgres_db("sqlite:///:memory:")
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "rides" in table_names
        assert "athletes" in table_names
        assert "training_loads" in table_names
        assert "training_goals" in table_names
        assert "planned_workouts" in table_names

    def test_get_db_session_returns_session(self, in_memory_engine):
        session = get_db_session()
        assert session is not None
        session.close()

    def test_get_db_session_inits_engine_if_needed(self, postgres_module):
        postgres_module._engine = None
        postgres_module._Session = None
        session = get_db_session()
        assert session is not None
        session.close()

    def test_get_session_context_manager(self, in_memory_engine):
        with get_session() as session:
            assert session is not None
            athlete = AthleteModel(name="Test Athlete")
            session.add(athlete)
        assert True

    def test_get_session_commits_on_success(self, in_memory_engine):
        with get_session() as session:
            athlete = AthleteModel(name="Committed Athlete")
            session.add(athlete)
        with get_session() as session:
            athletes = session.query(AthleteModel).filter(AthleteModel.name == "Committed Athlete").all()
            assert len(athletes) == 1

    def test_get_session_sync_parameter(self, in_memory_engine):
        with get_session():
            pass


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestTrainingLoad:
    """Test training load CRUD operations."""

    def test_save_training_load(self, in_memory_engine):
        load_id = save_training_load(1, {"date": "2024-01-15", "tss": 50.0, "atl": 45.0, "ctl": 55.0, "tsb": -5.0})
        assert load_id is not None
        assert load_id > 0

    def test_save_training_load_with_defaults(self, in_memory_engine):
        load_id = save_training_load(1, {"date": "2024-01-16"})
        assert load_id is not None

    def test_save_training_load_partial_data(self, in_memory_engine):
        load_id = save_training_load(1, {"date": "2024-01-17", "tss": 75.0})
        assert load_id is not None

    def test_get_training_loads(self, in_memory_engine):
        save_training_load(1, {"date": "2024-01-15", "tss": 50.0})
        save_training_load(1, {"date": "2024-01-16", "tss": 60.0})
        loads = get_training_loads(1, days=10)
        assert len(loads) == 2
        assert loads[0]["date"] in ["2024-01-15", "2024-01-16"]

    def test_get_training_loads_empty(self, in_memory_engine):
        loads = get_training_loads(999, days=10)
        assert loads == []

    def test_get_training_loads_respects_limit(self, in_memory_engine):
        for i in range(5):
            save_training_load(1, {"date": f"2024-01-{i+10:02d}", "tss": float(i)})
        loads = get_training_loads(1, days=2)
        assert len(loads) == 2


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestTrainingGoal:
    """Test training goal CRUD operations."""

    def test_save_training_goal(self, in_memory_engine):
        goal_id = save_training_goal(1, {"title": "Train for Gran Fondo", "description": "Build endurance"})
        assert goal_id is not None
        assert goal_id > 0

    def test_save_training_goal_with_all_fields(self, in_memory_engine):
        goal_id = save_training_goal(
            1,
            {
                "title": "Full Goal",
                "description": "Description",
                "goal_type": "race",
                "target_date": "2024-12-31",
                "target_distance_km": 200.0,
                "target_elevation_m": 3000.0,
                "status": "active",
            },
        )
        assert goal_id is not None

    def test_get_training_goals(self, in_memory_engine):
        save_training_goal(1, {"title": "Goal 1"})
        save_training_goal(1, {"title": "Goal 2"})
        goals = get_training_goals(1)
        assert len(goals) == 2
        assert goals[0]["title"] in ["Goal 1", "Goal 2"]

    def test_get_training_goals_empty(self, in_memory_engine):
        goals = get_training_goals(999)
        assert goals == []

    def test_get_training_goals_filtered_by_status(self, in_memory_engine):
        save_training_goal(1, {"title": "Active Goal", "status": "active"})
        save_training_goal(1, {"title": "Completed Goal", "status": "completed"})
        active_goals = get_training_goals(1, status="active")
        assert len(active_goals) == 1
        assert active_goals[0]["status"] == "active"

    def test_get_training_goals_returns_defaults(self, in_memory_engine):
        save_training_goal(1, {"title": "Default Goal"})
        goals = get_training_goals(1)
        assert goals[0]["goal_type"] == "granfondo"
        assert goals[0]["status"] == "active"


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestPlannedWorkout:
    """Test planned workout CRUD operations."""

    def test_save_planned_workout(self, in_memory_engine):
        workout_id = save_planned_workout(1, {"date": "2024-01-20", "title": "Endurance Ride"})
        assert workout_id is not None
        assert workout_id > 0

    def test_save_planned_workout_with_all_fields(self, in_memory_engine):
        workout_id = save_planned_workout(
            1,
            {
                "date": "2024-01-21",
                "title": "Interval Session",
                "workout_type": "interval",
                "duration_minutes": 90,
                "target_intensity": 0.8,
                "goal_id": 1,
            },
        )
        assert workout_id is not None

    def test_get_planned_workouts(self, in_memory_engine):
        save_planned_workout(1, {"date": "2024-01-20", "title": "Workout 1"})
        save_planned_workout(1, {"date": "2024-01-21", "title": "Workout 2"})
        workouts = get_planned_workouts(1)
        assert len(workouts) == 2

    def test_get_planned_workouts_empty(self, in_memory_engine):
        workouts = get_planned_workouts(999)
        assert workouts == []

    def test_get_planned_workouts_with_date_range(self, in_memory_engine):
        save_planned_workout(1, {"date": "2024-01-15", "title": "Before Range"})
        save_planned_workout(1, {"date": "2024-01-20", "title": "In Range"})
        save_planned_workout(1, {"date": "2024-01-25", "title": "After Range"})
        workouts = get_planned_workouts(1, start_date="2024-01-18", end_date="2024-01-22")
        assert len(workouts) == 1
        assert workouts[0]["date"] == "2024-01-20"

    def test_get_planned_workouts_defaults(self, in_memory_engine):
        save_planned_workout(1, {"date": "2024-01-20", "title": "Default Workout"})
        workouts = get_planned_workouts(1)
        assert workouts[0]["workout_type"] == "endurance"
        assert workouts[0]["duration_minutes"] == 60
        assert workouts[0]["target_intensity"] == 0.5
        assert workouts[0]["completed"] is False

    def test_complete_workout(self, in_memory_engine):
        workout_id = save_planned_workout(1, {"date": "2024-01-20", "title": "Workout to Complete"})
        result = complete_workout(workout_id)
        assert result is True
        workouts = get_planned_workouts(1)
        assert workouts[0]["completed"] is True

    def test_complete_workout_not_found(self, in_memory_engine):
        result = complete_workout(99999)
        assert result is False


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestForeignKeyRelationships:
    """Test foreign key relationships and constraints."""

    def test_training_load_requires_athlete(self, db_session):
        model = TrainingLoadModel(date="2024-01-15")
        db_session.add(model)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_training_goal_requires_athlete_and_title(self, db_session):
        model = TrainingGoalModel()
        db_session.add(model)
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.skipif(SQLALCHEMY_AVAILABLE, reason="SQLAlchemy available")
class TestSQLAlchemyNotAvailable:
    """Test graceful handling when SQLAlchemy is not installed."""

    def test_models_are_none(self):
        assert Base is None

    def test_save_training_load_raises_import_error(self):
        with pytest.raises(ImportError):
            save_training_load(1, {"date": "2024-01-15"})

    def test_get_training_loads_raises_import_error(self):
        with pytest.raises(ImportError):
            get_training_loads(1)

    def test_get_engine_raises_import_error(self):
        import bike_analyzer.backend.db.postgres_db as pg_module

        original = pg_module.SQLALCHEMY_AVAILABLE
        pg_module.SQLALCHEMY_AVAILABLE = False
        pg_module._engine = None
        pg_module._Session = None
        try:
            with pytest.raises(ImportError, match="SQLAlchemy"):
                pg_module.get_engine()
        finally:
            pg_module.SQLALCHEMY_AVAILABLE = original


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestSessionRollbackOnError:
    """Test session rollback behavior on errors."""

    def test_session_rolls_back_on_exception(self, postgres_module):
        engine = get_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with pytest.raises(ValueError, match="Test error"), get_session() as session:
            athlete = AthleteModel(name="Test Athlete")
            session.add(athlete)
            raise ValueError("Test error")
        with get_session() as session:
            athletes = session.query(AthleteModel).all()
            assert len(athletes) == 0
