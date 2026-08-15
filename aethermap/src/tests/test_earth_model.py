"""Tests for aethermap.core.earth_model (Phase 1)."""
from __future__ import annotations

import math
from datetime import UTC, datetime

from aethermap.core.earth_model import (
    EARTH,
    EARTH_RADIUS_AUTHALIC,
    EARTH_RADIUS_MEAN,
    EARTH_RADIUS_VOLUMETRIC,
    CompositeHeightfield,
    EGM96Geoid,
    EGM2008Geoid,
    HeightSample,
    ProceduralHeightfield,
    geoid_height,
    gravity_wgs84,
    set_geoid,
)


class TestEarthParams:
    def test_wgs84_constants(self):
        assert math.isclose(EARTH.semi_major_axis, 6378137.0)
        assert math.isclose(EARTH.semi_minor_axis, 6378137.0 * (1.0 - 1.0 / 298.257223563))

    def test_radius_of_curvature_equator(self):
        # At equator, radius of curvature = semi-major axis
        r = EARTH.radius_of_curvature(0.0)
        assert math.isclose(r, 6378137.0, rel_tol=1e-6)

    def test_radius_of_curvature_pole(self):
        # Prime vertical radius at pole = a²/b ≈ 6399593 m
        r = EARTH.radius_of_curvature(90.0)
        assert math.isclose(r, 6399593.0, rel_tol=1e-3)

    def test_surface_radius_range(self):
        for lat in [0.0, 45.0, 90.0]:
            r = EARTH.surface_radius(lat)
            assert 6_356_000 < r < 6_380_000

    def test_surface_area(self):
        area = EARTH.surface_area()
        assert 5.1e14 < area < 5.2e14  # ~510 million km²

    def test_meridian_arc_length(self):
        length = EARTH.meridian_arc_length(0.0, 90.0)
        assert 9_900_000 < length < 10_100_000  # ~10,000 km quarter meridian

    def test_mean_radius_constant(self):
        assert math.isclose(EARTH_RADIUS_MEAN, 6371008.8)

    def test_authalic_radius(self):
        assert 6_371_000 < EARTH_RADIUS_AUTHALIC < 6_372_000

    def test_volumetric_radius(self):
        assert 6_371_000 < EARTH_RADIUS_VOLUMETRIC < 6_372_000


class TestGeoidModel:
    def test_egm96_returns_zero(self):
        model = EGM96Geoid()
        assert model.height(45.0, 9.0) == 0.0

    def test_egm2008_returns_zero(self):
        model = EGM2008Geoid()
        assert model.height(45.0, 9.0) == 0.0

    def test_set_geoid(self):
        set_geoid(EGM2008Geoid())
        assert geoid_height(0.0, 0.0) == 0.0
        set_geoid(EGM96Geoid())  # restore

    def test_geoid_height_after_set(self):
        set_geoid(EGM2008Geoid())
        h = geoid_height(45.0, 9.0)
        assert h == 0.0
        set_geoid(EGM96Geoid())  # restore


class TestHeightfield:
    def test_procedural_returns_positive(self):
        hf = ProceduralHeightfield(seed=42)
        val = hf.sample(45.0, 9.0)
        assert isinstance(val, float)
        assert -5000 < val < 5000  # reasonable range for amplitude=2000

    def test_procedural_deterministic(self):
        hf1 = ProceduralHeightfield(seed=42)
        hf2 = ProceduralHeightfield(seed=42)
        assert math.isclose(hf1.sample(45.0, 9.0), hf2.sample(45.0, 9.0))

    def test_procedural_different_seeds(self):
        hf1 = ProceduralHeightfield(seed=1)
        hf2 = ProceduralHeightfield(seed=2)
        # Different seeds should produce different values (very likely)
        assert not math.isclose(hf1.sample(45.0, 9.0), hf2.sample(45.0, 9.0))

    def test_procedural_batch(self):
        hf = ProceduralHeightfield(seed=42)
        points = [(45.0, 9.0), (46.0, 10.0), (44.0, 8.0)]
        vals = hf.sample_batch(points)
        assert len(vals) == 3
        assert all(isinstance(v, float) for v in vals)

    def test_procedural_gradient(self):
        hf = ProceduralHeightfield(seed=42)
        dlat, dlon = hf.gradient(45.0, 9.0)
        assert isinstance(dlat, float)
        assert isinstance(dlon, float)
        assert not math.isnan(dlat)
        assert not math.isnan(dlon)

    def test_composite_heightfield(self):
        hf1 = ProceduralHeightfield(seed=42, amplitude=100.0)
        hf2 = ProceduralHeightfield(seed=99, amplitude=50.0)
        composite = CompositeHeightfield([(hf1, 0.7), (hf2, 0.3)])
        val = composite.sample(45.0, 9.0)
        assert isinstance(val, float)
        assert not math.isnan(val)

    def test_composite_batch(self):
        hf1 = ProceduralHeightfield(seed=42, amplitude=100.0)
        composite = CompositeHeightfield([(hf1, 1.0)])
        points = [(45.0, 9.0), (46.0, 10.0)]
        vals = composite.sample_batch(points)
        assert len(vals) == 2


class TestGravity:
    def test_gravity_equator(self):
        g = gravity_wgs84(0.0, 0.0)
        assert 9.7 < g < 9.9  # slightly less than pole

    def test_gravity_pole(self):
        g = gravity_wgs84(90.0, 0.0)
        assert 9.8 < g < 10.0

    def test_gravity_decreases_with_altitude(self):
        g_surface = gravity_wgs84(45.0, 0.0)
        g_altitude = gravity_wgs84(45.0, 10000.0)
        assert g_altitude < g_surface

    def test_gravity_positive(self):
        for lat in [0.0, 45.0, 90.0]:
            for alt in [0.0, 1000.0, 10000.0]:
                assert gravity_wgs84(lat, alt) > 0.0


class TestHeightSample:
    def test_default_values(self):
        sample = HeightSample(lat=45.0, lon=9.0)
        assert sample.elevation_m == 0.0
        assert sample.confidence == 1.0
        assert sample.source == "unknown"
        assert isinstance(sample.timestamp, datetime)

    def test_custom_values(self):
        now = datetime.now(UTC)
        sample = HeightSample(
            lat=45.0, lon=9.0, elevation_m=1500.0, timestamp=now, confidence=0.9, source="dem"
        )
        assert sample.elevation_m == 1500.0
        assert sample.confidence == 0.9
        assert sample.source == "dem"
        assert sample.timestamp == now


class TestEarthConstants:
    def test_radius_constants_order(self):
        # semi_major > mean > authalic > volumetric > semi_minor for WGS84
        assert (
            EARTH.semi_major_axis > EARTH_RADIUS_MEAN > EARTH_RADIUS_AUTHALIC
            > EARTH_RADIUS_VOLUMETRIC > EARTH.semi_minor_axis
        )

    def test_earth_params_defaults(self):
        assert EARTH.semi_major_axis == 6378137.0
        assert math.isclose(EARTH.flattening, 1.0 / 298.257223563)
        assert math.isclose(EARTH.eccentricity_squared, EARTH.flattening * (2.0 - EARTH.flattening))
