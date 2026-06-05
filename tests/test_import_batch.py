"""Test batch import functionality."""
import tempfile
import os

from bike_analyzer.backend.db.database import init_db
from bike_analyzer.backend.ingestion.gps_parser import parse_gpx_file, points_to_ride


def test_batch_import_multiple_gpx():
    init_db()
    gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="45.0" lon="9.0"><ele>100</ele><time>2024-01-01T10:00:00Z</time></trkpt>
    <trkpt lat="45.01" lon="9.01"><ele>110</ele><time>2024-01-01T10:01:00Z</time></trkpt>
  </trkseg></trk>
</gpx>'''
    points = parse_gpx_file(gpx_content)
    assert len(points) == 2
    ride_data = points_to_ride(points, name="test.gpx")
    assert "error" not in ride_data
    assert ride_data["distance_km"] > 0


def test_batch_import_empty_points():
    ride_data = points_to_ride([], name="empty.gpx")
    assert "error" in ride_data