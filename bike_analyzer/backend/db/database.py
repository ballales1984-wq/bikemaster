"""SQLite database layer."""
from __future__ import annotations
from contextlib import contextmanager
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()

class RideORM(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True)
    date = Column(String, nullable=False)
    distance_km = Column(Float, default=0.0)
    duration_minutes = Column(Float, default=0.0)
    avg_speed_kmh = Column(Float, default=0.0)
    weight_kg = Column(Float, default=70.0)
    calories = Column(Float, default=0.0)
    heart_rate_avg = Column(Float, nullable=True)
    elevation_gain_m = Column(Float, nullable=True)

class Database:
    def __init__(self, db_path: str = "rides.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        session = self.SessionLocal()
        try: yield session; session.commit()
        except Exception: session.rollback(); raise
        finally: session.close()

    def save_ride(self, ride: dict) -> int:
        ride_orm = RideORM(**ride)
        with self.get_session() as s: s.add(ride_orm); s.refresh(ride_orm); return ride_orm.id

    def get_ride(self, ride_id: int) -> Optional[dict]:
        with self.get_session() as s: r = s.query(RideORM).get(ride_id); return r.__dict__ if r else None

    def get_all_rides(self) -> List[dict]:
        with self.get_session() as s: return [r.__dict__ for r in s.query(RideORM).all()]