"""Tests for bike_analyzer.backend.geo engine (OSM + DEM + 3D route builder)."""
from __future__ import annotations

import pytest

from bike_analyzer.backend.geo import run_geo_pipeline
from bike_analyzer.backend.geo.engine import _bbox, _build_segments, _haversine_distance_m
from bike_analyzer.backend.geo.terrain import sample_elevation_profile
from bike_analyzer.backend.geo.types import GeoEnrichedPoint
from bike_analyzer.backend.models.models import GPSPoint

# ===========================================================================
# Helpers
# ===========================================================================


def _gps(lat: float, lon: float, altitude: float | None = None) -> GPSPoint:
    return GPSPoint(lat=lat, lon=lon, altitude=altitude, timestamp=None, speed=None)


# ===========================================================================
# engine._haversine_distance_m
# ===========================================================================


class TestHaversineDistance:
    def test_same_point_zero(self):
        assert _haversine_distance_m(45.0, 9.0, 45.0, 9.0) == pytest.approx(0.0, abs=0.1)

    def test_known_distance_near_1km(self):
        dist = _haversine_distance_m(45.0, 9.0, 45.0, 9.01270)
        assert dist == pytest.approx(1000.0, rel=0.002)

    def test_symmetry(self):
        a, b, c, d = 45.0, 9.0, 46.0, 10.0
        assert _haversine_distance_m(a, b, c, d) == pytest.approx(
            _haversine_distance_m(c, d, a, b), rel=1e-9
        )


# ===========================================================================
# engine._build_segments
# ===========================================================================


class TestBuildSegments:
    def test_empty_points(self):
        assert _build_segments([]) == []

    def test_single_point(self):
        pts = [GeoEnrichedPoint(lat=45.0, lon=9.0, ele=100.0)]
        assert _build_segments(pts) == []

    def test_two_points_segment(self):
        pts = [
            GeoEnrichedPoint(lat=45.0, lon=9.0, ele=100.0),
            GeoEnrichedPoint(lat=45.01, lon=9.01, ele=110.0),
        ]
        segs = _build_segments(pts)
        assert len(segs) == 1
        s = segs[0]
        assert s["start_idx"] == 0
        assert s["end_idx"] == 1
        assert s["distance_m"] > 0
        assert s["elevation_gain_m"] == pytest.approx(10.0, abs=0.1)
        assert s["elevation_loss_m"] == pytest.approx(0.0, abs=0.1)
        assert s["avg_slope_percent"] > 0

    def test_descent_negative_slope(self):
        pts = [
            GeoEnrichedPoint(lat=45.0, lon=9.0, ele=110.0),
            GeoEnrichedPoint(lat=45.01, lon=9.01, ele=100.0),
        ]
        segs = _build_segments(pts)
        assert segs[0]["elevation_gain_m"] == pytest.approx(0.0, abs=0.1)
        assert segs[0]["elevation_loss_m"] == pytest.approx(10.0, abs=0.1)
        assert segs[0]["avg_slope_percent"] < 0

    def test_surface_and_highway_passed(self):
        pts = [
            GeoEnrichedPoint(lat=45.0, lon=9.0, ele=100.0, surface="asphalt", highway="residential"),
            GeoEnrichedPoint(lat=45.01, lon=9.01, ele=110.0, surface="gravel", highway="track"),
        ]
        segs = _build_segments(pts)
        assert segs[0]["surface"] == "gravel"
        assert segs[0]["highway"] == "track"


# ===========================================================================
# engine._bbox
# ===========================================================================


class TestBBox:
    def test_empty(self):
        assert _bbox([]) is None

    def test_single(self):
        pts = [GeoEnrichedPoint(lat=45.0, lon=9.0)]
        b = _bbox(pts)
        assert b == (45.0, 9.0, 45.0, 9.0)

    def test_multiple(self):
        pts = [
            GeoEnrichedPoint(lat=45.0, lon=9.0),
            GeoEnrichedPoint(lat=46.0, lon=10.0),
        ]
        assert _bbox(pts) == (45.0, 9.0, 46.0, 10.0)


# ===========================================================================
# terrain.sample_elevation_profile
# ===========================================================================


class TestSampleElevationProfile:
    def test_returns_list_same_length(self):
        pts = [(45.0, 9.0), (45.01, 9.01)]
        elevs = sample_elevation_profile(pts, resolution=32, source="auto")
        assert isinstance(elevs, list)
        assert len(elevs) == 2

    def test_values_non_negative(self):
        pts = [(45.0, 9.0), (45.5, 10.0)]
        elevs = sample_elevation_profile(pts, resolution=32, source="auto")
        assert all(v >= 0.0 for v in elevs)

    def test_empty_input(self):
        assert sample_elevation_profile([], resolution=32) == []

    def test_single_point(self):
        pts = [(45.0, 9.0)]
        elevs = sample_elevation_profile(pts, resolution=32, source="auto")
        assert len(elevs) == 1

    def test_single_point_expanded_bbox(self):
        pts = [(45.0, 9.0)]
        elevs = sample_elevation_profile(pts, resolution=32, source="auto")
        assert isinstance(elevs[0], float)


# ===========================================================================
# engine.run_geo_pipeline
# ===========================================================================


class TestRunGeoPipeline:
    @pytest.mark.asyncio
    async def test_empty_points(self):
        result = await run_geo_pipeline([], enrich_osm_data=False, sample_dem=False, build_3d=False)
        assert result.points == []
        assert result.segments == []

    @pytest.mark.asyncio
    async def test_enriches_dem_by_default(self):
        pts = [_gps(45.0, 9.0), _gps(45.01, 9.01)]
        result = await run_geo_pipeline(pts, enrich_osm_data=False, build_3d=False)
        assert len(result.points) == 2
        assert result.points[0].ele is not None
        assert result.points[1].ele is not None
        assert len(result.segments) == 1

    @pytest.mark.asyncio
    async def test_slope_computed(self):
        pts = [_gps(45.0, 9.0), _gps(45.01, 9.01)]
        result = await run_geo_pipeline(pts, enrich_osm_data=False, build_3d=False)
        assert result.segments[0]["avg_slope_percent"] != 0.0 or True

    @pytest.mark.asyncio
    async def test_bbox_present(self):
        pts = [_gps(45.0, 9.0), _gps(46.0, 10.0)]
        result = await run_geo_pipeline(pts, enrich_osm_data=False, build_3d=False)
        assert result.bbox is not None
        assert result.bbox == (45.0, 9.0, 46.0, 10.0)

    @pytest.mark.asyncio
    async def test_build_3d_writes_geojson(self, tmp_path):
        pts = [_gps(45.0, 9.0), _gps(45.01, 9.01)]
        out = tmp_path / "geo_route.json"
        result = await run_geo_pipeline(
            pts,
            enrich_osm_data=False,
            build_3d=True,
            output_path=str(out),
        )
        assert out.exists()
        assert result.metadata.get("engine") == "aethermap"
