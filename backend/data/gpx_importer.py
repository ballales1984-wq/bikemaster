"""GPX file importer"""

import gpxpy
import gpxpy.gpx
from datetime import datetime
from typing import Optional

from .base_importer import BaseImporter, RawPoint, RawRide


class GPXImporter(BaseImporter):
    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".gpx")

    def import_file(self, file_path: str, sport_type: str = "cycling") -> RawRide:
        with open(file_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        name = "Untitled Ride"
        for track in gpx.tracks:
            if track.name:
                name = track.name
                break

        points: list[RawPoint] = []
        hr_from_ext = self._extract_hr_from_extensions(gpx)

        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    hr = hr_from_ext.get(id(pt))
                    points.append(RawPoint(
                        latitude=pt.latitude,
                        longitude=pt.longitude,
                        elevation=pt.elevation,
                        timestamp=pt.time or datetime.utcnow(),
                        speed=getattr(pt, "speed", None),
                        heart_rate=hr,
                    ))

        if not points:
            raise ValueError("No GPS points found in GPX file")

        return RawRide(
            name=name,
            sport_type=sport_type,
            source="gpx_file",
            external_id=None,
            points=points,
        )

    def _extract_hr_from_extensions(self, gpx):
        hr_map = {}
        try:
            for track in gpx.tracks:
                for segment in track.segments:
                    for pt in segment.points:
                        for ext in pt.extensions:
                            hr = ext.find(".//{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr")
                            if hr is not None and hr.text:
                                hr_map[id(pt)] = int(hr.text)
        except Exception:
            pass
        return hr_map
