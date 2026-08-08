"""Tests for AetherMap Sprint 5 modules."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aethermap.ai.ingest import RawPoint
from aethermap.ai.road_segmenter import RoadSurfaceSegmenter, _extract_segment_features
from aethermap.ai.traffic_classifier import TrafficClassifier, _extract_traffic_features


def _point(lat: float, lon: float, ele: float | None = None, speed: float | None = None, t: datetime | None = None) -> RawPoint:
    return RawPoint(
        lat=lat,
        lon=lon,
        ele=ele,
        speed=speed,
        t=t or datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC),
    )


class TestSegmentFeatures:
    def test_single_point_returns_defaults(self) -> None:
        feat = _extract_segment_features([_point(45.0, 9.0, 100.0)])
        assert feat.n_points == 1
        assert feat.length_m == 0.0

    def test_two_points_compute_length(self) -> None:
        pts = [_point(45.0, 9.0, 100.0), _point(45.001, 9.001, 110.0)]
        feat = _extract_segment_features(pts)
        assert feat.length_m > 0.0
        assert feat.n_points == 2


class TestRoadSurfaceSegmenter:
    def test_classify_returns_valid_surface(self) -> None:
        seg = RoadSurfaceSegmenter()
        pts = [_point(45.0, 9.0, 100.0), _point(45.001, 9.001, 110.0)]
        surface = seg.classify_segment(pts)
        assert surface in RoadSurfaceSegmenter.SURFACE_CLASSES

    def test_segment_ride_returns_list(self) -> None:
        seg = RoadSurfaceSegmenter()
        pts = [_point(45.0 + i * 0.0005, 9.0 + i * 0.0005, 100.0 + i) for i in range(20)]
        segments = seg.segment_ride(pts, window=6)
        assert isinstance(segments, list)
        assert len(segments) > 0
        for s in segments:
            assert "surface_type" in s
            assert "confidence" in s
            assert "start_index" in s
            assert "end_index" in s

    def test_to_geojson_returns_feature_collection(self) -> None:
        seg = RoadSurfaceSegmenter()
        pts = [_point(45.0 + i * 0.0005, 9.0 + i * 0.0005, 100.0 + i) for i in range(20)]
        segments = seg.segment_ride(pts, window=6)
        geojson = seg.to_geojson(pts, segments)
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == len(segments)
        for feat in geojson["features"]:
            assert feat["type"] == "Feature"
            assert feat["geometry"]["type"] == "LineString"
            assert len(feat["geometry"]["coordinates"]) >= 2


class TestTrafficFeatures:
    def test_no_speed_returns_defaults(self) -> None:
        feat = _extract_traffic_features([_point(45.0, 9.0, 100.0)])
        assert feat.avg_speed_kmh == 0.0
        assert feat.stops == 0

    def test_speed_computes_stats(self) -> None:
        pts = [
            _point(45.0, 9.0, 100.0, speed=10.0),
            _point(45.001, 9.001, 110.0, speed=20.0),
            _point(45.002, 9.002, 120.0, speed=15.0),
        ]
        feat = _extract_traffic_features(pts)
        assert feat.avg_speed_kmh == pytest.approx(15.0)
        assert feat.max_speed_kmh == 20.0
        assert feat.min_speed_kmh == 10.0


class TestTrafficClassifier:
    def test_classify_segment_returns_valid_class(self) -> None:
        cls = TrafficClassifier()
        pts = [_point(45.0, 9.0, 100.0, speed=25.0), _point(45.001, 9.001, 110.0, speed=30.0)]
        assert cls.classify_segment(pts) in TrafficClassifier.CLASSES

    def test_classify_ride_returns_segments(self) -> None:
        cls = TrafficClassifier()
        pts = [_point(45.0 + i * 0.0005, 9.0 + i * 0.0005, 100.0 + i, speed=20.0 + i) for i in range(20)]
        segments = cls.classify_ride(pts, window=6)
        assert isinstance(segments, list)
        assert len(segments) > 0
        for s in segments:
            assert "traffic_level" in s
            assert "confidence" in s
            assert s["traffic_level"] in TrafficClassifier.CLASSES

    def test_to_geojson_returns_feature_collection(self) -> None:
        cls = TrafficClassifier()
        pts = [_point(45.0 + i * 0.0005, 9.0 + i * 0.0005, 100.0 + i, speed=20.0 + i) for i in range(20)]
        segments = cls.classify_ride(pts, window=6)
        geojson = cls.to_geojson(pts, segments)
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == len(segments)
        for feat in geojson["features"]:
            assert feat["properties"]["traffic_level"] in TrafficClassifier.CLASSES
            assert "color" in feat["properties"]
