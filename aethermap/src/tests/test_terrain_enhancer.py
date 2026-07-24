"""Tests for aethermap.render.terrain_enhancer (DEM integration)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aethermap.render.terrain_enhancer import (
    _face_bbox,
    _face_direction,
    enhance_face,
    fetch_dem_tile,
    get_terrain_bboxes,
    build_enhanced_heightfield,
)


class TestFaceDirection:
    def test_face_0_center(self):
        d = _face_direction(0, 0.0, 0.0)
        assert np.allclose(d, [1.0, 0.0, 0.0], atol=1e-6)

    def test_face_4_center(self):
        d = _face_direction(4, 0.0, 0.0)
        assert np.allclose(d, [0.0, 0.0, 1.0], atol=1e-6)

    def test_unit_length(self):
        for face in range(6):
            d = _face_direction(face, 0.7, -0.3)
            assert np.isclose(np.linalg.norm(d), 1.0, atol=1e-6)


class TestFaceBbox:
    def test_returns_expected_keys(self):
        bbox = _face_bbox(0)
        for k in ("min_lat", "max_lat", "min_lon", "max_lon", "center_lat", "center_lon"):
            assert k in bbox

    def test_face0_center_near_equator(self):
        bbox = _face_bbox(0)
        assert abs(bbox["center_lat"]) < 40

    def test_each_face_has_bbox(self):
        for face in range(6):
            bbox = _face_bbox(face)
            assert bbox["min_lat"] <= bbox["max_lat"]
            assert bbox["min_lon"] <= bbox["max_lon"]


class TestFetchDemTile:
    @patch("urllib.request.urlopen")
    def test_returns_array_on_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'{"heights": [100.0, 200.0, 300.0, 400.0]}'
        )
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        bbox = {"min_lat": 44.0, "max_lat": 46.0, "min_lon": 8.0, "max_lon": 10.0}
        tile = fetch_dem_tile(bbox, resolution=2, base_url="http://localhost:8000")
        assert tile is not None
        assert tile.shape == (2, 2)

    @patch("urllib.request.urlopen", side_effect=Exception("fail"))
    def test_returns_none_on_failure(self, _mock_urlopen):
        bbox = {"min_lat": 44.0, "max_lat": 46.0, "min_lon": 8.0, "max_lon": 10.0}
        tile = fetch_dem_tile(bbox, resolution=2)
        assert tile is None


class TestEnhanceFace:
    def test_returns_unchanged_when_no_dem(self):
        hf = np.ones((4, 4), dtype=np.float32) * 0.5
        out = enhance_face(hf, face=0, base_url="http://does-not-exist.invalid", resolution=4)
        assert np.allclose(out, hf)

    @patch("aethermap.render.terrain_enhancer.fetch_dem_tile")
    def test_merges_dem_into_hf(self, mock_fetch):
        hf = np.ones((4, 4), dtype=np.float32) * 0.5
        dem = np.linspace(100, 400, 16).reshape(4, 4).astype(np.float32)
        mock_fetch.return_value = dem
        out = enhance_face(hf, face=0, base_url="http://localhost:8000", resolution=4)
        assert not np.allclose(out, hf)
        assert out.shape == hf.shape
        assert out.dtype == np.float32


class TestBuildEnhancedHeightfield:
    @patch("aethermap.render.terrain_enhancer.enhance_face")
    def test_calls_enhance_for_selected_faces(self, mock_enhance):
        mock_enhance.side_effect = lambda hf, face, *a, **kw: hf
        hf = build_enhanced_heightfield(
            n=8, base_alt=0.0, height_scale=0.04,
            base_url="http://localhost:8000", faces=(0, 4)
        )
        assert hf.shape == (6 * 8 * 8,)
        assert mock_enhance.call_count == 2

    def test_returns_procedural_when_no_url(self):
        hf = build_enhanced_heightfield(n=8, base_url="")
        assert hf.shape == (6 * 8 * 8,)


class TestGetTerrainBboxes:
    def test_returns_six_faces(self):
        bboxes = get_terrain_bboxes(n=32)
        assert set(bboxes.keys()) == set(range(6))
