"""Coordinate library shared by every AetherMap phase.

Design contracts (Phase 1, §6.3): a single, tested conversion layer.
No phase does hand-rolled WGS84 math. Internal key is the cube-sphere
(face, u, v); ECEF is used for physics/rendering; lat/lon/alt is I/O only.
S2 is the primary spatial key; H3 is the analysis layer (Phase 2, §10).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
EARTH_RADIUS_MEAN = 6371008.8


@dataclass
class Geodetic:
    lat: float
    lon: float
    alt: float = 0.0


@dataclass
class ECEF:
    x: float
    y: float
    z: float


@dataclass
class CubeCell:
    face: int
    u: float
    v: float
    level: int = 0


def geodetic_to_ecef(lat: float, lon: float, alt: float = 0.0) -> ECEF:
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    x = (n + alt) * cos_lat * math.cos(lon_r)
    y = (n + alt) * cos_lat * math.sin(lon_r)
    z = (n * (1.0 - WGS84_E2) + alt) * sin_lat
    return ECEF(x, y, z)


def ecef_to_geodetic(x: float, y: float, z: float) -> Geodetic:
    lon = math.degrees(math.atan2(y, x))
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1.0 - WGS84_E2))
    for _ in range(8):
        sin_lat = math.sin(lat)
        n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        alt = p / math.cos(lat) - n
        lat = math.atan2(z, p * (1.0 - WGS84_E2) * n / (n + alt))
    sin_lat = math.sin(lat)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    alt = p / math.cos(lat) - n
    return Geodetic(math.degrees(lat), lon, alt)


def geodetic_to_direction(lat: float, lon: float) -> tuple[float, float, float]:
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    cl = math.cos(lat_r)
    return (cl * math.cos(lon_r), cl * math.sin(lon_r), math.sin(lat_r))


def _cube_face_axes(face: int) -> tuple[int, int, int]:
    return {
        0: (1, 0, 0),
        1: (-1, 0, 0),
        2: (0, 1, 0),
        3: (0, -1, 0),
        4: (0, 0, 1),
        5: (0, 0, -1),
    }[face]


def geodetic_to_cube(lat: float, lon: float, level: int = 0) -> CubeCell:
    dx, dy, dz = geodetic_to_direction(lat, lon)
    adx, ady, adz = abs(dx), abs(dy), abs(dz)
    if adx >= ady and adx >= adz:
        face = 0 if dx > 0 else 1
        s = dx if dx > 0 else -dx
        u, v = dy / s, dz / s
    elif ady >= adx and ady >= adz:
        face = 2 if dy > 0 else 3
        s = dy if dy > 0 else -dy
        u, v = dx / s, dz / s
    else:
        face = 4 if dz > 0 else 5
        s = dz if dz > 0 else -dz
        u, v = dx / s, dy / s
    return CubeCell(face, u, v, level)


def cube_to_geodetic(cell: CubeCell) -> Geodetic:
    if cell.face in (0, 1):
        dx, dy, dz = _cube_face_axes(cell.face)[0], cell.u, cell.v
    elif cell.face in (2, 3):
        dx, dy, dz = cell.u, _cube_face_axes(cell.face)[1], cell.v
    else:
        dx, dy, dz = cell.u, cell.v, _cube_face_axes(cell.face)[2]
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    return ecef_to_geodetic_direction(dx / norm, dy / norm, dz / norm)


def ecef_to_geodetic_direction(dx: float, dy: float, dz: float) -> Geodetic:
    lat = math.degrees(math.asin(dz))
    lon = math.degrees(math.atan2(dy, dx))
    return Geodetic(lat, lon, 0.0)


def cube_cell_id(cell: CubeCell) -> str:
    face = cell.face
    u_int = int((cell.u * 0.5 + 0.5) * (2 ** 32))
    v_int = int((cell.v * 0.5 + 0.5) * (2 ** 32))
    return f"{face}:{cell.level}:{u_int}:{v_int}"


def s2_cell_id(lat: float, lon: float, level: int = 16) -> str:
    try:
        import s2sphere
    except ImportError as exc:
        raise RuntimeError(
            "s2sphere not installed; `pip install s2sphere` or use cube_cell_id"
        ) from exc
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    point = s2sphere.LatLng.from_radians(lat_r, lon_r)
    cell = s2sphere.CellId.from_lat_lng(point).parent(level)
    return cell.to_token()


def h3_cell(lat: float, lon: float, resolution: int = 9) -> str:
    try:
        import h3
    except ImportError as exc:
        raise RuntimeError(
            "h3 not installed; `pip install h3` or skip analysis layer"
        ) from exc
    return str(h3.latlng_to_cell(lat, lon, resolution))
