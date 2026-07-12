"""Tests for AetherMap backend integration."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from bike_analyzer.core.models import GPSPoint, RouteStatistics
from bike_analyzer.backend.maps import aethermap_adapter


FIXED_DT = "2024-06-15T10:00:00Z"


def _point(lat: float, lon: float, speed: float | None = None) -> GPSPoint:
    return GPSPoint(
        lat=lat,
        lon=lon,
        timestamp=FIXED_DT,
        altitude=100.0,
        speed=speed,
    )


def test_create_route_map_returns_json_path() -> None:
    points = [_point(45.0, 9.0, 25.0), _point(45.01, 9.01, 25.0)]
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "route.json")
        path = aethermap_adapter.create_route_map(points, output_path=out)
        assert path == out
        assert os.path.exists(out)
        payload = json.loads(open(out, encoding="utf-8").read())
        assert payload["engine"] == "aethermap"
        assert len(payload["entities"]) > 0


def test_create_route_map_with_statistics() -> None:
    points = [_point(45.0, 9.0, 25.0), _point(45.01, 9.01, 25.0)]
    stats = RouteStatistics(
        total_distance_m=2500.0,
        total_duration_s=3600.0,
        avg_speed_km_h=25.0,
        max_speed_km_h=30.0,
        total_elevation_gain_m=100.0,
    )
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "route_stats.json")
        path = aethermap_adapter.create_route_map(points, statistics=stats, output_path=out)
        payload = json.loads(open(out, encoding="utf-8").read())
        assert "statistics" in payload
        assert payload["statistics"]["total_distance_m"] == 2500.0
        assert payload["statistics"]["avg_speed_km_h"] == 25.0


def test_create_route_map_raises_on_empty_points() -> None:
    with pytest.raises(ValueError, match="No GPS points provided"):
        aethermap_adapter.create_route_map([])


def test_build_scene_entities_have_serializable_pts() -> None:
    points = [_point(45.0, 9.0, 25.0), _point(45.01, 9.01, 25.0)]
    scene = aethermap_adapter._build_scene(points, None, True)
    assert len(scene.entities) > 0
    for entity in scene.entities:
        assert "tipo" in entity
        assert "pts" in entity
        assert "char" in entity
        for pt in entity["pts"]:
            assert len(pt) == 3
