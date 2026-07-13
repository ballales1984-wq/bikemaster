"""PostgreSQL/SQLAlchemy synchronous session layer.

Provides synchronous session management and helper functions for the
``training_goals`` / ``planned_workouts`` tables. The ORM models themselves
live in :mod:`bike_analyzer.backend.db.models` (single source of truth,
shared with the async layer); this module only re-exports them for backward
compatibility and manages the synchronous engine/session.

Falls back gracefully when SQLAlchemy is not available or ``DATABASE_URL`` is
not set.
"""

from __future__ import annotations

from contextlib import contextmanager

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None
    sessionmaker = None
    create_engine = None

from ..settings import get_settings

_s = get_settings()

# Re-export the unified ORM models (single source of truth in models.py).
if SQLALCHEMY_AVAILABLE:
    from .models import Base, PlannedWorkoutModel, TrainingGoalModel
else:  # pragma: no cover - SQLAlchemy is a hard runtime dependency
    Base = None
    PlannedWorkoutModel = None
    TrainingGoalModel = None


if SQLALCHEMY_AVAILABLE and _s.database_url:
    engine = create_engine(_s.database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    @contextmanager
    def get_session():
        """Yield a synchronous SQLAlchemy session (context manager)."""
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
else:
    engine = None
    SessionLocal = None

    @contextmanager
    def get_session():
        """Raise when no synchronous engine is configured."""
        raise RuntimeError("SQLAlchemy not available or DATABASE_URL not configured")
        yield  # pragma: no cover - unreachable, marks this as a generator


def save_training_goal(athlete_id: int, goal: dict) -> int:
    """Persist a training goal and return its id (0 if no engine configured)."""
    if not SQLALCHEMY_AVAILABLE or engine is None:
        return 0
    with SessionLocal() as session:
        db_goal = TrainingGoalModel(**goal)
        session.add(db_goal)
        session.commit()
        return db_goal.id


def get_training_goals(athlete_id: int, status: str | None = None) -> list[dict]:
    """Return training goals for an athlete (empty list if no engine configured)."""
    if not SQLALCHEMY_AVAILABLE or engine is None:
        return []
    with SessionLocal() as session:
        query = session.query(TrainingGoalModel).filter(TrainingGoalModel.athlete_id == athlete_id)
        if status:
            query = query.filter(TrainingGoalModel.status == status)
        return [
            {
                "id": g.id,
                "athlete_id": g.athlete_id,
                "title": g.title,
                "description": g.description,
                "goal_type": g.goal_type,
                "target_date": g.target_date,
                "target_distance_km": g.target_distance_km,
                "target_elevation_m": g.target_elevation_m,
                "status": g.status,
            }
            for g in query.all()
        ]


__all__ = [
    "SQLALCHEMY_AVAILABLE",
    "Base",
    "TrainingGoalModel",
    "PlannedWorkoutModel",
    "engine",
    "SessionLocal",
    "get_session",
    "save_training_goal",
    "get_training_goals",
]
