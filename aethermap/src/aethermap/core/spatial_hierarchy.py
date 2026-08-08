"""Spatial hierarchy operations for S2 and H3 (Phase 1).

Provides tree traversal, region covering, and cross-system mapping
between S2, H3, and the cube-sphere representation.

S2 hierarchy:
    - Cells cover the unit sphere in a quad-tree (faces → cells → children)
    - Level 0 = 6 root cells, level 30 = ~4 billion cells
    - Cell IDs are 64-bit integers or base-16 tokens

H3 hierarchy:
    - Cells cover the sphere as hexagons (plus 12 pentagons at vertices)
    - Resolutions 0-15, each ~7x more cells than previous
    - Cell IDs are 64-bit integers or base-16 strings

Design principle (§6.3): the conversion library is the single authority
for all spatial key operations.
"""

from __future__ import annotations

import math
from typing import Optional


# ---------------------------------------------------------------------------
# S2 hierarchy operations
# ---------------------------------------------------------------------------

def s2_level_from_token(token: str) -> int:
    """Extract the level from an S2 cell token."""
    # S2 tokens are variable-length; length determines level
    # Level 0 = 2 chars, each additional 2 chars = +1 level
    return max(0, len(token) // 2 - 1)


def s2_parent(token: str) -> Optional[str]:
    """Return the parent S2 cell token, or None if already at level 0."""
    if len(token) <= 2:
        return None
    return token[:-2]


def s2_children(token: str) -> list[str]:
    """Return the 4 child S2 cell tokens."""
    return [token + suffix for suffix in ("0", "1", "2", "3")]


def s2_is_ancestor(ancestor: str, descendant: str) -> bool:
    """Check if ``ancestor`` is a prefix of ``descendant`` in S2 token space."""
    return descendant.startswith(ancestor) and len(descendant) > len(ancestor)


def s2_is_valid_token(token: str) -> bool:
    """Basic validation: non-empty, even length, hex characters."""
    if not token or len(token) < 2 or len(token) % 2 != 0:
        return False
    try:
        int(token, 16)
        return True
    except ValueError:
        return False


def s2_token_to_latlon(token: str) -> tuple[float, float]:
    """Decode an S2 token to (lat, lon) center point."""
    try:
        import s2sphere  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("s2sphere required for S2 token decoding") from exc
    cell = s2sphere.CellId.from_token(token)
    latlng = s2sphere.LatLng.from_point(cell.to_point())
    return math.degrees(latlng.lat().radians), math.degrees(latlng.lng().radians)


def s2_latlon_to_token(lat: float, lon: float, level: int = 16) -> str:
    """Encode a geodetic point as an S2 cell token at the given level."""
    try:
        import s2sphere  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("s2sphere required for S2 token encoding") from exc
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    point = s2sphere.LatLng.from_radians(lat_r, lon_r)
    cell = s2sphere.CellId.from_lat_lng(point).parent(level)
    return cell.to_token()


def s2_region_cover(
    lat: float, lon: float, radius_m: float, max_level: int = 16
) -> list[str]:
    """Cover a circular region with S2 cells.

    Returns a list of S2 cell tokens at varying levels that cover
    the circle of ``radius_m`` around ``(lat, lon)``.
    """
    try:
        import s2sphere  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("s2sphere required for S2 region covering") from exc

    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    center = s2sphere.LatLng.from_radians(lat_r, lon_r)
    center_point = center.to_point()

    radius_rad = radius_m / 6_371_000.0
    cap = s2sphere.Cap(center_point, s2sphere.Angle.from_radians(radius_rad))

    coverer = s2sphere.RegionCoverer()
    coverer.max_level = max_level
    coverer.min_level = 0
    coverer.max_cells = 100

    covering = coverer.get_covering(cap)
    return [cell.to_token() for cell in covering]


def s2_to_cube_sphere(token: str) -> Optional[tuple[int, float, float]]:
    """Map an S2 cell token to cube-sphere (face, u, v) at the cell center."""
    try:
        import s2sphere  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("s2sphere required for S2→cube mapping") from exc

    cell = s2sphere.CellId.from_token(token)
    point = cell.to_point()
    x, y, z = point[0], point[1], point[2]

    # Determine face
    adx, ady, adz = abs(x), abs(y), abs(z)
    if adx >= ady and adx >= adz:
        face = 0 if x > 0 else 1
        s = x if x > 0 else -x
        u, v = y / s, z / s
    elif ady >= adx and ady >= adz:
        face = 2 if y > 0 else 3
        s = y if y > 0 else -y
        u, v = x / s, z / s
    else:
        face = 4 if z > 0 else 5
        s = z if z > 0 else -z
        u, v = x / s, y / s
    return face, u, v


# ---------------------------------------------------------------------------
# H3 hierarchy operations
# ---------------------------------------------------------------------------

def h3_level_from_index(h3_index: str) -> int:
    """Extract H3 resolution from cell index string."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 level extraction") from exc
    return h3.get_resolution(h3_index)


def h3_parent(h3_index: str) -> Optional[str]:
    """Return the parent H3 cell, or None if at resolution 0."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 parent operation") from exc
    res = h3.get_resolution(h3_index)
    if res == 0:
        return None
    return h3.cell_to_parent(h3_index)


def h3_children(h3_index: str) -> list[str]:
    """Return the 7 child H3 cells (hexagons)."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 children operation") from exc
    return list(h3.cell_to_children(h3_index))


def h3_is_ancestor(ancestor: str, descendant: str) -> bool:
    """Check if ``ancestor`` is a parent of ``descendant`` in H3 hierarchy."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 ancestry check") from exc
    try:
        return h3.cell_to_parent(descendant, h3.get_resolution(ancestor)) == ancestor
    except Exception:
        return False


def h3_is_valid_index(h3_index: str) -> bool:
    """Validate an H3 index string."""
    try:
        import h3  # type: ignore[import-untyped]
        return h3.is_valid_cell(h3_index)
    except ImportError:
        return False


def h3_index_to_latlon(h3_index: str) -> tuple[float, float]:
    """Decode H3 cell center to (lat, lon)."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3→latlon decoding") from exc
    return h3.cell_to_latlng(h3_index)


def h3_latlon_to_index(lat: float, lon: float, resolution: int = 9) -> str:
    """Encode geodetic point as H3 cell at given resolution."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 encoding") from exc
    return h3.latlng_to_cell(lat, lon, resolution)


def h3_region_cover(
    lat: float, lon: float, radius_m: float, resolution: int = 9
) -> list[str]:
    """Cover a circular region with H3 hexagons at the given resolution."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 region covering") from exc

    km = radius_m / 1000.0
    radius_deg = km / 111.0

    center = h3.latlng_to_cell(lat, lon, resolution)
    k = max(1, int(radius_deg * 10))
    k = min(k, 100)
    cells = set([center])
    for _ in range(k):
        new_cells = set()
        for c in cells:
            new_cells.update(h3.grid_ring(c, 1))
        cells.update(new_cells)
    return list(cells)


def h3_compact(indices: list[str]) -> list[str]:
    """Compact a list of H3 cells by merging children into parents where possible."""
    try:
        import h3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("h3 required for H3 compaction") from exc
    return list(h3.compact_cells(indices))


# ---------------------------------------------------------------------------
# Cross-system mapping
# ---------------------------------------------------------------------------

def s2_level_to_h3_resolution(s2_level: int) -> int:
    """Map S2 level to approximately equivalent H3 resolution.

    S2 level 16 (~4.5m) ≈ H3 resolution 10 (~0.5km).
    This is a rough mapping for interoperability.
    """
    mapping = {0: 1, 2: 2, 4: 3, 6: 4, 8: 5, 10: 6, 12: 7, 14: 8, 16: 10}
    return mapping.get(s2_level, max(0, s2_level // 2))


def h3_resolution_to_s2_level(h3_res: int) -> int:
    """Map H3 resolution to approximately equivalent S2 level."""
    mapping = {1: 0, 2: 2, 3: 4, 4: 6, 5: 8, 6: 10, 7: 12, 8: 14, 10: 16}
    return mapping.get(h3_res, h3_res * 2)


def cube_cell_id_to_s2(cell_id: str) -> Optional[str]:
    """Map a cube-sphere cell ID to an S2 token (approximate)."""
    try:
        import s2sphere  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("s2sphere required for cube→S2 mapping") from exc

    parts = cell_id.split(":")
    if len(parts) != 4:
        return None
    face, level, u_int, v_int = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    scale = 2**32
    u = (u_int / scale) * 2.0 - 1.0
    v = (v_int / scale) * 2.0 - 1.0
    dx, dy, dz = _cube_uv_to_direction(face, u, v)
    lat = math.degrees(math.asin(max(-1.0, min(1.0, dz))))
    lon = math.degrees(math.atan2(dy, dx))
    return s2_latlon_to_token(lat, lon, level)


def _cube_uv_to_direction(face: int, u: float, v: float) -> tuple[float, float, float]:
    """Convert cube-sphere (face, u, v) to unit direction vector."""
    if face in (0, 1):
        dx = 1.0 if face == 0 else -1.0
        dy, dz = u, v
    elif face in (2, 3):
        dx, dz = u, v
        dy = 1.0 if face == 2 else -1.0
    else:
        dx, dy = u, v
        dz = 1.0 if face == 4 else -1.0
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    return dx / norm, dy / norm, dz / norm
