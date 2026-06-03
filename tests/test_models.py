"""Test models."""
from datetime import datetime, timezone
from bike_analyzer.backend.models.models import Ride, GPSPoint

def test_ride_creation():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0, weight_kg=70.0)
    assert r.distance_km == 25.0 and r.duration_hours == 1.0

def test_ride_to_dict():
    r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0)
    assert r.to_dict()["date"] == "2024-06-01"

def test_gps_point_distance():
    p1 = GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
    p2 = GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc))
    d = p1.distance_to(p2)
    assert 0 < d < 2000