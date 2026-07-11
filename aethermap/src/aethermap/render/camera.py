"""Camera with orbit controls and camera-relative ECEF transform.

Implements the Fase 1 §3.1 / §6.2 contract:
- Camera origin is an ECEF point (float64).
- All vertices are translated to camera-relative (subtract origin).
- Perspective projection with configurable FOV.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Camera:
    lat: float = 41.9
    lon: float = 12.5
    alt: float = 500_000.0          # meters above surface
    distance: float = 1_000_000.0   # view distance from surface
    yaw: float = 0.0                # radians, around Y axis
    pitch: float = -0.3             # radians, up/down
    fov: float = math.radians(60.0)
    near: float = 100.0
    far: float = 10_000_000.0
    width: int = 1024
    height: int = 768

    def ecef_origin(self) -> tuple[float, float, float]:
        from aethermap.core.coordinates import geodetic_to_ecef
        e = geodetic_to_ecef(self.lat, self.lon, self.alt)
        return (e.x, e.y, e.z)

    def view_matrix(self) -> list[list[float]]:
        cx, cy, cz = self.ecef_origin()

        cy_ = math.cos(self.yaw)
        sy_ = math.sin(self.yaw)
        cp_ = math.cos(self.pitch)
        sp_ = math.sin(self.pitch)

        forward = (
            cy_ * cp_,
            sp_,
            sy_ * cp_,
        )
        up = (
            -cy_ * sp_,
            cp_,
            -sy_ * sp_,
        )
        right = (
            sy_,
            0.0,
            cy_,
        )

        # camera position in world (ECEF)
        px = cx + forward[0] * self.distance
        py = cy + forward[1] * self.distance
        pz = cz + forward[2] * self.distance

        # view matrix = lookAt(px,py,pz, cx,cy,cz, up)
        zx, zy, zz = _normalize((
            px - cx, py - cy, pz - cz
        ))
        xx, xy, xz = _normalize(_cross(up, (zx, zy, zz)))
        yx, yy, yz = _cross((zx, zy, zz), (xx, xy, xz))

        return [
            [xx, xy, xz, -xx * px - xy * py - xz * pz],
            [yx, yy, yz, -yx * px - yy * py - yz * pz],
            [zx, zy, zz, -zx * px - zy * py - zz * pz],
            [0.0, 0.0, 0.0, 1.0],
        ]

    def projection_matrix(self) -> list[list[float]]:
        aspect = self.width / max(self.height, 1)
        f = 1.0 / math.tan(self.fov / 2.0)
        nf = 1.0 / (self.near - self.far)
        return [
            [f / aspect, 0.0, 0.0, 0.0],
            [0.0, f, 0.0, 0.0],
            [0.0, 0.0, (self.far + self.near) * nf, -1.0],
            [0.0, 0.0, 2.0 * self.far * self.near * nf, 0.0],
        ]

    def mvp(self) -> list[list[float]]:
        """Model-View-Projection (identity model, camera-relative applied externally)."""
        v = self.view_matrix()
        p = self.projection_matrix()
        return _mat4_mul(p, v)


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l == 0:
        return (0.0, 0.0, 0.0)
    return (x / l, y / l, z / l)


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _mat4_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    result = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            s = 0.0
            for k in range(4):
                s += a[i][k] * b[k][j]
            result[i][j] = s
    return result


def _transform_point(m: list[list[float]], p: tuple[float, float, float]) -> tuple[float, float, float, float]:
    x, y, z = p
    w = m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3]
    return (
        (m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3]) / w,
        (m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3]) / w,
        (m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3]) / w,
        w,
    )
