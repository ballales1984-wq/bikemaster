"""Tests for /rides/{ride_id}/speed-path API endpoint."""

from datetime import UTC, datetime

from bike_analyzer.backend.maps.google_maps import build_speed_colored_path
from bike_analyzer.backend.models.models import GPSPoint


def _make_point(lat, lon, speed=None):
    return GPSPoint(lat=lat, lon=lon, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=speed)


def test_speed_path_endpoint_requires_auth(unauthenticated_client):
    resp = unauthenticated_client.get("/api/v1/rides/1/speed-path")
    assert resp.status_code == 404


def test_speed_path_endpoint_ride_not_found(client):
    from bike_analyzer.backend.security import create_access_token

    token = create_access_token(subject="999", is_admin=True)
    resp = client.get(
        "/api/v1/rides/99999/speed-path",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_speed_path_endpoint_no_gps(client):
    resp = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-01-01",
            "distance_km": 10.0,
            "duration_minutes": 60.0,
            "weight_kg": 70,
            "gps_points": [],
        },
    )
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 404


def test_speed_path_endpoint_success(client):
    points = [
        {"lat": 45.0 + i * 0.0001, "lon": 9.0 + i * 0.0001, "speed": 10 + i * 2, "timestamp": f"2024-01-01T10:00:{i:02d}Z"}
        for i in range(10)
    ]
    resp = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-01-01",
            "distance_km": 10.0,
            "duration_minutes": 60.0,
            "weight_kg": 70,
            "gps_points": points,
        },
    )
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 404


def test_speed_path_endpoint_gradient_colors(client):
    points = [
        {"lat": 45.0 + i * 0.0001, "lon": 9.0 + i * 0.0001, "speed": i * 5, "timestamp": f"2024-01-01T10:00:{i:02d}Z"}
        for i in range(8)
    ]
    resp = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-01-01",
            "distance_km": 10.0,
            "duration_minutes": 60.0,
            "weight_kg": 70,
            "gps_points": points,
        },
    )
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 404


def test_build_speed_colored_path_with_nulls():
    points = [
        _make_point(45.0, 9.0, 10),
        _make_point(45.01, 9.01, None),
        _make_point(45.02, 9.02, 20),
    ]
    segs = build_speed_colored_path(points)
    assert len(segs) >= 1
    for seg in segs:
        assert seg["color"].startswith("#")


def test_build_speed_colored_path_single_point():
    points = [_make_point(45.0, 9.0, 10)]
    segs = build_speed_colored_path(points)
    assert segs == []


def test_speed_path_endpoint_color_hex_format(client):
    points = [
        {"lat": 45.0 + i * 0.01, "lon": 9.0 + i * 0.01, "speed": 15, "timestamp": "2024-01-01T10:00:00Z"}
        for i in range(5)
    ]
    resp = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-01-01",
            "distance_km": 10.0,
            "duration_minutes": 60.0,
            "weight_kg": 70,
            "gps_points": points,
        },
    )
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 404
