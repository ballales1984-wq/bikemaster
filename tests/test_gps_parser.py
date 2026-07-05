"""Tests for GPS parser module."""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import pytest

from bike_analyzer.backend.ingestion.gps_parser import parse_gpx_file, points_to_ride

SAMPLE_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="45.0" lon="9.0">
        <ele>100.0</ele>
        <time>2024-06-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="45.01" lon="9.01">
        <ele>150.0</ele>
        <time>2024-06-15T08:10:00Z</time>
      </trkpt>
      <trkpt lat="45.02" lon="9.02">
        <ele>200.0</ele>
        <time>2024-06-15T08:20:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""


class TestParseGpxFile:
    def test_parse_valid_gpx(self):
        points = parse_gpx_file(SAMPLE_GPX)
        assert len(points) == 3
        assert points[0]["lat"] == 45.0
        assert points[0]["lon"] == 9.0
        assert points[0]["altitude"] == 100.0

    def test_parse_timestamps(self):
        points = parse_gpx_file(SAMPLE_GPX)
        assert points[0]["timestamp"] == datetime(2024, 6, 15, 8, 0, 0, tzinfo=UTC)
        assert points[1]["timestamp"] == datetime(2024, 6, 15, 8, 10, 0, tzinfo=UTC)

    def test_parse_missing_altitude(self):
        gpx = SAMPLE_GPX.replace("<ele>100.0</ele>", "")
        points = parse_gpx_file(gpx)
        assert points[0]["altitude"] is None

    def test_parse_missing_time(self):
        gpx = SAMPLE_GPX.replace("<time>2024-06-15T08:00:00Z</time>", "")
        points = parse_gpx_file(gpx)
        assert len(points) == 2

    def test_parse_empty_gpx(self):
        gpx = '<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1"></gpx>'
        points = parse_gpx_file(gpx)
        assert points == []

    def test_parse_invalid_xml_raises(self):
        with pytest.raises(ET.ParseError):
            parse_gpx_file("not valid xml")

    def test_parse_invalid_lat_skips_point(self):
        gpx = SAMPLE_GPX.replace('lat="45.0"', 'lat="not_a_number"')
        result = parse_gpx_file(gpx)
        assert len(result) == 2
        for p in result:
            assert isinstance(p["lat"], float)


class TestPointsToRide:
    def test_empty_points(self):
        result = points_to_ride([])
        assert "error" in result

    def test_single_point(self):
        points = [{"lat": 45.0, "lon": 9.0, "timestamp": datetime(2024, 6, 15, 8, 0, 0, tzinfo=UTC)}]
        result = points_to_ride(points)
        assert result["date"] == "2024-06-15"
        assert result["distance_km"] == 0
        assert result["duration_minutes"] == 0

    def test_multiple_points(self):
        points = [
            {"lat": 45.0, "lon": 9.0, "timestamp": datetime(2024, 6, 15, 8, 0, 0, tzinfo=UTC)},
            {"lat": 45.01, "lon": 9.01, "timestamp": datetime(2024, 6, 15, 8, 10, 0, tzinfo=UTC)},
        ]
        result = points_to_ride(points)
        assert result["distance_km"] > 0
        assert result["duration_minutes"] > 0

    def test_gps_points_included(self):
        points = [
            {"lat": 45.0, "lon": 9.0, "timestamp": datetime(2024, 6, 15, 8, 0, 0, tzinfo=UTC)},
            {"lat": 45.01, "lon": 9.01, "timestamp": datetime(2024, 6, 15, 8, 10, 0, tzinfo=UTC)},
        ]
        result = points_to_ride(points)
        assert "gps_points" in result
        assert len(result["gps_points"]) == 2

    def test_custom_weight(self):
        points = [
            {"lat": 45.0, "lon": 9.0, "timestamp": datetime(2024, 6, 15, 8, 0, 0, tzinfo=UTC)},
            {"lat": 45.01, "lon": 9.01, "timestamp": datetime(2024, 6, 15, 8, 10, 0, tzinfo=UTC)},
        ]
        result = points_to_ride(points, weight_kg=75.0)
        assert result["weight_kg"] == 75.0
