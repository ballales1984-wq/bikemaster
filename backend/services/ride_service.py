"""Ride service - business logic for ride operations"""

from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from backend.core.analytics_engine import AnalyticsEngine
from backend.data.importer import import_from_file, import_from_json
from backend.data.base_importer import RawRide
from backend.db.session import get_database
from backend.gps.processor import GPSProcessor
from backend.models.orm import GPSPointORM, RideORM, SegmentORM
from backend.models.schemas import (
    AnalyticsData,
    FileImportRequest,
    RideCreate,
    RideUpdate,
    SegmentBase,
    GPSPointCreate,
)


DEFAULT_DB_URL = "sqlite:///./bike_analyzer.db"


class RideService:
    def __init__(self, db_url: str = DEFAULT_DB_URL, db_echo: bool = False):
        self.db_url = db_url
        self.db_echo = db_echo
        self.db = get_database(db_url, db_echo)
        self.processor = GPSProcessor()
        self.analytics = AnalyticsEngine()

    def get_db(self) -> Session:
        return self.db.get_session()

    # ── RIDES ─────────────────────────────────────────
    def create_ride(self, ride_in: RideCreate) -> RideORM:
        with self.get_db() as session:
            ride = RideORM(
                name=ride_in.name,
                description=ride_in.description,
                sport_type=ride_in.sport_type.value,
                source="api",
                external_id=None,
            )
            session.add(ride)
            session.commit()
            session.refresh(ride)
            self._save_points(session, ride.id, ride_in.gps_points)
            session.refresh(ride)
            return self._to_response(ride)

    def get_ride(self, ride_id: int) -> Optional[RideORM]:
        with self.get_db() as session:
            return session.query(RideORM).filter(RideORM.id == ride_id).first()

    def list_rides(self, page: int = 1, page_size: int = 20,
                   sport_type: Optional[str] = None) -> tuple[list[RideORM], int]:
        with self.get_db() as session:
            q = session.query(RideORM)
            if sport_type:
                q = q.filter(RideORM.sport_type == sport_type)
            total = q.count()
            rides = q.order_by(RideORM.created_at.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
            return rides, total

    def update_ride(self, ride_id: int, ride_in: RideUpdate) -> Optional[RideORM]:
        with self.get_db() as session:
            ride = session.query(RideORM).filter(RideORM.id == ride_id).first()
            if not ride:
                return None
            if ride_in.name is not None:
                ride.name = ride_in.name
            if ride_in.description is not None:
                ride.description = ride_in.description
            if ride_in.sport_type is not None:
                ride.sport_type = ride_in.sport_type.value
            session.commit()
            session.refresh(ride)
            return ride

    def delete_ride(self, ride_id: int) -> bool:
        with self.get_db() as session:
            ride = session.query(RideORM).filter(RideORM.id == ride_id).first()
            if not ride:
                return False
            session.delete(ride)
            session.commit()
            return True

    # ── IMPORT ────────────────────────────────────────
    def import_ride(self, request: FileImportRequest) -> RideORM:
        if request.format.value in ("json", "csv"):
            from backend.data.importer import import_from_json
            raw = import_from_json(request.format.value)
        else:
            raw = import_from_file(
                str(request.format.value),
                request.sport_type.value,
                name=request.name,
            )

        return self._create_from_raw(raw)

    # ── ANALYTICS ────────────────────────────────────
    def compute_analytics(self, ride_id: int) -> Optional[AnalyticsData]:
        ride = self.get_ride(ride_id)
        if not ride:
            return None

        points = sorted(ride.gps_points, key=lambda p: p.point_index)
        if len(points) < 2:
            return AnalyticsData(
                ride_id=ride_id,
                total_distance_km=0.0,
                total_duration_seconds=0.0,
                avg_speed_kmh=0.0,
                max_speed_kmh=0.0,
                elevation_gain_m=0.0,
                elevation_loss_m=0.0,
            )

        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        timestamps = [p.timestamp for p in points]
        elevations = [p.elevation for p in points]

        heart_rates = [p.heart_rate for p in points if p.heart_rate is not None]
        cadences = [p.cadence for p in points if p.cadence is not None]
        powers = [p.power for p in points if p.power is not None]

        result = self.processor.process(lats, lons, elevations, timestamps)
        analytics = self.analytics.compute_all(result, heart_rates, cadences, powers)
        return AnalyticsData(ride_id=ride_id, **analytics)

    def compare_rides(self, ride_ids: list[int]) -> dict:
        results = []
        for rid in ride_ids:
            a = self.compute_analytics(rid)
            if a:
                results.append(a)

        if not results:
            return {}

        keys = [
            "total_distance_km", "total_duration_seconds",
            "avg_speed_kmh", "max_speed_kmh",
            "elevation_gain_m", "energy_kcal",
        ]
        comparison = {}
        for key in keys:
            vals = [getattr(r, key) for r in results if getattr(r, key) is not None]
            if vals:
                comparison[key] = {
                    "min": round(min(vals), 2),
                    "max": round(max(vals), 2),
                    "avg": round(np.mean(vals), 2),
                }
        return {
            "ride_ids": ride_ids,
            "rides": [r.dict() for r in results],
            "comparison": comparison,
        }

    # ── INTERNAL ──────────────────────────────────────
    def _save_points(self, session: Session, ride_id: int, points: list[GPSPointCreate]):
        for i, p in enumerate(points):
            session.add(GPSPointORM(
                ride_id=ride_id,
                point_index=i,
                latitude=p.latitude,
                longitude=p.longitude,
                elevation=p.elevation,
                timestamp=p.timestamp,
                speed=p.speed,
                heart_rate=p.heart_rate,
                cadence=p.cadence,
                power=p.power,
                temperature=p.temperature,
            ))

    def _create_from_raw(self, raw: RawRide) -> RideORM:
        with self.get_db() as session:
            ride = RideORM(
                name=raw.name,
                sport_type=raw.sport_type,
                source=raw.source,
                external_id=raw.external_id,
            )
            session.add(ride)
            session.commit()
            session.refresh(ride)

            lats = [p.latitude for p in raw.points]
            lons = [p.longitude for p in raw.points]
            elevations = [p.elevation for p in raw.points]
            timestamps = [p.timestamp for p in raw.points]

            result = self.processor.process(lats, lons, elevations, timestamps)

            ride.point_count = result["points_kept"]
            ride.total_distance_km = result["total_distance_m"] / 1000
            ride.total_duration_seconds = result["duration_seconds"]
            ride.avg_speed_kmh = result["avg_speed_kmh"]
            ride.max_speed_kmh = result["max_speed_kmh"]

            session.merge(ride)
            session.commit()
            session.refresh(ride)

            ride_id = ride.id

        return ride

    def _to_response(self, ride: RideORM) -> RideORM:
        return ride  # we'll let the API layer do dict conversion
