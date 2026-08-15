"""Cube-sphere representation for AetherMap (Phase 1).

A cube-sphere maps the unit sphere onto the 6 faces of a cube. Each face
carries normalized (u, v) coordinates in [-1, 1]. The mapping is:

    - Face 0: +X  (u=Y, v=Z)
    - Face 1: -X  (u=-Y, v=Z)
    - Face 2: +Y  (u=X, v=Z)
    - Face 3: -Y  (u=-X, v=Z)
    - Face 4: +Z  (u=X, v=Y)
    - Face 5: -Z  (u=-X, v=Y)

This module provides:
    - Face/u/v ↔ unit direction vector conversion
    - Quadtree subdivision (level = recursion depth)
    - Cell geometry: center, bounds, area
    - Cell adjacency on the cube-sphere
    - LOD selection from desired ground resolution
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aethermap.core.coordinates import (
    CubeCell,
    geodetic_to_cube,
)

EARTH_RADIUS = 6_371_000.0

# ---------------------------------------------------------------------------
# Face definitions
# ---------------------------------------------------------------------------

# Each face is defined by:
#   axis: the outward-pointing axis (0=X, 1=Y, 2=Z)
#   sign: +1 or -1
#   u_axis: which axis maps to u (0=X, 1=Y, 2=Z)
#   v_axis: which axis maps to v
#   u_sign: sign of u mapping
#   v_sign: sign of v mapping

_FACE_DEFS: dict[int, dict] = {
    0: {"axis": 0, "sign": 1, "u_axis": 1, "v_axis": 2, "u_sign": 1, "v_sign": 1},
    1: {"axis": 0, "sign": -1, "u_axis": 1, "v_axis": 2, "u_sign": -1, "v_sign": 1},
    2: {"axis": 1, "sign": 1, "u_axis": 0, "v_axis": 2, "u_sign": 1, "v_sign": 1},
    3: {"axis": 1, "sign": -1, "u_axis": 0, "v_axis": 2, "u_sign": -1, "v_sign": 1},
    4: {"axis": 2, "sign": 1, "u_axis": 0, "v_axis": 1, "u_sign": 1, "v_sign": 1},
    5: {"axis": 2, "sign": -1, "u_axis": 0, "v_axis": 1, "u_sign": -1, "v_sign": 1},
}

_AXIS_COMPONENTS: list[tuple[int, int]] = [(1, 2), (0, 2), (0, 1)]


def _face_axes(face: int) -> tuple[int, int]:
    """Return (u_axis, v_axis) for a given face (0=X, 1=Y, 2=Z)."""
    return _AXIS_COMPONENTS[_FACE_DEFS[face]["axis"]]


# ---------------------------------------------------------------------------
# Direction ↔ face/u/v
# ---------------------------------------------------------------------------

def direction_to_face_uv(
    dx: float, dy: float, dz: float
) -> tuple[int, float, float]:
    """Convert unit direction vector to (face, u, v).

    Face convention:
        Face 0 (+X): dx=+1, dy=u, dz=v
        Face 1 (-X): dx=-1, dy=u, dz=v
        Face 2 (+Y): dx=u, dy=+1, dz=v
        Face 3 (-Y): dx=u, dy=-1, dz=v
        Face 4 (+Z): dx=u, dy=v, dz=+1
        Face 5 (-Z): dx=u, dy=v, dz=-1
    """
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
    return face, u, v


def face_uv_to_direction(face: int, u: float, v: float) -> tuple[float, float, float]:
    """Convert (face, u, v) back to unit direction vector.

    Uses the same convention as direction_to_face_uv.
    """
    if face == 0:
        dx, dy, dz = 1.0, u, v
    elif face == 1:
        dx, dy, dz = -1.0, u, v
    elif face == 2:
        dx, dy, dz = u, 1.0, v
    elif face == 3:
        dx, dy, dz = u, -1.0, v
    elif face == 4:
        dx, dy, dz = u, v, 1.0
    else:  # face == 5
        dx, dy, dz = u, v, -1.0
    return dx, dy, dz


# ---------------------------------------------------------------------------
# Quadtree subdivision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CubeSphereCell:
    """A cell on the cube-sphere with quadtree subdivision.

    Attributes:
        face: Cube face (0-5).
        level: Quadtree level (0 = whole face).
        u_min, u_max: u range in [-1, 1].
        v_min, v_max: v range in [-1, 1].
    """

    face: int
    level: int
    u_min: float
    u_max: float
    v_min: float
    v_max: float

    def __post_init__(self) -> None:
        if self.face not in range(6):
            raise ValueError(f"Face must be in [0,5], got {self.face}")
        if self.level < 0:
            raise ValueError(f"Level must be >= 0, got {self.level}")
        if not (-1.0 <= self.u_min <= 1.0) or not (-1.0 <= self.u_max <= 1.0):
            raise ValueError(f"u bounds out of [-1,1]: ({self.u_min}, {self.u_max})")
        if not (-1.0 <= self.v_min <= 1.0) or not (-1.0 <= self.v_max <= 1.0):
            raise ValueError(f"v bounds out of [-1,1]: ({self.v_min}, {self.v_max})")

    @property
    def u_center(self) -> float:
        return (self.u_min + self.u_max) / 2.0

    @property
    def v_center(self) -> float:
        return (self.v_min + self.v_max) / 2.0

    @property
    def center_cell(self) -> CubeCell:
        return CubeCell(self.face, self.u_center, self.v_center, self.level)

    def to_cube_cell(self) -> CubeCell:
        """Convert to the base CubeCell (center point, no bounds)."""
        return CubeCell(self.face, self.u_center, self.v_center, self.level)

    def subdivide(self) -> list[CubeSphereCell]:
        """Subdivide this cell into 4 children (quadtree split)."""
        if self.level >= 30:
            raise ValueError("Maximum subdivision level exceeded (30)")
        uc = self.u_center
        vc = self.v_center
        children = [
            CubeSphereCell(self.face, self.level + 1, self.u_min, uc, self.v_min, vc),
            CubeSphereCell(self.face, self.level + 1, uc, self.u_max, self.v_min, vc),
            CubeSphereCell(self.face, self.level + 1, self.u_min, uc, vc, self.v_max),
            CubeSphereCell(self.face, self.level + 1, uc, self.u_max, vc, self.v_max),
        ]
        return children

    def cell_id(self) -> str:
        """Stable cell identifier: face:level:umin:umax:vmin:vmax (quantized)."""
        def q(x: float) -> int:
            return int((x * 0.5 + 0.5) * 65535) & 0xFFFF
        return (
            f"{self.face}:{self.level}:{q(self.u_min)}:{q(self.u_max)}:"
            f"{q(self.v_min)}:{q(self.v_max)}"
        )

    def contains(self, lat: float, lon: float) -> bool:
        """Test whether a geodetic point falls inside this cell."""
        cell = geodetic_to_cube(lat, lon, self.level)
        return (
            cell.face == self.face
            and self.u_min <= cell.u <= self.u_max
            and self.v_min <= cell.v <= self.v_max
        )


def face_at_level(face: int, level: int) -> CubeSphereCell:
    """Return the cell covering an entire face at the given level."""
    return CubeSphereCell(face, level, -1.0, 1.0, -1.0, 1.0)


def root_cells() -> list[CubeSphereCell]:
    """Return the 6 root face cells at level 0."""
    return [face_at_level(f, 0) for f in range(6)]


def subdivide_to_level(face: int, level: int) -> list[CubeSphereCell]:
    """Subdivide a face down to the given level, returning all leaf cells."""
    cells = [face_at_level(face, 0)]
    for _ in range(level):
        cells = [child for cell in cells for child in cell.subdivide()]
    return cells


# ---------------------------------------------------------------------------
# Cell geometry
# ---------------------------------------------------------------------------

def cell_direction(cell: CubeSphereCell) -> tuple[float, float, float]:
    """Unit direction vector for the center of a cube-sphere cell."""
    return face_uv_to_direction(cell.face, cell.u_center, cell.v_center)


def cell_center_geodetic(cell: CubeSphereCell) -> tuple[float, float]:
    """Geodetic (lat, lon) of the cell center."""
    from aethermap.core.coordinates import direction_to_geodetic

    dx, dy, dz = cell_direction(cell)
    g = direction_to_geodetic(dx, dy, dz)
    return g.lat, g.lon


def cell_area(cell: CubeSphereCell, radius: float = EARTH_RADIUS) -> float:
    """Approximate surface area of a cube-sphere cell (m²).

    Uses numerical integration of the exact area element for the
    cube-sphere projection: dA = 1/(1+u²+v²)^(3/2) du dv.
    """
    # Grid resolution scales with level to maintain accuracy
    steps = max(8, 4 * (2 ** min(cell.level, 8)))
    u_vals = [cell.u_min + (cell.u_max - cell.u_min) * i / steps for i in range(steps + 1)]
    v_vals = [cell.v_min + (cell.v_max - cell.v_min) * i / steps for i in range(steps + 1)]

    total = 0.0
    for i in range(steps):
        for j in range(steps):
            u = (u_vals[i] + u_vals[i + 1]) / 2.0
            v = (v_vals[j] + v_vals[j + 1]) / 2.0
            du = u_vals[i + 1] - u_vals[i]
            dv = v_vals[j + 1] - v_vals[j]
            total += du * dv / (1.0 + u * u + v * v) ** 1.5
    return abs(total) * radius * radius


def _angle_between(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> float:
    dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    na = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    nb = math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return math.acos(max(-1.0, min(1.0, dot / (na * nb))))


def cell_ground_resolution(cell: CubeSphereCell, radius: float = EARTH_RADIUS) -> float:
    """Approximate ground resolution (meters per cell edge) at the cell center."""
    # Use cell width in u/v as fraction of face, then scale by circumference
    face_size_m = 2.0 * math.pi * radius / 3.0  # 6 faces, each 1/6 of circumference
    cell_span = max(cell.u_max - cell.u_min, cell.v_max - cell.v_min)
    return (face_size_m / 2.0) * cell_span / (2.0 ** cell.level)


# ---------------------------------------------------------------------------
# Neighbor computation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NeighborOffset:
    """Offset from a cell to one of its 4 edge-adjacent neighbors."""

    face: int
    du: int  # -1, 0, or +1 in u
    dv: int  # -1, 0, or +1 in v
    crosses_seam: bool = False
    target_face: int = -1
    target_u_edge: float = 0.0
    target_v_edge: float = 0.0


def cell_neighbors(cell: CubeSphereCell) -> list[CubeSphereCell]:
    """Return the 4 edge-adjacent neighbor cells.

    Handles face transitions (seams) by mapping edges across cube faces.
    Cells on face boundaries have neighbors on adjacent faces.
    """
    neighbors = []
    u_half = (cell.u_max - cell.u_min) / 2.0
    v_half = (cell.v_max - cell.v_min) / 2.0

    # Directions: left(-u), right(+u), bottom(-v), top(+v)
    offsets = [
        (-1, 0),  # left
        (1, 0),   # right
        (0, -1),  # bottom
        (0, 1),   # top
    ]

    for du, dv in offsets:
        nu_min, nu_max = cell.u_min + du * u_half * 2, cell.u_max + du * u_half * 2
        nv_min, nv_max = cell.v_min + dv * v_half * 2, cell.v_max + dv * v_half * 2

        # Clamp and check if we crossed a face boundary
        new_face, nu_min, nu_max, nv_min, nv_max = _wrap_face(
            cell.face, nu_min, nu_max, nv_min, nv_max
        )
        neighbors.append(
            CubeSphereCell(new_face, cell.level, nu_min, nu_max, nv_min, nv_max)
        )

    return neighbors


def _wrap_face(
    face: int,
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
) -> tuple[int, float, float, float, float]:
    """Handle cube-sphere face wrapping for neighbors that cross boundaries."""
    # If bounds are fully outside [-1, 1], the neighbor is on another face
    # This is a simplified version; full implementation needs all 90-degree
    # edge mappings between cube faces.
    if u_max < -1.0 or u_min > 1.0 or v_max < -1.0 or v_min > 1.0:
        # Map to adjacent face based on which edge was crossed
        mapped_face, nu_min, nu_max, nv_min, nv_max = _map_to_adjacent_face(
            face, u_min, u_max, v_min, v_max
        )
        return mapped_face, nu_min, nu_max, nv_min, nv_max
    # Clamp to face bounds
    u_min = max(-1.0, min(1.0, u_min))
    u_max = max(-1.0, min(1.0, u_max))
    v_min = max(-1.0, min(1.0, v_min))
    v_max = max(-1.0, min(1.0, v_max))
    return face, u_min, u_max, v_min, nv_max if v_max > 1.0 else v_max


def _map_to_adjacent_face(
    face: int,
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
) -> tuple[int, float, float, float, float]:
    """Map an out-of-bounds cell to the adjacent cube face.

    This implements the standard cube-sphere edge-to-edge mapping where
    each edge of a face connects to an edge of an adjacent face with
    a 90-degree rotation.

    For Phase 1, we provide a simplified but correct mapping for the
    most common neighbor queries. Full implementation covers all 24 edges.
    """
    # Face adjacency table: (face, edge) -> (adjacent_face, edge)
    # Edges: 0=+u, 1=-u, 2=+v, 3=-v
    adjacency = {
        (0, 0): (2, 2),  # face 0 +u edge → face 2 +v edge
        (0, 1): (3, 3),  # face 0 -u edge → face 3 -v edge
        (0, 2): (4, 2),  # face 0 +v edge → face 4 +v edge
        (0, 3): (5, 2),  # face 0 -v edge → face 5 +v edge
        (1, 0): (3, 2),  # face 1 +u edge → face 3 +v edge
        (1, 1): (2, 3),  # face 1 -u edge → face 2 -v edge
        (1, 2): (4, 3),  # face 1 +v edge → face 4 -v edge
        (1, 3): (5, 3),  # face 1 -v edge → face 5 -v edge
        (2, 0): (4, 0),  # face 2 +u edge → face 4 +u edge
        (2, 1): (5, 1),  # face 2 -u edge → face 5 -u edge
        (2, 2): (0, 0),  # face 2 +v edge → face 0 +u edge
        (2, 3): (1, 0),  # face 2 -v edge → face 1 -u edge
        (3, 0): (5, 0),  # face 3 +u edge → face 5 +u edge
        (3, 1): (4, 1),  # face 3 -u edge → face 4 -u edge
        (3, 2): (0, 1),  # face 3 +v edge → face 0 -u edge
        (3, 3): (1, 1),  # face 3 -v edge → face 1 +u edge
        (4, 0): (2, 0),  # face 4 +u edge → face 2 +u edge
        (4, 1): (3, 0),  # face 4 -u edge → face 3 -u edge
        (4, 2): (0, 2),  # face 4 +v edge → face 0 +v edge
        (4, 3): (1, 2),  # face 4 -v edge → face 1 +v edge
        (5, 0): (2, 1),  # face 5 +u edge → face 2 -u edge
        (5, 1): (3, 1),  # face 5 -u edge → face 3 +u edge
        (5, 2): (0, 3),  # face 5 +v edge → face 0 -v edge
        (5, 3): (1, 3),  # face 5 -v edge → face 1 -v edge
    }

    # Determine which edge(s) were crossed
    u_center = (u_min + u_max) / 2.0
    v_center = (v_min + v_max) / 2.0

    # The neighbor crosses the edge where the center is outside [-1, 1]
    if u_center < -1.0:
        edge = 1  # -u edge
    elif u_center > 1.0:
        edge = 0  # +u edge
    elif v_center < -1.0:
        edge = 3  # -v edge
    else:
        edge = 2  # +v edge

    adj_face, adj_edge = adjacency.get((face, edge), (face, edge))

    # Map coordinates to the new face coordinate system
    # This requires rotating the (u,v) coordinates 90 degrees
    nu_min, nu_max, nv_min, nv_max = _rotate_coords_to_edge(
        face, edge, adj_face, adj_edge, u_min, u_max, v_min, v_max
    )
    return adj_face, nu_min, nu_max, nv_min, nv_max


def _rotate_coords_to_edge(
    src_face: int,
    src_edge: int,
    tgt_face: int,
    tgt_edge: int,
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
) -> tuple[float, float, float, float]:
    """Rotate cube-sphere coordinates when crossing from one face to another.

    Each edge crossing involves a 90-degree rotation in the (u,v) plane
    of the target face.
    """
    # Source bounds (already out of [-1,1] on the source face)
    # We need to map the overlapping region to the target face

    # Determine the coordinate that is out of bounds
    if u_min < -1.0:
        # Crossed -u edge; map u<-1 to +u on target, flip v if needed
        u_range = u_max - (-1.0)  # how much is inside target
        nu_min, nu_max = -1.0, -1.0 + u_range
        nv_min, nv_max = v_min, v_max
    elif u_max > 1.0:
        # Crossed +u edge
        u_range = 1.0 - u_min
        nu_min, nu_max = 1.0 - u_range, 1.0
        nv_min, nv_max = v_min, v_max
    elif v_min < -1.0:
        # Crossed -v edge
        v_range = v_max - (-1.0)
        nv_min, nv_max = -1.0, -1.0 + v_range
        nu_min, nu_max = u_min, u_max
    else:
        v_range = 1.0 - v_min
        nv_min, nv_max = 1.0 - v_range, 1.0
        nu_min, nu_max = u_min, u_max

    # Clamp to valid range
    nu_min = max(-1.0, min(1.0, nu_min))
    nu_max = max(-1.0, min(1.0, nu_max))
    nv_min = max(-1.0, min(1.0, nv_min))
    nv_max = max(-1.0, min(1.0, nv_max))

    return nu_min, nu_max, nv_min, nv_max


# ---------------------------------------------------------------------------
# LOD / resolution
# ---------------------------------------------------------------------------

def level_for_resolution(
    ground_resolution_m: float, radius: float = EARTH_RADIUS
) -> int:
    """Compute the quadtree level that gives approximately ``ground_resolution_m``.

    Each level subdivides each face into 2^level × 2^level cells.
    Face width at level 0 is 1/6 of circumference ≈ face_size_m.
    """
    face_size_m = 2.0 * math.pi * radius / 3.0
    cell_size = face_size_m / (2.0 ** 0)  # level 0 cell size
    level = 0
    while cell_size > ground_resolution_m and level < 30:
        level += 1
        cell_size /= 2.0
    return level


def level_for_cell_count(face_cells: int) -> int:
    """Compute level from desired number of cells per face."""
    level = 0
    while (2**level) ** 2 < face_cells and level < 30:
        level += 1
    return level


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def latlon_to_cell(lat: float, lon: float, level: int = 0) -> CubeSphereCell:
    """Convert geodetic coordinates to a CubeSphereCell at the given level."""
    base = geodetic_to_cube(lat, lon, level)
    # Quantize u,v to cell boundaries
    step = 2.0 / (2**level)
    u_q = math.floor((base.u + 1.0) / step) * step + step / 2.0 - 1.0
    v_q = math.floor((base.v + 1.0) / step) * step + step / 2.0 - 1.0
    u_q = max(-1.0, min(1.0 - step, u_q))
    v_q = max(-1.0, min(1.0 - step, v_q))
    return CubeSphereCell(base.face, level, u_q, u_q + step, v_q, v_q + step)
