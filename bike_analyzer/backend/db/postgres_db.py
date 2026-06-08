"""PostgreSQL database layer with SQLAlchemy."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.orm import sessionmaker, Session, relationship
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

from ..config import DB_PATH

Base = declarative_base() if SQLALCHEMY_AVAILABLE else None


class RideModel(Base):
    __tablename__ = "rides"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=True)
    date = Column(String, nullable=False, index=True)
    distance_km = Column(Float, default=0.0)
    duration_minutes = Column(Float, default=0.0)
    avg_speed_kmh = Column(Float, default=0.0)
    weight_kg = Column(Float, default=70.0)
    calories = Column(Float, default=0.0)
    heart_rate_avg = Column(Float, nullable=True)
    elevation_gain_m = Column(Float, nullable=True)
    gps_points = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AthleteModel(Base):
    __tablename__ = "athletes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    age = Column(Integer, default=30)
    weight_kg = Column(Float, default=70.0)
    height_cm = Column(Float, nullable=True)
    fat_percentage = Column(Float, nullable=True)
    years_active = Column(Integer, default=1)
    weekly_sessions = Column(Integer, default=3)
    monthly_hours = Column(Float, default=0.0)
    annual_hours = Column(Float, default=0.0)
    experience_level = Column(String, default="Beginner")
    goals = Column(Text, nullable=True)
    preferred_terrain = Column(String, nullable=True)
    weekly_volume_km = Column(Float, default=0.0)
    best_segments = Column(Text, nullable=True)
    medical_notes = Column(Text, nullable=True)
    equipment = Column(Text, nullable=True)
    ftp_watts = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TrainingLoadModel(Base):
    __tablename__ = "training_loads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date = Column(String, nullable=False, index=True)
    tss = Column(Float, default=0.0)
    atl = Column(Float, default=0.0)
    ctl = Column(Float, default=0.0)
    tsb = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (Index("idx_training_loads_athlete_date", "athlete_id", "date"),)


class TrainingGoalModel(Base):
    __tablename__ = "training_goals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(String, default="granfondo")
    target_date = Column(String, nullable=True)
    target_distance_km = Column(Float, nullable=True)
    target_elevation_m = Column(Float, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PlannedWorkoutModel(Base):
    __tablename__ = "planned_workouts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("training_goals.id"), nullable=True)
    date = Column(String, nullable=False)
    title = Column(String, nullable=False)
    workout_type = Column(String, default="endurance")
    duration_minutes = Column(Integer, default=60)
    target_intensity = Column(Float, default=0.5)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)


_engine = None
_Session = None


def get_engine(db_url: Optional[str] = None):
    """Get or create SQLAlchemy engine."""
    global _engine, _Session
    if _engine:
        return _engine
    
    if not SQLALCHEMY_AVAILABLE:
        raise ImportError("SQLAlchemy non installato. Installa con: pip install sqlalchemy psycopg2-binary")
    
    url = db_url or f"sqlite:///{DB_PATH}"
    _engine = create_engine(url, echo=False)
    _Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def init_postgres_db(db_url: Optional[str] = None):
    """Initialize PostgreSQL database tables."""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


def get_db_session() -> Session:
    """Get database session."""
    if not _Session:
        get_engine()
    return _Session()


@contextmanager
def get_session():
    """Context manager for database sessions."""
    session = get_db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_training_load(athlete_id: int, load_data: dict) -> int:
    """Save ATL/CTL/TSB values for a specific date."""
    with get_session() as session:
        model = TrainingLoadModel(
            athlete_id=athlete_id,
            date=load_data["date"],
            tss=load_data.get("tss", 0),
            atl=load_data.get("atl", 0),
            ctl=load_data.get("ctl", 0),
            tsb=load_data.get("tsb", 0)
        )
        session.add(model)
        session.flush()
        return model.id


def get_training_loads(athlete_id: int, days: int = 30) -> List[dict]:
    """Get training load history for athlete."""
    with get_session() as session:
        from sqlalchemy import desc
        models = session.query(TrainingLoadModel).filter(
            TrainingLoadModel.athlete_id == athlete_id
        ).order_by(desc(TrainingLoadModel.date)).limit(days).all()
        
        return [
            {"date": m.date, "tss": m.tss, "atl": m.atl, "ctl": m.ctl, "tsb": m.tsb}
            for m in models
        ]


def save_training_goal(athlete_id: int, goal: dict) -> int:
    """Save a training goal for athlete."""
    with get_session() as session:
        model = TrainingGoalModel(
            athlete_id=athlete_id,
            title=goal["title"],
            description=goal.get("description"),
            goal_type=goal.get("goal_type", "granfondo"),
            target_date=goal.get("target_date"),
            target_distance_km=goal.get("target_distance_km"),
            target_elevation_m=goal.get("target_elevation_m"),
            status=goal.get("status", "active")
        )
        session.add(model)
        session.flush()
        return model.id


def get_training_goals(athlete_id: int, status: Optional[str] = None) -> List[dict]:
    """Get training goals for athlete."""
    with get_session() as session:
        query = session.query(TrainingGoalModel).filter(
            TrainingGoalModel.athlete_id == athlete_id
        )
        if status:
            query = query.filter(TrainingGoalModel.status == status)
        
        models = query.order_by(TrainingGoalModel.created_at.desc()).all()
        return [
            {
                "id": m.id, "athlete_id": m.athlete_id, "title": m.title,
                "description": m.description, "goal_type": m.goal_type,
                "target_date": m.target_date, "target_distance_km": m.target_distance_km,
                "target_elevation_m": m.target_elevation_m, "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in models
        ]


def save_planned_workout(athlete_id: int, workout: dict) -> int:
    """Save a planned workout."""
    with get_session() as session:
        model = PlannedWorkoutModel(
            athlete_id=athlete_id,
            goal_id=workout.get("goal_id"),
            date=workout["date"],
            title=workout["title"],
            workout_type=workout.get("workout_type", "endurance"),
            duration_minutes=workout.get("duration_minutes", 60),
            target_intensity=workout.get("target_intensity", 0.5),
            completed=False
        )
        session.add(model)
        session.flush()
        return model.id


def get_planned_workouts(athlete_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[dict]:
    """Get planned workouts for athlete."""
    with get_session() as session:
        query = session.query(PlannedWorkoutModel).filter(
            PlannedWorkoutModel.athlete_id == athlete_id
        )
        if start_date and end_date:
            query = query.filter(PlannedWorkoutModel.date >= start_date)
            query = query.filter(PlannedWorkoutModel.date <= end_date)
        
        models = query.order_by(PlannedWorkoutModel.date).all()
        return [
            {
                "id": m.id, "athlete_id": m.athlete_id, "goal_id": m.goal_id,
                "date": m.date, "title": m.title, "workout_type": m.workout_type,
                "duration_minutes": m.duration_minutes, "target_intensity": m.target_intensity,
                "completed": m.completed, "completed_at": m.completed_at.isoformat() if m.completed_at else None
            }
            for m in models
        ]


def complete_workout(workout_id: int) -> bool:
    """Mark a workout as completed."""
    with get_session() as session:
        model = session.query(PlannedWorkoutModel).filter(PlannedWorkoutModel.id == workout_id).first()
        if model:
            model.completed = True
            model.completed_at = datetime.now(timezone.utc)
            return True
        return False


__all__ = [
    "SQLALCHEMY_AVAILABLE",
    "get_engine",
    "init_postgres_db",
    "get_db_session",
    "get_session",
    "save_training_load",
    "get_training_loads",
    "save_training_goal",
    "get_training_goals",
    "save_planned_workout",
    "get_planned_workouts",
    "complete_workout",
    "RideModel",
    "AthleteModel",
    "TrainingLoadModel",
    "TrainingGoalModel",
    "PlannedWorkoutModel"
]