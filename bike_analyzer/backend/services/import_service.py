"""Import service for GPS files (FIT, GPX, TCX).

Orchestrates parsing, normalization, and persistence for file-based activity imports.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
from bike_analyzer.backend.ingestion.gps_parser import (
    get_fit_external_id,
    parse_fit_file,
    parse_gpx_file,
    parse_tcx_file,
    points_to_ride,
)

logger = logging.getLogger(__name__)


class ImportService:
    @staticmethod
    def import_file(
        file_type: str,
        *,
        file_path: str | None = None,
        content: str | None = None,
        name: str | None = None,
        athlete_id: int = 0,
        tenant_id: int = 0,
        weight_kg: float = 70.0,
    ) -> dict:
        """Import a GPS activity file (GPX, TCX, or FIT) into the database.

        Parses the file, normalizes it into a ride dict, enriches calories when
        missing, and persists via RideRepository.

        Args:
            file_type: One of ``"gpx"``, ``"tcx"``, or ``"fit"``.
            file_path: Path to the file on disk. Required for FIT; optional for
                GPX/TCX if ``content`` is provided instead.
            content: Raw XML/bytes string of the file. Used for GPX/TCX when
                ``file_path`` is not available.
            name: Optional ride name override.
            athlete_id: Athlete identifier to associate with the ride.
            tenant_id: Tenant identifier for multi-tenant isolation.
            weight_kg: Rider weight in kilograms used for calorie estimation.

        Returns:
            A dict representing the saved ride, including the generated ``id``.

        Raises:
            ValueError: If ``file_type`` is unsupported or FIT import is missing
                ``file_path``.
        """
        if file_type == "gpx":
            if content is None and file_path:
                content = Path(file_path).read_text(encoding="utf-8")
            points = parse_gpx_file(content or "")
        elif file_type == "tcx":
            if content is None and file_path:
                content = Path(file_path).read_text(encoding="utf-8")
            points = parse_tcx_file(content or "")
        elif file_type == "fit":
            if file_path is None:
                raise ValueError("FIT import requires file_path")
            points = parse_fit_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        ride_data = points_to_ride(points, name=name, weight_kg=weight_kg)
        if "error" in ride_data:
            return ride_data

        ride_data["athlete_id"] = athlete_id
        ride_data["tenant_id"] = tenant_id
        ride_data["source"] = "imported"

        if file_type == "fit" and file_path:
            ride_data["external_source"] = "fit"
            ride_data["external_id"] = get_fit_external_id(file_path)

        db_ride = {k: v for k, v in ride_data.items() if k != "id"}
        if not db_ride.get("calories"):
            try:
                from bike_analyzer.backend.analytics.calories import ensure_calories
                from bike_analyzer.backend.models.models import Ride

                allowed = set(Ride.__dataclass_fields__.keys())
                clean = {k: v for k, v in db_ride.items() if k in allowed and k not in ("gps_points", "id")}
                db_ride["calories"] = ensure_calories(Ride(**clean))
            except Exception:
                db_ride["calories"] = 0
        ride_id = RideRepository.save_ride(db_ride)
        ride_data["id"] = int(ride_id)
        return ride_data
