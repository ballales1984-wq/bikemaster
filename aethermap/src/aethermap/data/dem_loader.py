"""AetherMap DEM loader (Punto 2 — dataset terreno reale).

Carica dati DEM reali da:
- Copernicus DEM GLO-30/90 (GeoTIFF, remoto o locale)
- SRTM (HGT locale)
- LiDAR (LAS/LAZ)

Fallback: heightfield procedurale se nessun dataset e` disponibile.

Interfaccia: `load_dem(bbox) -> heightfield numpy array`.
"""
from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class DEMLoader:
    """Carica DEM reali da file locali o remote Copernicus con fallback procedurale."""

    def __init__(self, dem_dir: str | Path | None = None) -> None:
        self._dem_dir = Path(dem_dir) if dem_dir else None
        self._cache: dict[str, np.ndarray] = {}

    def load(self, bbox: tuple[float, float, float, float], resolution: int = 64) -> np.ndarray:
        """Carica heightfield per bounding box.

        Args:
            bbox: (min_lat, max_lat, min_lon, max_lon)
            resolution: risoluzione griglia

        Returns:
            heightfield numpy array (resolution x resolution), valori normalizzati 0..1
        """
        cache_key = f"{bbox[0]:.4f}_{bbox[1]:.4f}_{bbox[2]:.4f}_{bbox[3]:.4f}_{resolution}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        hf = self._try_load_real_dem(bbox, resolution)
        if hf is None:
            hf = self._generate_procedural_fallback(resolution)

        self._cache[cache_key] = hf
        return hf

    def _try_load_real_dem(self, bbox: tuple[float, float, float, float], resolution: int) -> np.ndarray | None:
        if self._dem_dir is None or not self._dem_dir.exists():
            return None

        min_lat, max_lat, min_lon, max_lon = bbox
        candidates = self._find_dem_files(min_lat, max_lat, min_lon, max_lon)
        if not candidates:
            candidates = self._try_download_copernicus(min_lat, max_lat, min_lon, max_lon)
        if not candidates:
            return None

        for path in candidates:
            try:
                if path.suffix.lower() == ".tif":
                    return self._load_geotiff(path, bbox, resolution)
                elif path.suffix.lower() in (".hgt", ".hgt.zip"):
                    return self._load_hgt(path, bbox, resolution)
                elif path.suffix.lower() in (".las", ".laz"):
                    return self._load_las(path, bbox, resolution)
            except Exception as exc:
                logger.warning("Failed to load DEM from %s: %s", path, exc)
                continue
        return None

    def _find_dem_files(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> list[Path]:
        found: list[Path] = []
        if self._dem_dir is None:
            return found

        lat_prefix = "N" if min_lat >= 0 else "S"
        lon_prefix = "E" if min_lon >= 0 else "W"
        lat_str = f"{abs(int(min_lat)):02d}"
        lon_str = f"{abs(int(min_lon)):03d}"

        patterns = [
            f"*{lat_prefix}{lat_str}{lon_prefix}{lon_str}*",
            f"*{lat_prefix}{lat_str}{lon_prefix}{lon_str}.tif",
        ]

        for pattern in patterns:
            found.extend(self._dem_dir.glob(pattern))

        return list(dict.fromkeys(found))

    def _try_download_copernicus(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> list[Path]:
        """Try to download Copernicus DEM GLO-30 tiles for the bbox."""
        remote_url = os.environ.get("AETHERMAP_DEM_REMOTE_URL")
        if not remote_url:
            return []

        tile_lat = int(min_lat)
        tile_lon = int(min_lon)
        lat_sign = "N" if tile_lat >= 0 else "S"
        lon_sign = "E" if tile_lon >= 0 else "W"

        candidates: list[Path] = []
        filenames = [
            f"Copernicus_DSM_30_{lat_sign}{abs(tile_lat):02d}_{lon_sign}{abs(tile_lon):03d}_DSM.tif",
            f"Copernicus_DSM_30_{lat_sign}{abs(tile_lat):02d}_{lon_sign}{abs(tile_lon):03d}_DSM.zip",
        ]

        for filename in filenames:
            cache_path = self._dem_dir / filename
            if cache_path.exists():
                candidates.append(cache_path)
                continue

            url = f"{remote_url.rstrip('/')}/{filename}"
            try:
                import requests
                resp = requests.get(url, timeout=60, stream=True)
                if resp.status_code == 200:
                    self._dem_dir.mkdir(parents=True, exist_ok=True)
                    with open(cache_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if cache_path.suffix.lower() == ".zip":
                        with zipfile.ZipFile(cache_path) as zf:
                            tif_names = [n for n in zf.namelist() if n.lower().endswith(".tif")]
                            if tif_names:
                                extracted = self._dem_dir / tif_names[0]
                                zf.extract(tif_names[0], self._dem_dir)
                                candidates.append(extracted)
                    else:
                        candidates.append(cache_path)
            except Exception as exc:
                logger.info("Copernicus tile download failed for %s: %s", url, exc)

        return candidates

    def _load_geotiff(self, path: Path, bbox: tuple[float, float, float, float], resolution: int) -> np.ndarray | None:
        try:
            import rasterio
            from rasterio.warp import Resampling
        except ImportError:
            logger.info("rasterio not installed; skipping GeoTiff DEM")
            return None

        with rasterio.open(path) as src:
            if src.crs and src.crs.to_string() not in ("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs"):
                return None

            window = src.window(bbox[2], bbox[1], bbox[3], bbox[0])
            if window.width <= 0 or window.height <= 0:
                return None

            data = src.read(1, window=window, out_shape=(resolution, resolution), resampling=Resampling.bilinear)
            data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

            hmin = float(np.nanmin(data))
            hmax = float(np.nanmax(data))
            data = (data - hmin) / (hmax - hmin) if hmax - hmin > 1e-06 else np.zeros_like(data)

            return data.astype(np.float32)

    def _load_hgt(self, path: Path, bbox: tuple[float, float, float, float], resolution: int) -> np.ndarray | None:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                hgt_files = [n for n in zf.namelist() if n.lower().endswith(".hgt")]
                if not hgt_files:
                    return None
                with zf.open(hgt_files[0]) as f:
                    return self._parse_hgt(f, resolution)

        return self._parse_hgt(path, resolution)

    def _parse_hgt(self, fh: Any, resolution: int) -> np.ndarray | None:
        try:
            data = np.frombuffer(fh.read(), dtype=">i2")
            side = int(np.sqrt(data.size))
            if side * side != data.size:
                return None
            data = data.reshape((side, side)).astype(np.float32)
            hmin = float(data.min())
            hmax = float(data.max())
            data = (data - hmin) / (hmax - hmin) if hmax - hmin > 1e-06 else np.zeros_like(data)
            from PIL import Image
            img = Image.fromarray(data)
            img = img.resize((resolution, resolution), Image.Resampling.BILINEAR)
            return np.array(img, dtype=np.float32)
        except Exception as exc:
            logger.warning("Failed to parse HGT: %s", exc)
            return None

    def _load_las(self, path: Path, bbox: tuple[float, float, float, float], resolution: int) -> np.ndarray | None:
        try:
            import laspy
        except ImportError:
            logger.info("laspy not installed; skipping LiDAR DEM")
            return None

        try:
            las = laspy.read(path)
            mask = (
                (las.x >= bbox[2]) & (las.x <= bbox[3]) &
                (las.y >= bbox[0]) & (las.y <= bbox[1])
            )
            points = las.points[mask]
            if len(points) == 0:
                return None

            grid = np.zeros((resolution, resolution), dtype=np.float32)
            for i in range(resolution):
                lat = bbox[0] + (bbox[1] - bbox[0]) * (i + 0.5) / resolution
                for j in range(resolution):
                    lon = bbox[2] + (bbox[3] - bbox[2]) * (j + 0.5) / resolution
                    dists = np.sqrt((points.x - lon) ** 2 + (points.y - lat) ** 2)
                    idx = np.argmin(dists)
                    grid[i, j] = float(points.z[idx])

            hmin = float(grid.min())
            hmax = float(grid.max())
            if hmax - hmin > 1e-6:
                grid = (grid - hmin) / (hmax - hmin)
            return grid
        except Exception as exc:
            logger.warning("Failed to load LiDAR DEM from %s: %s", path, exc)
            return None

    def _generate_procedural_fallback(self, resolution: int) -> np.ndarray:
        from aethermap.render.webgl_exporter import _build_heightfield
        hf = _build_heightfield(resolution, 0.0, 0.04)
        hmin = float(hf.min())
        hmax = float(hf.max())
        hf = (hf - hmin) / (hmax - hmin) if hmax - hmin > 1e-06 else np.zeros_like(hf)
        return hf.astype(np.float32)


def get_dem_loader() -> DEMLoader | None:
    """Return a DEMLoader if a DEM directory or remote source is configured.

    Checks env vars:
    - AETHERMAP_DEM_DIR / AETHERMAP_DEM_PATH: local directory
    - AETHERMAP_DEM_REMOTE_URL: remote tile server base URL (Copernicus-compatible naming)
    """
    dem_dir = os.environ.get("AETHERMAP_DEM_DIR") or os.environ.get("AETHERMAP_DEM_PATH")
    remote_url = os.environ.get("AETHERMAP_DEM_REMOTE_URL")
    if dem_dir:
        return DEMLoader(dem_dir)
    if remote_url:
        return DEMLoader(Path(".cache/aethermap/dem"))
    return None
