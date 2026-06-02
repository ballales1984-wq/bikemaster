"""
Unified ORM models for Ride, GPSPoint, Segment.
Single source of truth for database schema.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RideORM(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(5000), nullable=True)
    sport_type = Column(String(50), nullable=False, default="cycling")
    source = Column(String(100), nullable=True)
    external_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    total_distance_km = Column(Float, default=0.0)
    total_duration_seconds = Column(Float, default=0.0)
    avg_speed_kmh = Column(Float, default=0.0)
    max_speed_kmh = Column(Float, default=0.0)
    point_count = Column(Integer, default=0)

    gps_points = relationship("GPSPointORM", back_populates="ride", cascade="all, delete-orphan")
    segments = relationship("SegmentORM", back_populates="ride", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("external_id", name="uq_ride_external_id"),
        Index("idx_ride_created_at", "created_at"),
        Index("idx_ride_sport_type", "sport_type"),
    )


class GPSPointORM(Base):
    __tablename__ = "gps_points"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    point_index = Column(Integer, nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)

    speed = Column(Float, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    cadence = Column(Integer, nullable=True)
    power = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)

    ride = relationship("RideORM", back_populates="gps_points")

    __table_args__ = (
        UniqueConstraint("ride_id", "point_index", name="uq_gps_ride_index"),
        Index("idx_gps_ride", "ride_id", "point_index"),
    )


class SegmentORM(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    segment_type = Column(String(50), nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    label = Column(String(255), nullable=True)
    avg_speed = Column(Float, nullable=True)
    avg_hr = Column(Integer, nullable=True)

    ride = relationship("RideORM", back_populates="segments")

    __table_args__ = (
        UniqueConstraint("ride_id", "start_index", "end_index", name="uq_segment_range"),
        Index("idx_segment_ride", "ride_id"),
    )
