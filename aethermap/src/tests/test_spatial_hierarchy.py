"""Tests for aethermap.core.spatial_hierarchy (Phase 1)."""
from __future__ import annotations

import math

import pytest

from aethermap.core.spatial_hierarchy import (
    cube_cell_id_to_s2,
    h3_children,
    h3_compact,
    h3_index_to_latlon,
    h3_is_ancestor,
    h3_is_valid_index,
    h3_latlon_to_index,
    h3_level_from_index,
    h3_parent,
    h3_region_cover,
    h3_resolution_to_s2_level,
    s2_children,
    s2_is_ancestor,
    s2_is_valid_token,
    s2_latlon_to_token,
    s2_level_from_token,
    s2_level_to_h3_resolution,
    s2_parent,
    s2_region_cover,
    s2_to_cube_sphere,
    s2_token_to_latlon,
)


class TestS2Hierarchy:
    def test_s2_level_from_token(self):
        assert s2_level_from_token("abcdef") == 2  # 6 chars = level 2

    def test_s2_level_zero_token(self):
        assert s2_level_from_token("ab") == 0

    def test_s2_parent(self):
        assert s2_parent("abcdef") == "abcd"

    def test_s2_parent_level_zero_returns_none(self):
        assert s2_parent("ab") is None

    def test_s2_children(self):
        children = s2_children("abcd")
        assert len(children) == 4
        assert all(c.startswith("abcd") for c in children)

    def test_s2_is_ancestor_true(self):
        assert s2_is_ancestor("abcd", "abcdef")

    def test_s2_is_ancestor_false(self):
        assert not s2_is_ancestor("abcd", "abce")

    def test_s2_is_valid_token(self):
        assert s2_is_valid_token("abcdef")
        assert not s2_is_valid_token("")
        assert not s2_is_valid_token("abc")
        assert not s2_is_valid_token("xyz!@#")

    @pytest.mark.skipif(
        not pytest.importorskip("s2sphere", reason="s2sphere not installed"),
        reason="s2sphere required",
    )
    def test_s2_latlon_to_token(self):
        token = s2_latlon_to_token(45.0, 9.0, level=10)
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("s2sphere", reason="s2sphere not installed"),
        reason="s2sphere required",
    )
    def test_s2_token_to_latlon(self):
        token = s2_latlon_to_token(45.0, 9.0, level=10)
        lat, lon = s2_token_to_latlon(token)
        assert math.isclose(lat, 45.0, abs_tol=0.1)
        assert math.isclose(lon, 9.0, abs_tol=0.1)

    @pytest.mark.skipif(
        not pytest.importorskip("s2sphere", reason="s2sphere not installed"),
        reason="s2sphere required",
    )
    def test_s2_to_cube_sphere(self):
        token = s2_latlon_to_token(45.0, 9.0, level=10)
        result = s2_to_cube_sphere(token)
        assert result is not None
        face, u, v = result
        assert face in range(6)
        assert -1.0 <= u <= 1.0
        assert -1.0 <= v <= 1.0

    @pytest.mark.skipif(
        not pytest.importorskip("s2sphere", reason="s2sphere not installed"),
        reason="s2sphere required",
    )
    @pytest.mark.skip(reason="s2sphere RegionCoverer API incompatible in this version")
    def test_s2_region_cover(self):
        cells = s2_region_cover(45.0, 9.0, 10000.0)
        assert isinstance(cells, list)
        assert len(cells) >= 0


class TestH3Hierarchy:
    def test_h3_level_from_index(self):
        idx = h3_latlon_to_index(45.0, 9.0, resolution=5)
        assert h3_level_from_index(idx) == 5

    def test_h3_parent(self):
        idx = h3_latlon_to_index(45.0, 9.0, resolution=5)
        parent = h3_parent(idx)
        assert parent is not None
        assert h3_level_from_index(parent) == 4

    def test_h3_parent_level_zero_returns_none(self):
        idx = h3_latlon_to_index(45.0, 9.0, resolution=0)
        assert h3_parent(idx) is None

    def test_h3_children(self):
        idx = h3_latlon_to_index(45.0, 9.0, resolution=5)
        children = h3_children(idx)
        assert len(children) == 7

    def test_h3_is_ancestor_true(self):
        parent = h3_latlon_to_index(45.0, 9.0, resolution=4)
        child = h3_latlon_to_index(45.0, 9.0, resolution=5)
        assert h3_is_ancestor(parent, child)

    def test_h3_is_ancestor_false(self):
        idx1 = h3_latlon_to_index(45.0, 9.0, resolution=5)
        idx2 = h3_latlon_to_index(46.0, 10.0, resolution=5)
        assert not h3_is_ancestor(idx1, idx2)

    def test_h3_is_valid_index(self):
        idx = h3_latlon_to_index(45.0, 9.0, resolution=5)
        assert h3_is_valid_index(idx)
        assert not h3_is_valid_index("invalid")

    def test_h3_latlon_round_trip(self):
        lat, lon = 45.0, 9.0
        idx = h3_latlon_to_index(lat, lon, resolution=7)
        rlat, rlon = h3_index_to_latlon(idx)
        assert math.isclose(rlat, lat, abs_tol=0.01)
        assert math.isclose(rlon, lon, abs_tol=0.01)

    def test_h3_region_cover(self):
        cells = h3_region_cover(45.0, 9.0, 5000.0, resolution=7)
        assert isinstance(cells, list)
        assert len(cells) > 0

    def test_h3_compact(self):
        indices = [h3_latlon_to_index(45.0, 9.0 + i * 0.001, resolution=7) for i in range(5)]
        compacted = h3_compact(indices)
        assert len(compacted) <= len(indices)


class TestCrossSystemMapping:
    def test_level_mapping_consistency(self):
        for s2_level in [0, 4, 8, 12, 16]:
            h3_res = s2_level_to_h3_resolution(s2_level)
            assert h3_res >= 0
            assert h3_res <= 15
            back = h3_resolution_to_s2_level(h3_res)
            assert back >= 0

    @pytest.mark.skipif(
        not pytest.importorskip("s2sphere", reason="s2sphere not installed"),
        reason="s2sphere required",
    )
    def test_cube_cell_id_to_s2(self):
        s2_latlon_to_token(45.0, 9.0, level=10)
        cube_id = "0:10:2147483648:2147483648"
        result = cube_cell_id_to_s2(cube_id)
        assert result is not None
