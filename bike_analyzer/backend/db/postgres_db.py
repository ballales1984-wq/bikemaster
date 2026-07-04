"""PostgreSQL/SQLAlchemy database layer.

Provides SQLAlchemy models and session management for PostgreSQL.
Falls back gracefully when SQLAlchemy is not available or DATABASE_URL is not set.
"""

from __future__ import annotations

try:
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import (
        DeclarativeBase,
        Mapped,
        Session,
        declarative_base,
        mapped_column,
        sessionmaker,
    )
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    DeclarativeBase = object
    Mapped = None
    Session = None
    declarative_base = None
    mapped_column = None
    sessionmaker = None
    create_engine = None

from ..config import DATABASE_URL

if SQLALCHEMY_AVAILABLE and DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def get_session():
        with SessionLocal() as session:
            yield session
else:
    engine = None
    SessionLocal = None

    def get_session():
        raise RuntimeError("SQLAlchemy not available or DATABASE_URL not configured")


class Base(DeclarativeBase):
    pass


class TrainingGoalModel(Base):
    __tablename__ = "training_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int | None] = mapped_column()
    title: Mapped[str] = mapped_column()
    goal_type: Mapped[str] = mapped_column(default="granfondo")
    target_date: Mapped[str | None] = mapped_column()
    target_distance_km: Mapped[float | None] = mapped_column()
    status: Mapped[str] = mapped_column(default="active")


class PlannedWorkoutModel(Base):
    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column()
    goal_id: Mapped[int | None] = mapped_column()
    date: Mapped[str] = mapped_column()
    title: Mapped[str] = mapped_column()
    workout_type: Mapped[str] = mapped_column()
    duration_minutes: Mapped[int] = mapped_column(default=60)
    target_intensity: Mapped[float] = mapped_column(default=0.5)


def save_training_goal(athlete_id: int, goal: dict) -> int:
    if not SQLALCHEMY_AVAILABLE or engine is None:
        return 0
    with SessionLocal() as session:
        db_goal = TrainingGoalModel(**goal)
        session.add(db_goal)
        session.commit()
        return db_goal.id


def get_training_goals(athlete_id: int, status: str | None = None) -> list[dict]:
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
                "goal_type": g.goal_type,
                "target_date": g.target_date,
                "target_distance_km": g.target_distance_km,
                "status": g.status,
            }
            for g in query.all()
        ]