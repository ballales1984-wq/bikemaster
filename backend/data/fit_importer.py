"""FIT (Flexible and Interoperable Data Transfer) importer using fitparse"""

from datetime import datetime
from typing import Optional

from fitparse import FitFile
from .base_importer import BaseImporter, RawPoint, RawRide


class FITImporter(BaseImporter):
    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".fit")

    def import_file(self, file_path: str, sport_type: str = "cycling") -> RawRide:
        fit_file = FitFile(file_path)
        records = list(fit_file.get_messages("record"))

        if not records:
            raise ValueError("No record messages found in FIT file")

        name = "Untitled Ride"
        for msg in fit_file.get_messages("file_id"):
            if msg.get_value("product_name"):
                name = str(msg.get_value("product_name"))
                break

        for msg in fit_file.get_messages("event"):
            if msg.get_value("event") == "timer" and msg.get_value("event_type") == "start":
                break

        points: list[RawPoint] = []
        for record in records:
            lat = record.get_value("position_lat")
            lon = record.get_value("position_long")
            speed = record.get_value("speed")
            hr = record.get_value("heart_rate")
            cad = record.get_value("cadence")
            power = record.get_value("power")
            temp = record.get_value("temperature")

            if lat is not None and lon is not None:
                lat_deg = lat / (2**31) * 180
                lon_deg = lon / (2**31) * 180

                ts_raw = record.get_value("timestamp")
                timestamp = ts_raw if isinstance(ts_raw, datetime) else datetime.utcnow()

                elevation_raw = record.get_value("enhanced_altitude") or record.get_value("altitude")

                points.append(RawPoint(
                    latitude=lat_deg,
                    longitude=lon_deg,
                    elevation=elevation_raw,
                    timestamp=timestamp,
                    speed=speed,
                    heart_rate=hr,
                    cadence=cadence,
                    power=power,
                    temperature=temp,
                ))

        if not points:
            raise ValueError("No valid GPS positions found in FIT file")

        return RawRide(
            name=name,
            sport_type=sport_type,
            source="fit_file",
            external_id=None,
            points=points,
        )
