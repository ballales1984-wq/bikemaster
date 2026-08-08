"""Terrain heightfield provider for AetherMap.

Falls back to procedural FBM when real DEM data is unavailable or the request
fails. Real DEM uses Copernicus/SRTM via the ``elevation`` package, with a
local disk cache to avoid repeated downloads.
"""

from __future__ import annotations

import math
import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_EARTH_RADIUS_M = 6_371_000.0
_TILE_SIZE = 64
_SEED = 0xAE7E5
_DEM_CACHE_DIR = Path(os.environ.get("AETHERMAP_DEM_CACHE", ".cache/aethermap/dem"))
_DEM_SOURCE = os.environ.get("AETHERMAP_DEM_SOURCE", "auto")


def _hash(x: int, y: int, seed: int = _SEED) -> float:
    data = struct.pack(">II", (x ^ seed) & 0xFFFFFFFF, (y ^ (seed >> 32)) & 0xFFFFFFFF)
    return (zlib.crc32(data) & 0xFFFF) / 0xFFFF


def _smooth(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _noise(x: float, y: float) -> float:
    xi, yi = int(math.floor(x)), int(math.floor(y))
    xf, yf = x - xi, y - yi
    ux, uy = _smooth(xf), _smooth(yf)
    a = _hash(xi, yi)
    b = _hash(xi + 1, yi)
    c = _hash(xi, yi + 1)
    d = _hash(xi + 1, yi + 1)
    return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy


def _fbm(x: float, y: float, octaves: int = 6) -> float:
    value = 0.0
    amplitude = 0.5
    frequency = 1.0
    for _ in range(octaves):
        value += amplitude * _noise(x * frequency, y * frequency)
        frequency *= 2.0
        amplitude *= 0.5
    return value


def _continent_mask(lat: float, lon: float) -> float:
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    n = _fbm(lon_rad * 3.0, lat_rad * 3.0, 6)
    n2 = _fbm(lon_rad * 7.0 + 100.0, lat_rad * 7.0 + 100.0, 4)
    mask = n * 0.7 + n2 * 0.3
    threshold = 0.48 + 0.08 * math.sin(lat_rad * 2.0)
    if mask > threshold:
        detail = _fbm(lon_rad * 15.0, lat_rad * 15.0, 4)
        elevation = (mask - threshold) / (1.0 - threshold)
        elevation = elevation * 0.7 + detail * 0.3
        if lat_rad > 1.2:
            elevation *= max(0.0, 1.0 - (lat_rad - 1.2) / 0.4)
        return max(0.0, elevation) * 4000.0
    return 0.0


def _generate_procedural_heightfield(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    resolution: int = _TILE_SIZE,
) -> np.ndarray:
    lat = np.linspace(max_lat, min_lat, resolution)
    lon = np.linspace(min_lon, max_lon, resolution)
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    vfunc = np.vectorize(_continent_mask)
    return vfunc(lat_grid, lon_grid).astype(np.float32)


def _try_fetch_dem_tile(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    resolution: int,
) -> np.ndarray | None:
    try:
        import elevation
    except ImportError:
        return None

    _DEM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tile_name = f"dem_{min_lat:.2f}_{max_lat:.2f}_{min_lon:.2f}_{max_lon:.2f}_{resolution}.npy"
    cache_path = _DEM_CACHE_DIR / tile_name

    if cache_path.exists():
        try:
            return np.load(cache_path).astype(np.float32)
        except Exception:
            cache_path.unlink(missing_ok=True)

    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            elevation.clip(
                bounds=(min_lon, min_lat, max_lon, max_lat),
                product="SRTM1",
                cache_dir=tmpdir,
            )
            import rasterio
            dem_files = list(Path(tmpdir).rglob("*.tif"))
            if not dem_files:
                return None
            with rasterio.open(dem_files[0]) as src:
                data = src.read(1).astype(np.float32)
                if data.size == 0:
                    return None
                from scipy.ndimage import zoom
                zoom_factor = (resolution / data.shape[0], resolution / data.shape[1])
                resized = zoom(data, zoom_factor, order=1)
                if resized.shape != (resolution, resolution):
                    resized = resized[:resolution, :resolution]
                np.save(cache_path, resized)
                return resized
    except Exception:
        return None


def generate_heightfield(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    resolution: int = _TILE_SIZE,
    source: str = _DEM_SOURCE,
) -> np.ndarray:
    if source in ("auto", "dem"):
        dem = _try_fetch_dem_tile(min_lat, max_lat, min_lon, max_lon, resolution)
        if dem is not None:
            return dem
    return _generate_procedural_heightfield(min_lat, max_lat, min_lon, max_lon, resolution)


@dataclass
class TerrainTile:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    resolution: int
    heights: np.ndarray
    source: str = "procedural"

    def to_dict(self) -> dict:
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "resolution": self.resolution,
            "source": self.source,
            "heights": self.heights.flatten().tolist(),
        }


def get_tile(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    resolution: int = _TILE_SIZE,
    source: str = _DEM_SOURCE,
) -> TerrainTile:
    dem = None
    tile_source = "procedural"

    if source in ("auto", "dem"):
        dem = _try_fetch_dem_tile(min_lat, max_lat, min_lon, max_lon, resolution)
        if dem is not None:
            tile_source = "dem"

    if dem is None and source in ("auto", "copernicus", "lidar", "osm"):
        try:
            from aethermap.data.dem_loader import get_dem_loader
            loader = get_dem_loader()
            if loader is not None:
                real_dem = loader.load((min_lat, max_lat, min_lon, max_lon), resolution)
                if real_dem is not None and np.mean(np.abs(real_dem)) > 1e-6:
                    dem = real_dem
                    tile_source = f"dem:{source}"
        except Exception:
            pass

    if dem is None:
        dem = _generate_procedural_heightfield(min_lat, max_lat, min_lon, max_lon, resolution)

    return TerrainTile(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        resolution=resolution,
        heights=dem,
        source=tile_source,
    )
