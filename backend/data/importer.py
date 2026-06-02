"""Importer factory and Google Fit API integration stub"""

import json
from pathlib import Path
from typing import Optional

from .base_importer import BaseImporter, RawRide
from .fit_importer import FITImporter
from .gpx_importer import GPXImporter


IMPORTERS = [
    GPXImporter(),
    FITImporter(),
]


def detect_importer(file_path: str) -> BaseImporter:
    for importer in IMPORTERS:
        if importer.can_handle(file_path):
            return importer
    raise ValueError(f"No importer found for file: {file_path}")


def import_from_file(file_path: str, sport_type: str = "cycling", name: Optional[str] = None) -> RawRide:
    importer = detect_importer(file_path)
    raw_ride = importer.import_file(file_path, sport_type)
    if name:
        raw_ride.name = name
    return raw_ride


def import_from_json(file_path: str) -> RawRide:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for p in data.get("points", []):
        from datetime import datetime
        points.append(RawPoint(
            latitude=p["lat"],
            longitude=p["lon"],
            elevation=p.get("elevation"),
            timestamp=datetime.fromisoformat(p["ts"]) if isinstance(p["ts"], str) else p["ts"],
            speed=p.get("speed"),
            heart_rate=p.get("hr"),
            cadence=p.get("cad"),
            power=p.get("power"),
        ))

    return RawRide(
        name=data.get("name", "Imported from JSON"),
        sport_type=data.get("sport_type", "cycling"),
        source="json_file",
        external_id=str(data.get("id")),
        points=points,
    )


class GoogleFitConnector:
    """Stub for Google Fit API connection (requires OAuth2)"""

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path

    def list_activities(self, start_date: str, end_date: str) -> list[dict]:
        raise NotImplementedError(
            "Google Fit integration requires OAuth2 setup. "
            "See backend/data/google_fit_connector.py for implementation details."
        )

    def fetch_ride(self, activity_id: str) -> RawRide:
        raise NotImplementedError(
            "Google Fit ride fetching requires OAuth2 setup. "
            "See backend/data/google_fit_connector.py for implementation details."
        )
