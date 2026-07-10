"""Test BikeMaster 2.0 - Data Agents."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pytest

from bike_analyzer.bm2.agents import (
    EnvironmentAgent,
    GarminAgent,
    GPSAgent,
    SensorAgent,
    StravaAgent,
)
from bike_analyzer.bm2.models import Activity, Athlete, WorldObject
from bike_analyzer.bm2.transformer import TransformerEngine
from bike_analyzer.bm2.units import q


def _transformer():
    return TransformerEngine()


def test_gps_agent_collect():
    t = _transformer()
    agent = GPSAgent(t)
    raw = [
        {"lat": 45.0, "lon": 9.0, "altitude": 200, "timestamp": "2026-07-10T08:00:00Z"},
        {"lat": 45.005, "lon": 9.005, "altitude": 360, "timestamp": "2026-07-10T09:00:00Z"},
    ]
    act = agent.collect(raw, title="Test")
    assert isinstance(act, Activity)
    assert len(act.points) == 2
    assert act.points[0].lat == 45.0
    assert act.title == "Test"


def test_gps_agent_from_gpx():
    t = _transformer()
    gpx = """<?xml version="1.0"?>
    <gpx xmlns="http://www.topografix.com/GPX/1/1">
      <trk>
        <name>GPX Test</name>
        <trkseg>
          <trkpt lat="45.0" lon="9.0">
            <ele>200</ele>
            <time>2026-07-10T08:00:00Z</time>
          </trkpt>
          <trkpt lat="45.005" lon="9.005">
            <ele>360</ele>
            <time>2026-07-10T09:00:00Z</time>
          </trkpt>
        </trkseg>
      </trk>
    </gpx>"""
    act = GPSAgent.from_gpx(t, gpx, title="GPX")
    assert isinstance(act, Activity)
    assert len(act.points) == 2
    assert act.points[1].altitude == 360.0
    assert act.title == "GPX"


def test_gps_agent_from_geojson():
    t = _transformer()
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [9.0, 45.0, 200]},
                "properties": {"timestamp": "2026-07-10T08:00:00Z"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [9.005, 45.005, 360]},
                "properties": {"timestamp": "2026-07-10T09:00:00Z"},
            },
        ],
    }
    act = GPSAgent.from_geojson(t, data, title="GeoJSON")
    assert isinstance(act, Activity)
    assert len(act.points) == 2
    assert act.points[0].lon == 9.0
    assert act.points[0].lat == 45.0
    assert act.points[1].altitude == 360.0


def test_strava_agent_activity_from_raw():
    t = _transformer()
    agent = StravaAgent(t)
    raw = {
        "name": "Strava Ride",
        "distance": 50000,
        "moving_time": 3600,
        "average_speed": 13.89,
        "total_elevation_gain": 500,
        "average_heartrate": 145,
        "gps_points": [
            {"lat": 45.0, "lon": 9.0, "altitude": 200, "timestamp": "2026-07-10T08:00:00Z"},
        ],
    }
    act = agent.activity_from_raw(raw)
    assert isinstance(act, Activity)
    assert act.title == "Strava Ride"
    assert len(act.points) == 1
    assert act.summary["distance_km"] == 50.0
    assert act.summary["avg_speed_kmh"] == pytest.approx(13.89 * 3.6)


def test_garmin_agent_activity_from_raw():
    t = _transformer()
    agent = GarminAgent(t)
    raw = {
        "activityName": "Garmin Ride",
        "activityType": "cycling",
        "distance": 40000,
        "duration": 2400,
        "averageSpeed": 15.0,
        "elevationGain": 300,
        "averageHR": 150,
        "gps_points": [
            {"lat": 45.0, "lon": 9.0, "altitude": 200, "timestamp": "2026-07-10T08:00:00Z"},
        ],
    }
    act = agent.activity_from_raw(raw)
    assert isinstance(act, Activity)
    assert act.title == "Garmin Ride"
    assert act.summary["distance_km"] == 40.0
    assert act.summary["duration_minutes"] == 40.0
    assert act.summary["avg_speed_kmh"] == pytest.approx(15.0 * 3.6)


def test_sensor_agent_enrich_irregular():
    t = _transformer()
    agent = SensorAgent(t)
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    act = Activity(points=pts)
    samples = [
        {"timestamp": "2026-07-10T07:59:00Z", "heart_rate": 140, "power": 180},
        {"timestamp": "2026-07-10T09:01:00Z", "heart_rate": 165, "power": 240},
    ]
    enriched = agent.enrich_points(act, samples, match_by_timestamp=True)
    assert enriched.points[0].heart_rate == 140
    assert enriched.points[1].heart_rate == 165


def test_sensor_summarize():
    t = _transformer()
    agent = SensorAgent(t)
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc),
                 heart_rate=140, power=180, cadence=80, speed=5.0),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc),
                 heart_rate=160, power=220, cadence=90, speed=6.0),
    ]
    act = Activity(points=pts)
    s = agent.summarize(act)
    assert s["heart_rate_avg_bpm"] == pytest.approx(150.0)
    assert s["heart_rate_max_bpm"] == 160
    assert s["power_avg_w"] == pytest.approx(200.0)
    assert s["cadence_avg_rpm"] == pytest.approx(85.0)
    assert s["speed_avg_ms"] == pytest.approx(5.5)
    assert s["samples_count"] == 2
