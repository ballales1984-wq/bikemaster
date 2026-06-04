"""SQLAlchemy ORM models and session."""
from __future__ import annotations
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
from typing import List, Optional

Base = declarative_base()
engine = create_engine("sqlite:///./rides.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

class RideORM(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)
    distance_km = Column(Float, default=0)
    duration_minutes = Column(Float, default=0)
    avg_speed_kmh = Column(Float, default=0)
    weight_kg = Column(Float, default=70)
    calories = Column(Float, default=0)
    heart_rate_avg = Column(Float)
    elevation_gain_m = Column(Float)
    gps_points = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    athlete_id = Column(Integer, ForeignKey("athletes.id"))

    athlete = relationship("AthleteORM", back_populates="rides")

class AthleteORM(Base):
    __tablename__ = "athletes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    age = Column(Integer, default=30)
    weight_kg = Column(Float, default=70)
    height_cm = Column(Float)
    fat_percentage = Column(Float)
    years_active = Column(Integer, default=1)
    weekly_sessions = Column(Integer, default=3)
    monthly_hours = Column(Float, default=0)
    annual_hours = Column(Float, default=0)
    experience_level = Column(String, default="Beginner")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    rides = relationship("RideORM", back_populates="athlete")

class MetricORM(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"))
    ride_id = Column(Integer, ForeignKey("rides.id"))
    fatigue_score = Column(Float)
    recovery_hours = Column(Float)
    calories_per_km = Column(Float)
    efficiency_score = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def init_orm():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()

def orm_to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}