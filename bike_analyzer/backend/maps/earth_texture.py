"""Generate and cache an equirectangular earth texture for AetherMap.

Uses Natural Earth land polygons to rasterize land/ocean/ice onto a
2048x1024 PNG, cached on disk to avoid repeated work.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

_EARTH_TEXTURE_SIZE = (2048, 1024)
_EARTH_TEXTURE_CACHE = Path(
    os.environ.get("AETHERMAP_TEXTURE_CACHE", ".cache/aethermap/earth_texture.png")
)


def _load_natural_earth_land(cache_dir: Path, resolution: str = "110") -> list | None:
    """Load Natural Earth land polygons from cached GeoJSON."""
    cache_file = cache_dir / f"natural-earth-{resolution}.geojson"
    if not cache_file.exists():
        return None
    try:
        raw = cache_file.read_text(encoding="utf-8")
        geojson = json.loads(raw)
        features = geojson.get("features", [])
        land_polygons = []
        for feature in features:
            geom = feature.get("geometry", {})
            if geom.get("type") == "Polygon":
                coords = geom.get("coordinates", [])
                if coords:
                    land_polygons.append(coords[0])
            elif geom.get("type") == "MultiPolygon":
                for poly in geom.get("coordinates", []):
                    if poly and poly[0]:
                        land_polygons.append(poly[0])
        return land_polygons
    except Exception:
        return None


def ensure_natural_earth_cached(
    cache_dir: Path, resolution: str = "110"
) -> bool:
    """Best-effort download of Natural Earth land polygons if not cached.

    Returns True when a real polygon file is available (cached or just downloaded).
    Returns False if download fails (caller will fall back to procedural mask).
    """
    import urllib.request
    from urllib.error import URLError, HTTPError

    cache_file = cache_dir / f"natural-earth-{resolution}.geojson"
    if cache_file.exists() and cache_file.stat().st_size > 1024:
        return True
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        url = (
            "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
            f"ne_{resolution}m_land.geojson"
        )
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read()
        cache_file.write_bytes(data)
        return len(data) > 1024
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        logger.warning(
            "ensure_natural_earth_cached: download failed (%s); using procedural mask",
            exc,
        )
        return False


def _generate_procedural_mask(width: int, height: int) -> np.ndarray:
    """Generate a procedural land mask as fallback."""
    lats = np.linspace(90, -90, height).reshape(-1, 1).repeat(width, axis=1)
    lons = np.linspace(-180, 180, width).reshape(1, -1).repeat(height, axis=0)
    lat_rad = np.radians(lats)
    lon_rad = np.radians(lons)
    
    def _hash(x, y, seed=0xAE7E5):
        data = np.array([(x ^ seed) & 0xFFFFFFFF, (y ^ (seed >> 32)) & 0xFFFFFFFF], dtype=np.uint32)
        return (np.frombuffer(data.tobytes(), dtype=np.uint32).sum() & 0xFFFF) / 0xFFFF
    
    def _noise(x, y):
        xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
        xf, yf = x - xi, y - yi
        ux, uy = xf * xf * (3.0 - 2.0 * xf), yf * yf * (3.0 - 2.0 * yf)
        a = np.vectorize(_hash)(xi, yi)
        b = np.vectorize(_hash)(xi + 1, yi)
        c = np.vectorize(_hash)(xi, yi + 1)
        d = np.vectorize(_hash)(xi + 1, yi + 1)
        return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy
    
    def _fbm(x, y, octaves=6):
        value = np.zeros_like(x, dtype=float)
        amplitude = 0.5
        frequency = 1.0
        for _ in range(octaves):
            value += amplitude * _noise(x * frequency, y * frequency)
            frequency *= 2.0
            amplitude *= 0.5
        return value
    
    def _smooth_ellipse(lat, lon, clat, clon, rlat, rlon):
        dlat = (lat - clat) / rlat
        dlon = (lon - clon) / rlon
        d = dlat * dlat + dlon * dlon
        return 1.0 - np.clip((d - 0.7) / 0.3, 0, 1)
    
    m = np.maximum.reduce([
        _smooth_ellipse(lats, lons, 45.0, -100.0, 22.0, 28.0),
        _smooth_ellipse(lats, lons, 30.0, -90.0, 10.0, 15.0) * 0.8,
        _smooth_ellipse(lats, lons, -15.0, -55.0, 12.0, 18.0) * 0.9,
        _smooth_ellipse(lats, lons, 50.0, 10.0, 12.0, 18.0) * 0.85,
        _smooth_ellipse(lats, lons, 5.0, 20.0, 22.0, 22.0) * 0.9,
        _smooth_ellipse(lats, lons, 40.0, 80.0, 25.0, 40.0) * 0.85,
        _smooth_ellipse(lats, lons, 55.0, 100.0, 12.0, 20.0) * 0.7,
        _smooth_ellipse(lats, lons, -25.0, 135.0, 10.0, 14.0) * 0.8,
    ])
    
    polar_factor = np.maximum(0, (np.abs(lats) - 70.0) / 20.0)
    m = np.maximum(m, polar_factor)
    
    detail = _fbm(lon_rad * 8.0 + 0.5, lat_rad * 8.0 + 0.5, 5) * 0.2
    m = np.clip((m + detail - 0.45) / 0.2, 0, 1)
    
    return m > 0.5


def _rasterize_polygons(width: int, height: int, polygons: list) -> np.ndarray:
    """Rasterize polygons using PIL's ImageDraw for performance."""
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    for coords in polygons:
        if len(coords) < 3:
            continue
        points = []
        for lon, lat in coords:
            x = int((lon + 180.0) / 360.0 * width)
            y = int((90.0 - lat) / 180.0 * height)
            points.append((x, y))
        if len(points) >= 3:
            draw.polygon(points, fill=255)
    
    return np.array(mask, dtype=bool)


def generate_earth_texture(
    width: int = 2048,
    height: int = 1024,
    cache_path: Path | None = None,
) -> bytes | None:
    """Generate an equirectangular earth texture PNG.

    Returns PNG bytes, or None if generation fails.
    """
    cache_path = cache_path or _EARTH_TEXTURE_CACHE
    if cache_path.exists():
        return cache_path.read_bytes()

    try:
        cache_dir = cache_path.parent
        cache_dir.mkdir(parents=True, exist_ok=True)

        land_polygons = _load_natural_earth_land(cache_dir)
        if not land_polygons:
            ensure_natural_earth_cached(cache_dir)
            land_polygons = _load_natural_earth_land(cache_dir)
        
        ocean_deep = np.array([8, 18, 45], dtype=np.uint8)
        ocean_shallow = np.array([15, 40, 80], dtype=np.uint8)
        lowland = np.array([30, 90, 30], dtype=np.uint8)
        forest = np.array([20, 70, 20], dtype=np.uint8)
        desert = np.array([190, 170, 110], dtype=np.uint8)
        mountain = np.array([110, 95, 70], dtype=np.uint8)
        snow = np.array([230, 235, 245], dtype=np.uint8)
        ice = np.array([200, 215, 235], dtype=np.uint8)

        lats = np.linspace(90, -90, height).reshape(-1, 1).repeat(width, axis=1)
        lons = np.linspace(-180, 180, width).reshape(1, -1).repeat(height, axis=0)
        lat_rad = np.radians(lats)
        lon_rad = np.radians(lons)
        
        pixels = np.full((height, width, 3), ocean_deep, dtype=np.uint8)
        
        if land_polygons:
            land_mask = _rasterize_polygons(width, height, land_polygons)
        else:
            land_mask = _generate_procedural_mask(width, height)
        
        # Generate elevation for land areas
        def _hash_vec(x, y, seed=0xAE7E5):
            return (np.sin(x * 127.1 + seed) * 43758.5453 + np.sin(y * 311.7 + seed) * 22578.1459) % 1.0
        
        def _noise_vec(x, y):
            xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
            xf, yf = x - xi, y - yi
            ux, uy = xf * xf * (3.0 - 2.0 * xf), yf * yf * (3.0 - 2.0 * yf)
            a = _hash_vec(xi, yi)
            b = _hash_vec(xi + 1, yi)
            c = _hash_vec(xi, yi + 1)
            d = _hash_vec(xi + 1, yi + 1)
            return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy
        
        def _fbm_vec(x, y, octaves=5):
            value = np.zeros_like(x, dtype=float)
            amplitude = 0.5
            frequency = 1.0
            for _ in range(octaves):
                value += amplitude * _noise_vec(x * frequency, y * frequency)
                frequency *= 2.0
                amplitude *= 0.5
            return value
        
        land_lats = lats[land_mask]
        land_lons = lons[land_mask]
        land_lat_rad = np.radians(land_lats)
        land_lon_rad = np.radians(land_lons)
        
        n1 = _fbm_vec(land_lon_rad * 4.0, land_lat_rad * 4.0, 5)
        n2 = _fbm_vec(land_lon_rad * 8.0 + 50.0, land_lat_rad * 8.0 + 50.0, 4)
        
        lat_factor = np.abs(land_lats) / 90.0
        desert_mask = (1.0 - lat_factor) * np.maximum(0, n1 - 0.45)
        forest_mask = lat_factor * np.maximum(0, n2 - 0.4)
        
        elevation = n1 * 0.6 + n2 * 0.4
        mountain_mask = np.maximum(0, (elevation - 0.55) / 0.45)
        
        land_colors = np.tile(lowland.astype(float), (land_lats.shape[0], 1))
        land_colors = land_colors * (1 - desert_mask[:, None]) + desert * desert_mask[:, None]
        land_colors = land_colors * (1 - forest_mask[:, None] * 0.6) + forest * forest_mask[:, None] * 0.6
        land_colors = land_colors * (1 - mountain_mask[:, None]) + mountain * mountain_mask[:, None]
        snow_mask = np.maximum(0, mountain_mask - 0.5) * 2.0
        land_colors = land_colors * (1 - snow_mask[:, None]) + snow * snow_mask[:, None]
        
        pixels[land_mask] = np.clip(land_colors, 0, 255).astype(np.uint8)
        
        # Ocean colors
        ocean_n = _fbm_vec(lon_rad * 2.0, lat_rad * 2.0, 3)
        depth = np.clip((ocean_n - 0.3) / 0.7, 0, 1)
        ocean_colors = ocean_deep.astype(float).reshape(1, 1, 3) * (1 - depth[:, :, np.newaxis]) + ocean_shallow.astype(float).reshape(1, 1, 3) * depth[:, :, np.newaxis]
        ocean_mask = ~land_mask
        pixels[ocean_mask] = np.clip(ocean_colors[ocean_mask], 0, 255).astype(np.uint8)
        
        # Polar ice
        polar_factor = np.maximum(0, (np.abs(lats) - 70.0) / 20.0)
        polar_mask = polar_factor > 0
        if np.any(polar_mask):
            pixels[polar_mask] = ice

        result_img = Image.fromarray(pixels, "RGB")
        buf = io.BytesIO()
        result_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        cache_path.write_bytes(png_bytes)
        return png_bytes
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None
