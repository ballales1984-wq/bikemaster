"""Test batch import functionality."""

from io import BytesIO

import pytest

from bike_analyzer.backend.db.database import init_db
from bike_analyzer.backend.ingestion.gps_parser import parse_gpx_file, points_to_ride


def test_batch_import_multiple_gpx():
    init_db()
    gpx_content = """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="45.0" lon="9.0"><ele>100</ele><time>2024-01-01T10:00:00Z</time></trkpt>
    <trkpt lat="45.01" lon="9.01"><ele>110</ele><time>2024-01-01T10:01:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""
    points = parse_gpx_file(gpx_content)
    assert len(points) == 2
    ride_data = points_to_ride(points, name="test.gpx")
    assert "error" not in ride_data
    assert ride_data["distance_km"] > 0


def test_batch_import_empty_points():
    ride_data = points_to_ride([], name="empty.gpx")
    assert "error" in ride_data


def test_batch_import_invalid_extension():
    from datetime import datetime

    from bike_analyzer.backend.ingestion.gps_parser import points_to_ride

    ts = datetime(2024, 1, 1, 10, 0, 0)
    ride_data = points_to_ride([{"lat": 45.0, "lon": 9.0, "ele": 100, "timestamp": ts}], name="file.xyz")
    assert "error" not in ride_data


def test_batch_import_bad_gpx_content():
    import xml.etree.ElementTree as ET

    with pytest.raises(ET.ParseError):
        parse_gpx_file("<not valid xml")


def test_batch_import_empty_filename():
    from bike_analyzer.backend.ingestion.gps_parser import (
        parse_gpx_file,
        points_to_ride,
    )

    gpx_content = """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="45.0" lon="9.0"><ele>100</ele><time>2024-01-01T10:00:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""
    points = parse_gpx_file(gpx_content)
    ride_data = points_to_ride(points, name=None)
    assert "error" not in ride_data


def test_batch_import_gpx_points_preserve_sensor_fields():
    from datetime import datetime

    points = [
        {
            "lat": 45.0,
            "lon": 9.0,
            "timestamp": datetime(2024, 1, 1, 10, 0, 0),
            "altitude": 100.0,
            "speed": 20.0,
            "power": 180.0,
            "heart_rate": 140,
            "cadence": 80,
        },
        {
            "lat": 45.01,
            "lon": 9.01,
            "timestamp": datetime(2024, 1, 1, 10, 1, 0),
            "altitude": 110.0,
            "speed": 22.0,
            "power": 200.0,
            "heart_rate": 145,
            "cadence": 85,
        },
    ]
    ride_data = points_to_ride(points, name="sensors.gpx")
    assert "error" not in ride_data
    assert ride_data["gps_points"][0]["power"] == 180.0
    assert ride_data["gps_points"][0]["heart_rate"] == 140
    assert ride_data["gps_points"][0]["cadence"] == 80


def test_import_gpx_endpoint(client):
    gpx_content = """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
<trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>
<trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("test.gpx", BytesIO(gpx_content.encode()), "application/gpx+xml")}
    response = client.post("/api/v1/import/gpx", files=files)
    assert response.status_code == 200
    assert response.json()["date"] == "2024-06-15"


def test_import_fit_endpoint_invalid(client):
    files = {"file": ("test.fit", BytesIO(b"invalid"), "application/octet-stream")}
    response = client.post("/api/v1/import/fit", files=files)
    assert response.status_code == 400
