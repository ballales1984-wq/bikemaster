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
    """ORM model for a ride"""
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(5000))
    sport_type = Column(String(50), nullable=False, default="cycling")
    source = Column(String(100))
    external_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    total_distance_km = Column(Float, default=0.0)
    total_duration_seconds = Column(Float, default=0.0)
    avg_speed_kmh = Column(Float, default=0.0)
    max_speed_kmh = Column(Float, default=0.0)
    point_count = Column(Integer, default=0)

    gps_points = relationship(
        "GPSPointORM", back_populates="ride", cascade="all, delete-orphan"
    )
    segments = relationship(
        "SegmentORM", back_populates="ride", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("external_id", name="uq_ride_external_id"),
        Index("idx_ride_created_at", "created_at"),
        Index("idx_ride_sport_type", "sport_type"),
    )


class GPSPointORM(Base):
    """ORM model for a single GPS reading"""
    __tablename__ = "gps_points"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    point_index = Column(Integer, nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float)
    timestamp = Column(DateTime, nullable=False)

    speed = Column(Float)  # m/s
    heart_rate = Column(Integer)  # bpm
    cadence = Column(Integer)  # rpm
    power = Column(Integer)  # watts
    temperature = Column(Float)  # celsius

    ride = relationship("RideORM", back_populates="gps_points")

    __table_args__ = (
        Index("idx_gps_ride", "ride_id", "point_index"),
        UniqueConstraint("ride_id", "point_index", name="uq_gps_ride_index"),
    )


class SegmentORM(Base):
    """ORM model for a sub-segment of a ride"""
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    segment_type = Column(String(50), nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    label = Column(String(255))
    avg_speed = Column(Float)
    avg_hr = Column(Integer)

    ride = relationship("RideORM", back_populates="segments")

    __table_args__ = (
        Index("idx_segment_ride", "ride_id"),
        UniqueConstraint("ride_id", "start_index", "end_index", name="uq_segment_range"),
    )
