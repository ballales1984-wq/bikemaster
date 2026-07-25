"""Tests for aethermap.core.coordinates (Phase 1 earth model)."""
from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from aethermap.core.coordinates import (
    CubeCell,
    cube_cell_id,
    cube_to_geodetic,
    ecef_to_geodetic,
    ecef_to_geodetic_direction,
    geodetic_to_cube,
    geodetic_to_direction,
    geodetic_to_ecef,
    h3_cell,
    s2_cell_id,
)
from aethermap.ai.models import Posizione


class TestWGS84:
    def test_round_trip_equator_greenwich(self):
        ecef = geodetic_to_ecef(0.0, 0.0, 0.0)
        g = ecef_to_geodetic(ecef.x, ecef.y, ecef.z)
        assert math.isclose(g.lat, 0.0, abs_tol=1e-9)
        assert math.isclose(g.lon, 0.0, abs_tol=1e-9)
        assert math.isclose(g.alt, 0.0, abs_tol=1e-3)

    def test_round_trip_with_altitude(self):
        lat, lon, alt = 45.0, 9.0, 1234.0
        ecef = geodetic_to_ecef(lat, lon, alt)
        g = ecef_to_geodetic(ecef.x, ecef.y, ecef.z)
        assert math.isclose(g.lat, lat, abs_tol=1e-9)
        assert math.isclose(g.lon, lon, abs_tol=1e-9)
        assert math.isclose(g.alt, alt, abs_tol=1e-3)

    def test_round_trip_south_america(self):
        lat, lon, alt = -33.0, -56.0, 500.0
        ecef = geodetic_to_ecef(lat, lon, alt)
        g = ecef_to_geodetic(ecef.x, ecef.y, ecef.z)
        assert math.isclose(g.lat, lat, abs_tol=1e-9)
        assert math.isclose(g.lon, lon, abs_tol=1e-9)
        assert math.isclose(g.alt, alt, abs_tol=1e-3)


class TestDirection:
    @pytest.mark.parametrize("lat,lon", [(0, 0), (45, 9), (-33, -56), (89, 180)])
    def test_direction_inverse(self, lat, lon):
        d = geodetic_to_direction(lat, lon)
        g = ecef_to_geodetic_direction(*d)
        assert math.isclose(g.lat, lat, abs_tol=1e-10)
        assert math.isclose(g.lon, lon, abs_tol=1e-10)
        assert g.alt == 0.0


class TestCubeSphere:
    @pytest.mark.parametrize("lat,lon,alt", [
        (0.0, 0.0, 0.0),
        (45.0, 9.0, 100.0),
        (-33.0, -56.0, 500.0),
        (89.0, 180.0, 0.0),
    ])
    def test_round_trip(self, lat, lon, alt):
        c = geodetic_to_cube(lat, lon)
        g = cube_to_geodetic(c, alt=alt)
        assert math.isclose(g.lat, lat, abs_tol=1e-6)
        assert math.isclose(g.lon, lon, abs_tol=1e-6)
        assert g.alt == alt

    def test_cube_cell_id_format(self):
        cell = CubeCell(face=2, u=0.5, v=-0.3, level=4)
        cid = cube_cell_id(cell)
        parts = cid.split(":")
        assert len(parts) == 4
        assert parts[0] == "2"
        assert parts[1] == "4"
        assert 0 <= int(parts[2]) <= 2**32
        assert 0 <= int(parts[3]) <= 2**32


class TestS2H3:
    def test_s2_cell_id_returns_token(self):
        pytest.importorskip("s2sphere")
        token = s2_cell_id(45.0, 9.0)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_h3_cell_returns_index(self):
        pytest.importorskip("h3")
        idx = h3_cell(45.0, 9.0)
        assert isinstance(idx, str)
        assert len(idx) > 0


class TestPosizioneFromLatlon:
    def test_without_optional_deps(self):
        with patch("aethermap.ai.models.s2_cell_id", side_effect=RuntimeError("missing")):
            with patch("aethermap.ai.models.h3_cell", side_effect=RuntimeError("missing")):
                p = Posizione.from_latlon(45.0, 9.0, alt=100.0)
                assert p.s2 is None
                assert p.h3 is None
                assert p.alt == 100.0
                assert p.cube_face is not None

    def test_with_optional_deps(self):
        p = Posizione.from_latlon(45.0, 9.0, alt=50.0)
        assert p.alt == 50.0
        assert p.cube_face is not None
        assert isinstance(p.s2, str)
        assert isinstance(p.h3, str)
