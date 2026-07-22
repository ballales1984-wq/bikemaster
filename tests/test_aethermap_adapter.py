"""Tests for AetherMap backend integration (GeoJSON serialization)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aethermap import Geometria, Oggetto, Posizione, WorldStore
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


def test_create_route_map_returns_json_path(tmp_path: Path) -> None:
    points = [_point(45.0, 9.0, 25.0), _point(45.01, 9.01, 25.0)]
    out = tmp_path / "route.json"
    path = aethermap_adapter.create_route_map(points, output_path=str(out))
    assert path == str(out)
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) > 0
    assert payload["metadata"]["engine"] == "aethermap"


def test_create_route_map_with_statistics(tmp_path: Path) -> None:
    points = [_point(45.0, 9.0, 25.0), _point(45.01, 9.01, 25.0)]
    stats = RouteStatistics(
        total_distance_m=2500.0,
        total_duration_s=3600.0,
        avg_speed_km_h=25.0,
        max_speed_km_h=30.0,
        total_elevation_gain_m=100.0,
    )
    out = tmp_path / "route_stats.json"
    path = aethermap_adapter.create_route_map(points, statistics=stats, output_path=str(out))
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "metadata" in payload
    assert "statistics" in payload["metadata"]
    assert payload["metadata"]["statistics"]["total_distance_m"] == 2500.0
    assert payload["metadata"]["statistics"]["avg_speed_km_h"] == 25.0


def test_create_route_map_raises_on_empty_points() -> None:
    with pytest.raises(ValueError, match="No GPS points provided"):
        aethermap_adapter.create_route_map([])


def test_create_route_map_features_have_valid_geometry(tmp_path: Path) -> None:
    points = [_point(45.0, 9.0, 25.0), _point(45.01, 9.01, 25.0)]
    out = tmp_path / "route_geom.json"
    aethermap_adapter.create_route_map(points, output_path=str(out))
    payload = json.loads(out.read_text(encoding="utf-8"))
    tipi = set()
    for feature in payload["features"]:
        assert feature["type"] == "Feature"
        assert "geometry" in feature
        assert "properties" in feature
        assert "tipo" in feature["properties"]
        tipi.add(feature["properties"]["tipo"])
        geom = feature["geometry"]
        if geom["type"] == "LineString":
            assert len(geom["coordinates"]) >= 2
            for coord in geom["coordinates"]:
                assert len(coord) >= 2
                assert -90 <= coord[1] <= 90   # lat
                assert -180 <= coord[0] <= 180  # lon
        elif geom["type"] == "Point":
            assert len(geom["coordinates"]) >= 2
    assert {"segment", "start", "end"}.issubset(tipi)
