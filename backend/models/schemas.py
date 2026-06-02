from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SportType(str, Enum):
    CYCLING = "cycling"
    RUNNING = "running"
    HIKING = "hiking"
    OTHER = "other"


class FileFormat(str, Enum):
    GPX = "gpx"
    FIT = "fit"
    TCX = "tcx"
    JSON = "json"
    CSV = "csv"


class GPSPointBase(BaseModel):
    """Single GPS point with all available data"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation: Optional[float] = None
    timestamp: datetime
    speed: Optional[float] = None  # m/s
    heart_rate: Optional[int] = None
    cadence: Optional[int] = None
    power: Optional[int] = None  # watts
    temperature: Optional[float] = None


class GPSPointCreate(GPSPointBase):
    pass


class GPSPointResponse(GPSPointBase):
    point_index: int

    class Config:
        from_attributes = True


class SegmentBase(BaseModel):
    """Sub-segment of a ride (e.g., between rest stops or speed zones)"""
    segment_type: str  # "full_ride", "lap", "manual", "speed_zone"
    start_index: int
    end_index: int
    label: Optional[str] = None
    avg_speed: Optional[float] = None
    avg_hr: Optional[int] = None


class SegmentResponse(SegmentBase):
    id: int
    ride_id: int

    class Config:
        from_attributes = True


class RideBase(BaseModel):
    name: str
    description: Optional[str] = None
    sport_type: SportType = SportType.CYCLING
    source: Optional[str] = None
    external_id: Optional[str] = None


class RideCreate(RideBase):
    gps_points: list[GPSPointCreate]


class RideUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sport_type: Optional[SportType] = None


class AnalyticsData(BaseModel):
    """Computed analytics for a ride"""
    ride_id: int
    total_distance_km: float
    total_duration_seconds: float
    avg_speed_kmh: float
    max_speed_kmh: float
    min_elevation_m: Optional[float] = None
    max_elevation_m: Optional[float] = None
    elevation_gain_m: float
    elevation_loss_m: float
    avg_heart_rate: Optional[float] = None
    max_heart_rate: Optional[int] = None
    avg_cadence: Optional[float] = None
    energy_kcal: Optional[float] = None
    avg_power: Optional[float] = None


class RideResponse(RideBase):
    id: int
    created_at: datetime
    total_distance_km: float
    total_duration_seconds: float
    avg_speed_kmh: float
    max_speed_kmh: float
    point_count: int
    analytics: Optional[AnalyticsData] = None

    class Config:
        from_attributes = True


class RideListResponse(BaseModel):
    rides: list[RideResponse]
    total: int
    page: int
    page_size: int


class FileImportRequest(BaseModel):
    format: FileFormat
    sport_type: SportType = SportType.CYCLING
    name: Optional[str] = None


class ComparisonRequest(BaseModel):
    ride_ids: list[int] = Field(..., min_length=2, max_length=5)


class ComparisonResponse(BaseModel):
    rides: list[RideResponse]
    comparison_summary: dict
