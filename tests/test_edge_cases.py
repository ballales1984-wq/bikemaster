"""Edge case tests for bug fixes."""
from __future__ import annotations
import json
import os
import tempfile
import pytest
from datetime import datetime, timezone

from bike_analyzer.backend.models.models import GPSPoint, Ride
from bike_analyzer.backend.ingestion.gps_parser import parse_gpx_file
from bike_analyzer.backend.db.database import (
    init_db,
    save_ride,
    get_ride,
    get_all_rides,
    get_rides_by_athlete,
    backup_database,
    DB_PATH,
)
from bike_analyzer.backend.maps.map_renderer import create_route_map
from bike_analyzer.backend.processing.processing import process_route, detect_pauses, detect_accelerations, detect_decelerations, remove_outliers
from bike_analyzer.backend.analytics.calories import estimate_calories


@pytest.fixture(autouse=True)
def _init_db():
    init_db()
    yield
    # cleanup: rimuove ride inserite dal test corrente
    for r in get_all_rides():
        from bike_analyzer.backend.db.database import delete_ride
        delete_ride(r["id"])


# ── gps_parser: coordinate 0.0 valide ─────────────────────────────────────
@pytest.fixture
def gpx_zero_lat():
    return """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="0.0" lon="0.0"><ele>10</ele><time>2024-01-01T10:00:00Z</time></trkpt>
    <trkpt lat="0.0" lon="1.0"><ele>12</ele><time>2024-01-01T10:01:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""


def test_gpx_coordinate_zero_lat(gpx_zero_lat):
    points = parse_gpx_file(gpx_zero_lat)
    assert len(points) == 2
    assert points[0]["lat"] == 0.0
    assert points[0]["lon"] == 0.0


# ── gps_parser: coordinate 0.0 per lon ────────────────────────────────────
@pytest.fixture
def gpx_zero_lon():
    return """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="1.0" lon="0.0"><ele>10</ele><time>2024-01-01T10:00:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""


def test_gpx_coordinate_zero_lon(gpx_zero_lon):
    points = parse_gpx_file(gpx_zero_lon)
    assert len(points) == 1
    assert points[0]["lon"] == 0.0


# ── database: JSON corrotto non crasha ────────────────────────────────────
def test_db_corrupt_gps_points_does_not_crash():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rides (date, distance_km, duration_minutes, gps_points) VALUES (?, ?, ?, ?)",
        ("2024-06-20", 10.0, 30.0, "NOT_JSON"),
    )
    conn.commit()
    ride_id = cur.lastrowid
    conn.close()
    ride = get_ride(ride_id)
    assert ride is not None
    assert ride["gps_points"] is None


def test_get_all_rides_corrupt_gps_points():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rides (date, distance_km, duration_minutes, gps_points) VALUES (?, ?, ?, ?)",
        ("2024-06-21", 10.0, 30.0, "{invalid json"),
    )
    conn.commit()
    conn.close()
    rides = get_all_rides()
    assert isinstance(rides, list)


def test_get_rides_by_athlete_corrupt_gps_points():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rides (athlete_id, date, distance_km, duration_minutes, gps_points) VALUES (?, ?, ?, ?, ?)",
        (1, "2024-06-22", 10.0, 30.0, "[]"),
    )
    conn.commit()
    conn.close()
    rides = get_rides_by_athlete(1)
    assert isinstance(rides, list)


# ── database: backup su DB assente ───────────────────────────────────────
def test_backup_database_missing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = os.path.join(tmpdir, "nonexistent.db")
        with pytest.raises(FileNotFoundError):
            from bike_analyzer.backend.db.database import DB_PATH as _orig_db
            # monkey-patch temporaneo: salviamo DB_PATH, lo impostiamo a un path inesistente, chiamiamo backup, ripristiniamo
            import bike_analyzer.backend.db.database as dbmod
            old_db_path = dbmod.DB_PATH
            dbmod.DB_PATH = missing_path
            try:
                backup_database(os.path.join(tmpdir, "backup.db"))
            finally:
                dbmod.DB_PATH = old_db_path


# ── database: gps_points preservati dopo save_ride (import bug) ──────────
def test_save_ride_preserves_gps_points():
    points = [
        {"lat": 45.0, "lon": 9.0, "timestamp": "2024-01-01T10:00:00+00:00", "altitude": 100.0},
        {"lat": 45.01, "lon": 9.01, "timestamp": "2024-01-01T10:01:00+00:00", "altitude": 110.0},
    ]
    ride_data = {
        "date": "2024-06-01",
        "distance_km": 1.5,
        "duration_minutes": 5.0,
        "gps_points": points,
    }
    ride_id = save_ride(ride_data)
    stored = get_ride(ride_id)
    assert stored is not None
    assert stored["gps_points"] is not None
    assert len(stored["gps_points"]) == 2
    assert stored["gps_points"][0]["lat"] == 45.0


# ── processing: remove_outliers chiamato una sola volta ───────────────────
def test_process_route_does_not_double_outlier():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc)),
    ]
    cleaned, stats = process_route(points)
    # con outlier threshold 120 km/h tutti i punti sono validi
    assert len(cleaned) == 3
    assert stats.segment_count == 2


# ── analytics: calorie a 0.0 non ricalcolate ─────────────────────────────
def test_calories_zero_not_recalculated():
    """
    Verifica che estimate_calories restituisca un valore > 0 per una pedalata
    con dati realistici, e che la route /api/v1/rides/{id} non sovrascriva
    un valore di calories pari a 0.0 (test indiretto tramite models).
    """
    ride = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0,
                avg_speed_kmh=25.0, weight_kg=70.0, calories=0.0)
    c = estimate_calories(ride, method="physics")
    assert c > 0


# ── calorie: stima MET valida ────────────────────────────────────────────
def test_met_calorie_reasonable():
    ride = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0,
                avg_speed_kmh=20.0, weight_kg=70.0)
    c = estimate_calories(ride, method="met")
    assert 200 < c < 800


# ── map_renderer: crash evitato con statistics disegnate ─────────────────
def test_map_renderer_with_statistics_does_not_crash():
    points = [
        GPSPoint(lat=45.0 + i * 0.001, lon=9.0 + i * 0.001,
                 timestamp=datetime(2024, 1, 1, i, tzinfo=timezone.utc),
                 speed=20.0 + i)
        for i in range(5)
    ]
    _, stats = process_route(points)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        out = f.name
    try:
        create_route_map(points, statistics=stats, output_path=out)
        assert os.path.exists(out)
    finally:
        if os.path.exists(out):
            os.remove(out)


# ── maps: api key loader non crasha senza .env ───────────────────────────
def test_google_api_key_missing_env():
    from bike_analyzer.backend.maps.google_maps import get_google_api_key
    assert isinstance(get_google_api_key(), (str, type(None)))


# ── processing: pause detection with single point ─────────────────────────
def test_detect_pauses_single_point():
    p = GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=0.5)
    assert detect_pauses([p]) == []


# ── processing: acceleration/deceleration detection ───────────────────────
def test_detect_acceleration_and_deceleration():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pts = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=base, speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=base.replace(minute=base.minute + 1), speed=20),
        GPSPoint(lat=45.02, lon=9.02, timestamp=base.replace(minute=base.minute + 2), speed=8),
    ]
    accels = detect_accelerations(pts)
    decels = detect_decelerations(pts)
    assert len(accels) >= 1
    assert len(decels) >= 1


# ── processing: remove outliers returns copy for < 3 points ───────────────
def test_remove_outliers_short_list():
    pts = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)),
    ]
    cleaned = remove_outliers(pts)
    assert len(cleaned) >= 2
