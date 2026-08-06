"""AetherMap Fase 4 — terrain heightfield enhancer.

Fetches real DEM tiles from a BikeMaster backend and applies them to the
cube-sphere mesh, falling back to procedural FBM when unavailable.
"""
from __future__ import annotations

import numpy as np

from aethermap.core.coordinates import ecef_to_geodetic

_EARTH_R = 6_371_000.0
_DEM_API = "/aethermap/terrain"


def _face_direction(face: int, u: float, v: float) -> np.ndarray:
    if face == 0:
        d = np.array([1.0, u, v])
    elif face == 1:
        d = np.array([-1.0, u, v])
    elif face == 2:
        d = np.array([u, 1.0, v])
    elif face == 3:
        d = np.array([u, -1.0, v])
    elif face == 4:
        d = np.array([u, v, 1.0])
    else:
        d = np.array([u, v, -1.0])
    return d / np.linalg.norm(d)


def _face_bbox(face: int, n: int = 64) -> dict[str, float]:
    corners = []
    for i in (0, n - 1):
        for j in (0, n - 1):
            u = (i / (n - 1)) * 2.0 - 1.0
            v = (j / (n - 1)) * 2.0 - 1.0
            d = _face_direction(face, u, v)
            g = ecef_to_geodetic(d[0], d[1], d[2])
            corners.append((g.lat, g.lon))
    lats = [c[0] for c in corners]
    lons = [c[1] for c in corners]
    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lon": min(lons),
        "max_lon": max(lons),
        "center_lat": sum(lats) / len(lats),
        "center_lon": sum(lons) / len(lons),
    }


def fetch_dem_tile(
    bbox: dict[str, float],
    resolution: int = 64,
    base_url: str = "http://localhost:8000",
    source: str = "auto",
) -> np.ndarray | None:
    try:
        import json
        import urllib.request

        qs = (
            f"?min_lat={bbox['min_lat']:.4f}&max_lat={bbox['max_lat']:.4f}"
            f"&min_lon={bbox['min_lon']:.4f}&max_lon={bbox['max_lon']:.4f}"
            f"&resolution={resolution}&source={source}"
        )
        url = f"{base_url}{_DEM_API}{qs}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        payload = json.loads(data)
        heights = np.array(payload["heights"], dtype=np.float32)
        return heights.reshape((resolution, resolution))
    except Exception:
        return None


def enhance_face(
    hf: np.ndarray,
    face: int,
    base_url: str = "http://localhost:8000",
    resolution: int = 64,
) -> np.ndarray:
    bbox = _face_bbox(face, resolution)
    dem = fetch_dem_tile(bbox, resolution, base_url)
    if dem is None:
        return hf
    dem_min, dem_max = float(dem.min()), float(dem.max())
    dem_range = max(dem_max - dem_min, 1.0)
    hf_min, hf_max = float(hf.min()), float(hf.max())
    hf_range = max(hf_max - hf_min, 1e-6)
    hf_scaled = (dem - dem_min) / dem_range * hf_range + hf_min
    return hf_scaled.astype(np.float32)


def build_enhanced_heightfield(
    n: int = 64,
    base_alt: float = 0.0,
    height_scale: float = 0.04,
    base_url: str = "http://localhost:8000",
    faces: tuple[int, ...] = (0, 1, 4, 5),
) -> np.ndarray:
    from aethermap.render.webgl_exporter import _build_heightfield

    hf = np.zeros((6, n, n), dtype=np.float32)
    for face in range(6):
        hf[face] = _build_heightfield(n, base_alt, height_scale).astype(np.float32)
    if not base_url:
        return hf.flatten()
    for face in faces:
        face_hf = hf[face]
        enhanced = enhance_face(face_hf, face, base_url, n)
        hf[face] = enhanced
    return hf.flatten()


def get_terrain_bboxes(n: int = 64) -> dict[int, dict[str, float]]:
    return {face: _face_bbox(face, n) for face in range(6)}
