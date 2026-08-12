"""Coordinate library shared by every AetherMap phase.

Design contracts (Phase 1, §6.3): a single, tested conversion layer.
No phase does hand-rolled WGS84 math. Internal key is the cube-sphere
(face, u, v); ECEF is used for physics/rendering; lat/lon/alt is I/O only.
S2 is the primary spatial key; H3 is the analysis layer.

Conversions supported:
    LatLonAlt (geodetic) ↔ ECEF (WGS84 cartesian)
    LatLonAlt → unit direction vector (on unit sphere)
    LatLonAlt ↔ CubeCell (cube-sphere face/u/v)
    ECEF ↔ unit direction
    S2 cell ID (optional, requires s2sphere)
    H3 cell index (optional, requires h3)
    Distance / bearing / interpolation utilities
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
WGS84_B = WGS84_A * (1.0 - WGS84_F)
EARTH_RADIUS_MEAN = 6_371_008.8
EARTH_RADIUS_EQ = WGS84_A
EARTH_RADIUS_POL = WGS84_B


@dataclass(frozen=True)
class Geodetic:
    """WGS84 geodetic coordinates (lat/lon in degrees, alt in meters)."""

    lat: float
    lon: float
    alt: float = 0.0

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.lon}")


@dataclass(frozen=True)
class ECEF:
    """Earth-Centered, Earth-Fixed Cartesian coordinates in meters."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class CubeCell:
    """Cube-sphere cell: face (0-5) + normalized u,v in [-1,1] + level (quadtree depth)."""

    face: int
    u: float
    v: float
    level: int = 0

    def __post_init__(self) -> None:
        if self.face not in range(6):
            raise ValueError(f"Face must be in [0,5], got {self.face}")
        if not -1.0 <= self.u <= 1.0:
            raise ValueError(f"u must be in [-1,1], got {self.u}")
        if not -1.0 <= self.v <= 1.0:
            raise ValueError(f"v must be in [-1,1], got {self.v}")
        if self.level < 0:
            raise ValueError(f"Level must be >= 0, got {self.level}")


# ---------------------------------------------------------------------------
# WGS84 ellipsoid helpers
# ---------------------------------------------------------------------------

def _n_radius(lat_r: float) -> float:
    """Prime vertical radius of curvature at geodetic latitude."""
    sin_lat = math.sin(lat_r)
    return WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)


# ---------------------------------------------------------------------------
# Geodetic ↔ ECEF
# ---------------------------------------------------------------------------

def geodetic_to_ecef(lat: float, lon: float, alt: float = 0.0) -> ECEF:
    """Convert WGS84 geodetic (lat, lon in degrees, alt in meters) to ECEF."""
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    n = _n_radius(lat_r)
    x = (n + alt) * cos_lat * math.cos(lon_r)
    y = (n + alt) * cos_lat * math.sin(lon_r)
    z = (n * (1.0 - WGS84_E2) + alt) * sin_lat
    return ECEF(x, y, z)


def ecef_to_geodetic(x: float, y: float, z: float) -> Geodetic:
    """Convert ECEF to WGS84 geodetic (lat/lon in degrees, alt in meters)."""
    lon = math.degrees(math.atan2(y, x))
    p = math.hypot(x, y)
    a = WGS84_A
    b = WGS84_B
    e2 = WGS84_E2
    ep2 = (a * a - b * b) / (b * b)
    th = math.atan2(a * z, b * p)
    lat = math.atan2(
        z + ep2 * b * math.sin(th) ** 3,
        p - e2 * a * math.cos(th) ** 3,
    )
    sin_lat = math.sin(lat)
    n = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    alt = p / math.cos(lat) - n
    return Geodetic(math.degrees(lat), lon, alt)


# ---------------------------------------------------------------------------
# Unit direction vectors (on unit sphere)
# ---------------------------------------------------------------------------

def geodetic_to_direction(lat: float, lon: float) -> tuple[float, float, float]:
    """Unit direction vector from Earth center to (lat, lon) on unit sphere."""
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    cl = math.cos(lat_r)
    return (cl * math.cos(lon_r), cl * math.sin(lon_r), math.sin(lat_r))


def geodetic_to_ecef_direction(lat: float, lon: float) -> tuple[float, float, float]:
    """Alias for geodetic_to_direction (backward compatibility with Phase 0 API)."""
    return geodetic_to_direction(lat, lon)


def direction_to_geodetic(dx: float, dy: float, dz: float) -> Geodetic:
    """Convert unit direction vector to geodetic lat/lon (alt=0)."""
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    if norm == 0.0:
        raise ValueError("Zero-length direction vector")
    nx, ny, nz = dx / norm, dy / norm, dz / norm
    lat = math.degrees(math.asin(max(-1.0, min(1.0, nz))))
    lon = math.degrees(math.atan2(ny, nx))
    return Geodetic(lat, lon, 0.0)


def ecef_to_direction(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Normalize ECEF vector to unit direction."""
    norm = math.sqrt(x * x + y * y + z * z)
    if norm == 0.0:
        raise ValueError("Zero-length ECEF vector")
    return (x / norm, y / norm, z / norm)


def ecef_to_geodetic_direction(dx: float, dy: float, dz: float) -> Geodetic:
    """Alias for direction_to_geodetic (backward compatibility)."""
    return direction_to_geodetic(dx, dy, dz)


# ---------------------------------------------------------------------------
# Cube-sphere mapping
# ---------------------------------------------------------------------------

# Face axes: which axis points outward from each face
_CUBE_FACE_AXES: dict[int, tuple[int, int, int]] = {
    0: (1, 0, 0),
    1: (-1, 0, 0),
    2: (0, 1, 0),
    3: (0, -1, 0),
    4: (0, 0, 1),
    5: (0, 0, -1),
}


def _face_for_direction(dx: float, dy: float, dz: float) -> int:
    """Select cube face from the dominant axis of a unit direction vector."""
    adx, ady, adz = abs(dx), abs(dy), abs(dz)
    if adx >= ady and adx >= adz:
        return 0 if dx > 0 else 1
    if ady >= adx and ady >= adz:
        return 2 if dy > 0 else 3
    return 4 if dz > 0 else 5


def geodetic_to_cube(lat: float, lon: float, level: int = 0) -> CubeCell:
    """Project geodetic lat/lon onto cube-sphere face/u/v.

    Uses unit sphere projection (not ellipsoid). The direction vector is
    computed from geodetic coordinates as if on a unit sphere, then mapped
    to the dominant-axis face. u,v are the remaining two components scaled
    by the dominant component, yielding values in [-1, 1].
    """
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


def cube_to_geodetic(cell: CubeCell, alt: float = 0.0) -> Geodetic:
    """Convert cube-sphere cell to geodetic lat/lon.

    Reconstructs the unit direction vector from face/u/v and converts
    to geodetic on the unit sphere (alt is returned as-is, not applied
    to the direction).
    """
    if cell.face in (0, 1):
        dx = _CUBE_FACE_AXES[cell.face][0]
        dy, dz = cell.u, cell.v
    elif cell.face in (2, 3):
        dx, dz = cell.u, cell.v
        dy = _CUBE_FACE_AXES[cell.face][1]
    else:
        dx, dy = cell.u, cell.v
        dz = _CUBE_FACE_AXES[cell.face][2]
    g = direction_to_geodetic(dx, dy, dz)
    return Geodetic(g.lat, g.lon, alt)


def direction_to_cube(dx: float, dy: float, dz: float, level: int = 0) -> CubeCell:
    """Convert unit direction vector to cube-sphere cell."""
    face = _face_for_direction(dx, dy, dz)
    adx, ady, adz = abs(dx), abs(dy), abs(dz)
    if face in (0, 1):
        s = dx if dx > 0 else -dx
        u, v = dy / s, dz / s
    elif face in (2, 3):
        s = dy if dy > 0 else -dy
        u, v = dx / s, dz / s
    else:
        s = dz if dz > 0 else -dz
        u, v = dx / s, dy / s
    return CubeCell(face, u, v, level)


def ecef_to_cube(x: float, y: float, z: float, level: int = 0) -> CubeCell:
    """Convert ECEF point to cube-sphere cell (projects onto unit sphere)."""
    dx, dy, dz = ecef_to_direction(x, y, z)
    return direction_to_cube(dx, dy, dz, level)


# ---------------------------------------------------------------------------
# Cell ID encoding
# ---------------------------------------------------------------------------

def cube_cell_id(cell: CubeCell, bits: int = 32) -> str:
    """Encode cube-sphere cell as string key.

    Format: ``face:level:u_int:v_int`` where u_int/v_int are quantized
    to ``bits``-bit unsigned integers.
    """
    face = cell.face
    scale = 2**bits
    u_int = int((cell.u * 0.5 + 0.5) * scale) & (scale - 1)
    v_int = int((cell.v * 0.5 + 0.5) * scale) & (scale - 1)
    return f"{face}:{cell.level}:{u_int}:{v_int}"


def parse_cube_cell_id(cell_id: str) -> CubeCell:
    """Decode cube-sphere cell ID string back to CubeCell."""
    parts = cell_id.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid cube cell id: {cell_id!r}")
    face = int(parts[0])
    level = int(parts[1])
    u_int = int(parts[2])
    v_int = int(parts[3])
    bits = max(u_int.bit_length(), v_int.bit_length(), 1)
    scale = 2**bits
    u = (u_int / scale) * 2.0 - 1.0
    v = (v_int / scale) * 2.0 - 1.0
    return CubeCell(face, u, v, level)


# ---------------------------------------------------------------------------
# S2 / H3 wrappers (optional dependencies)
# ---------------------------------------------------------------------------

def s2_cell_id(lat: float, lon: float, level: int = 16) -> str:
    try:
        import s2sphere  # type: ignore[import-untyped]
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
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "h3 not installed; `pip install h3` or skip analysis layer"
        ) from exc
    return str(h3.latlng_to_cell(lat, lon, resolution))


# ---------------------------------------------------------------------------
# Distance / bearing / interpolation
# ---------------------------------------------------------------------------

def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, radius: float = EARTH_RADIUS_MEAN
) -> float:
    """Great-circle distance between two geodetic points (meters)."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return radius * c


def ecef_distance(p1: ECEF, p2: ECEF) -> float:
    """Euclidean distance between two ECEF points (meters)."""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)


def geodetic_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (forward azimuth) from point 1 to point 2 (degrees)."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0


def interpolate_geodetic(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> Geodetic:
    """Interpolate along great-circle arc between two geodetic points.

    ``fraction`` is in [0, 1].
    """
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    d = (
        math.sin(lat1_r) * math.sin(lat2_r)
        + math.cos(lat1_r) * math.cos(lat2_r) * math.cos(lon2_r - lon1_r)
    )
    d = max(-1.0, min(1.0, d))
    delta = math.acos(d)
    if abs(delta) < 1e-12:
        return Geodetic(lat1, lon1)
    a = math.sin((1.0 - fraction) * delta) / math.sin(delta)
    b = math.sin(fraction * delta) / math.sin(delta)
    x = a * math.cos(lat1_r) * math.cos(lon1_r) + b * math.cos(lat2_r) * math.cos(
        lon2_r
    )
    y = a * math.cos(lat1_r) * math.sin(lon1_r) + b * math.cos(lat2_r) * math.sin(
        lon2_r
    )
    z = a * math.sin(lat1_r) + b * math.sin(lat2_r)
    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))
    return Geodetic(lat, lon)


# ---------------------------------------------------------------------------
# Ellipsoid geometry
# ---------------------------------------------------------------------------

def ellipsoid_radius_of_curvature(lat: float) -> float:
    """Radius of curvature in the prime vertical at geodetic latitude (meters)."""
    return _n_radius(math.radians(lat))


def ellipsoid_radius(lat: float) -> float:
    """Radius of the ellipsoid surface at geodetic latitude (meters).

    This is the distance from Earth center to the ellipsoid surface along
    the geodetic normal. It differs from the radius of curvature.
    """
    lat_r = math.radians(lat)
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    n = _n_radius(lat_r)
    return math.sqrt(
        (n * cos_lat) ** 2 + (n * (1.0 - WGS84_E2) * sin_lat) ** 2
    )


def ellipsoid_area() -> float:
    """Total surface area of the WGS84 ellipsoid (m²)."""
    a, b = WGS84_A, WGS84_B
    e2 = WGS84_E2
    return 2.0 * math.pi * a**2 * (1.0 + (b / a) / e2 * math.atanh(math.sqrt(e2)))
