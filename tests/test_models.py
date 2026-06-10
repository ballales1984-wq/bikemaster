"""Test models."""
from datetime import datetime, timezone

from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.backend.processing.processing import (
    validate_coordinate,
    validate_gps_point,
)


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

def test_athlete_profile():
    a = AthleteProfile(name="Mario Rossi", age=35, weight_kg=75.0, experience_level="Intermediate")
    assert a.name == "Mario Rossi" and a.experience_level == "Intermediate"

def test_athlete_to_dict():
    a = AthleteProfile(name="Test", age=30, weight_kg=70.0)
    assert a.to_dict()["name"] == "Test"

def test_validate_coordinate_valid():
    assert validate_coordinate(45.0, 9.0) == True
    assert validate_coordinate(-90, 180) == True
    assert validate_coordinate(90, -180) == True

def test_validate_coordinate_invalid():
    assert validate_coordinate(91, 9.0) == False
    assert validate_coordinate(-91, 9.0) == False
    assert validate_coordinate(45.0, 181) == False
    assert validate_coordinate(45.0, -181) == False
    assert validate_coordinate("a", 9.0) == False

def test_validate_gps_point():
    p = GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert validate_gps_point(p) == True
    p_invalid = GPSPoint(lat=91, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert validate_gps_point(p_invalid) == False
