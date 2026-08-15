"""Tests for aethermap.data.dem_loader."""
from __future__ import annotations

import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aethermap.data.dem_loader import DEMLoader, get_dem_loader


class TestDEMLoaderLocal:
    def test_returns_procedural_when_no_dir(self, tmp_path):
        loader = DEMLoader(dem_dir=None)
        hf = loader.load((44.0, 46.0, 8.0, 10.0), resolution=8)
        assert hf.shape == (8, 8)
        assert hf.dtype == np.float32

    def test_returns_procedural_when_dir_empty(self, tmp_path):
        loader = DEMLoader(dem_dir=tmp_path)
        hf = loader.load((44.0, 46.0, 8.0, 10.0), resolution=8)
        assert hf.shape == (8, 8)

    def test_returns_procedural_when_no_matching_files(self, tmp_path):
        (tmp_path / "other.tif").write_bytes(b"not a geotiff")
        loader = DEMLoader(dem_dir=tmp_path)
        hf = loader.load((44.0, 46.0, 8.0, 10.0), resolution=8)
        assert hf.shape == (8, 8)

    def test_cache_hit(self, tmp_path):
        loader = DEMLoader(dem_dir=tmp_path)
        hf1 = loader.load((44.0, 46.0, 8.0, 10.0), resolution=8)
        hf2 = loader.load((44.0, 46.0, 8.0, 10.0), resolution=8)
        assert hf1 is hf2

    def test_different_bbox_different_cache(self, tmp_path):
        loader = DEMLoader(dem_dir=tmp_path)
        hf1 = loader.load((44.0, 46.0, 8.0, 10.0), resolution=8)
        hf2 = loader.load((45.0, 47.0, 9.0, 11.0), resolution=8)
        assert hf1 is not hf2


class TestDEMLoaderRemoteCopernicus:
    def test_downloads_copernicus_tile(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AETHERMAP_DEM_REMOTE_URL", "https://example.com/tiles")

        fake_tif = tmp_path / "Copernicus_DSM_30_N44_E008_DSM.tif"
        fake_tif.write_bytes(b"fake geotiff")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [b"fake geotiff"]
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_resp
            loader = DEMLoader(dem_dir=tmp_path)
            loader._try_download_copernicus(44.0, 46.0, 8.0, 10.0)

        downloaded = tmp_path / "Copernicus_DSM_30_N44_E008_DSM.tif"
        assert downloaded.exists()

    def test_skips_download_when_no_remote_url(self, tmp_path):
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.delenv("AETHERMAP_DEM_REMOTE_URL", raising=False)
        loader = DEMLoader(dem_dir=tmp_path)
        result = loader._try_download_copernicus(44.0, 46.0, 8.0, 10.0)
        assert result == []
        monkeypatch.undo()

    def test_handles_download_failure_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AETHERMAP_DEM_REMOTE_URL", "https://example.com/tiles")

        with patch("requests.get", side_effect=Exception("network fail")):
            loader = DEMLoader(dem_dir=tmp_path)
            result = loader._try_download_copernicus(44.0, 46.0, 8.0, 10.0)

        assert result == []

    def test_returns_existing_cached_tile(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AETHERMAP_DEM_REMOTE_URL", "https://example.com/tiles")

        fake_tif = tmp_path / "Copernicus_DSM_30_N44_E008_DSM.tif"
        fake_tif.write_bytes(b"cached")

        loader = DEMLoader(dem_dir=tmp_path)
        result = loader._try_download_copernicus(44.0, 46.0, 8.0, 10.0)
        assert fake_tif in result

    def test_downloads_zip_and_extracts(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AETHERMAP_DEM_REMOTE_URL", "https://example.com/tiles")

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("Copernicus_DSM_30_N44_E008_DSM.tif", b"tif data")
        zip_buffer.seek(0)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [zip_buffer.read()]
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_resp
            loader = DEMLoader(dem_dir=tmp_path)
            result = loader._try_download_copernicus(44.0, 46.0, 8.0, 10.0)

        assert len(result) >= 1
        assert any(p.exists() for p in result)


class TestGetDemLoader:
    def test_returns_none_when_no_config(self, monkeypatch):
        monkeypatch.delenv("AETHERMAP_DEM_DIR", raising=False)
        monkeypatch.delenv("AETHERMAP_DEM_PATH", raising=False)
        monkeypatch.delenv("AETHERMAP_DEM_REMOTE_URL", raising=False)
        assert get_dem_loader() is None

    def test_returns_loader_for_local_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AETHERMAP_DEM_DIR", str(tmp_path))
        monkeypatch.delenv("AETHERMAP_DEM_REMOTE_URL", raising=False)
        loader = get_dem_loader()
        assert loader is not None
        assert loader._dem_dir == tmp_path

    def test_returns_loader_for_remote_url(self, monkeypatch):
        monkeypatch.delenv("AETHERMAP_DEM_DIR", raising=False)
        monkeypatch.delenv("AETHERMAP_DEM_PATH", raising=False)
        monkeypatch.setenv("AETHERMAP_DEM_REMOTE_URL", "https://example.com/tiles")
        loader = get_dem_loader()
        assert loader is not None
        assert loader._dem_dir is not None
