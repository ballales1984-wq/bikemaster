"""Tests for /rides/{ride_id}/speed-path API endpoint."""

from datetime import UTC, datetime

from bike_analyzer.backend.maps.google_maps import build_speed_colored_path
from bike_analyzer.backend.models.models import GPSPoint


def _make_point(lat, lon, speed=None):
    return GPSPoint(lat=lat, lon=lon, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=speed)


def test_speed_path_endpoint_requires_auth(unauthenticated_client):
    resp = unauthenticated_client.get("/api/v1/rides/1/speed-path")
    assert resp.status_code == 401


def test_speed_path_endpoint_ride_not_found(client):
    from bike_analyzer.backend.security import create_access_token

    token = create_access_token(subject="999", is_admin=True)
    resp = client.get(
        "/api/v1/rides/99999/speed-path",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_speed_path_endpoint_no_gps(client):
    resp = client.post("/api/v1/rides", json={
        "date": "2024-01-01",
        "distance_km": 10.0,
        "duration_minutes": 60.0,
        "weight_kg": 70,
        "gps_points": [],
    })
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 400
    assert "No GPS points" in resp.json()["detail"]


def test_speed_path_endpoint_success(client):
    points = [
        {"lat": 45.0 + i * 0.01, "lon": 9.0 + i * 0.01, "speed": 10 + i * 2, "timestamp": "2024-01-01T10:00:00Z"}
        for i in range(10)
    ]
    resp = client.post("/api/v1/rides", json={
        "date": "2024-01-01",
        "distance_km": 10.0,
        "duration_minutes": 60.0,
        "weight_kg": 70,
        "gps_points": points,
    })
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ride_id"] == ride_id
    assert "segments" in data
    assert "min_speed" in data
    assert "max_speed" in data
    assert "center" in data
    assert data["point_count"] == 10
    assert len(data["segments"]) == 9
    for seg in data["segments"]:
        assert "start" in seg
        assert "end" in seg
        assert "color" in seg
        assert seg["color"].startswith("#")
        assert "speed_kmh" in seg


def test_speed_path_endpoint_gradient_colors(client):
    points = [
        {"lat": 45.0 + i * 0.01, "lon": 9.0 + i * 0.01, "speed": i * 5, "timestamp": "2024-01-01T10:00:00Z"}
        for i in range(8)
    ]
    resp = client.post("/api/v1/rides", json={
        "date": "2024-01-01",
        "distance_km": 10.0,
        "duration_minutes": 60.0,
        "weight_kg": 70,
        "gps_points": points,
    })
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_speed"] == 0
    assert data["max_speed"] == 35


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
    resp = client.post("/api/v1/rides", json={
        "date": "2024-01-01",
        "distance_km": 10.0,
        "duration_minutes": 60.0,
        "weight_kg": 70,
        "gps_points": points,
    })
    assert resp.status_code == 200
    ride_id = resp.json()["id"]
    resp = client.get(f"/api/v1/rides/{ride_id}/speed-path")
    assert resp.status_code == 200
    data = resp.json()
    for seg in data["segments"]:
        assert len(seg["color"]) == 7
        assert seg["color"][0] == "#"
