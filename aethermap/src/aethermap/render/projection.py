from __future__ import annotations

import numpy as np

from aethermap.core.coordinates import (
    CubeCell,
    cube_to_geodetic,
    geodetic_to_direction,
)
from aethermap.render.camera import Camera

# Scala reale: raggio Terra in metri. A questa scala le coordinate ECEF
# valgono ~6.37e6 m -> in float32 la precisione e' ~0.5-1 m (persa).
# Per questo serve la camera-relative (vedi Fase 1 §3.1 / §6.2):
# sottrai l'origine della camera cosi' le coordinate restano O(1e3) m.
R = 6_371_000.0


def direction_from_cube(face: int, u: float, v: float) -> np.ndarray:
    g = cube_to_geodetic(CubeCell(face, u, v), alt=0.0)
    return np.array(geodetic_to_direction(g.lat, g.lon)) * R


def latlon_to_vec(lat: float, lon: float, alt: float = 0.0) -> np.ndarray:
    d = geodetic_to_direction(lat, lon)
    return np.array([d[0], d[1], d[2]], dtype=np.float64) * (R + alt)


def cube_sphere_mesh(n: int = 10) -> list[tuple[np.ndarray, np.ndarray]]:
    segs: list[tuple[np.ndarray, np.ndarray]] = []
    for face in range(6):
        grid = np.linspace(-1.0, 1.0, n + 1)
        verts = {
            (i, j): direction_from_cube(face, grid[i], grid[j])
            for i in range(n + 1) for j in range(n + 1)
        }
        for i in range(n + 1):
            for j in range(n + 1):
                if i + 1 <= n:
                    segs.append((verts[(i, j)], verts[(i + 1, j)]))
                if j + 1 <= n:
                    segs.append((verts[(i, j)], verts[(i, j + 1)]))
    return segs


def project_ecef(vec, camera: Camera):
    """Proiezione camera-relative (precisione float32 sicura).

    1) sottrai l'origine ECEF della camera: coordinate da ~6.37e6 m
       diventano O(1e3) m (camera-relative);
    2) applichi MVP (view + projection prospettica della camera);
    3) dividi per w (perspective divide) -> NDC in [-1,1].
    """
    ox, oy, oz = camera.ecef_origin()
    rel = np.array([vec[0] - ox, vec[1] - oy, vec[2] - oz, 1.0], dtype=np.float64)
    mvp = np.array(camera.mvp(), dtype=np.float64)
    clip = mvp @ rel
    if clip[3] <= 0.0:
        return None
    return (clip[0] / clip[3], clip[1] / clip[3], clip[2] / clip[3])
