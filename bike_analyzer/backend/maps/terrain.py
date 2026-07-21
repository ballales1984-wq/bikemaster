"""Procedural terrain generation for AetherMap.

Generates heightfield tiles for the cube-sphere globe using fractal noise.
No external dependencies beyond numpy (already used by the project).
"""

from __future__ import annotations

import hashlib
import math
import struct
import zlib
from dataclasses import dataclass
from typing import Sequence

import numpy as np

_EARTH_RADIUS_M = 6_371_000.0
_TILE_SIZE = 64
_SEED = 0xAE7E5


def _hash(x: int, y: int, seed: int = _SEED) -> float:
    data = struct.pack(">II", x ^ seed, y ^ (seed >> 32))
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


def generate_heightfield(
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


@dataclass
class TerrainTile:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    resolution: int
    heights: np.ndarray

    def to_dict(self) -> dict:
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "resolution": self.resolution,
            "heights": self.heights.flatten().tolist(),
        }


def get_tile(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    resolution: int = _TILE_SIZE,
) -> TerrainTile:
    heights = generate_heightfield(min_lat, max_lat, min_lon, max_lon, resolution)
    return TerrainTile(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        resolution=resolution,
        heights=heights,
    )
