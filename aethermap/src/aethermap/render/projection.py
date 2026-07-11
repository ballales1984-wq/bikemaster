from __future__ import annotations

import numpy as np

from aethermap.core.coordinates import cube_to_geodetic, geodetic_to_direction

R = 1.0


def direction_from_cube(face: int, u: float, v: float) -> np.ndarray:
    g = cube_to_geodetic(__import__("aethermap.core.coordinates", fromlist=["CubeCell"]).CubeCell(face, u, v))
    return np.array(geodetic_to_direction(g.lat, g.lon)) * R


def latlon_to_vec(lat: float, lon: float, alt: float = 0.0) -> np.ndarray:
    d = geodetic_to_direction(lat, lon)
    return np.array([d[0], d[1], d[2]]) * (R + alt / 6_371_000.0)


def cube_sphere_mesh(n: int = 10) -> list[tuple[np.ndarray, np.ndarray]]:
    segs: list[tuple[np.ndarray, np.ndarray]] = []
    for face in range(6):
        grid = np.linspace(-1.0, 1.0, n + 1)
        verts = {(i, j): direction_from_cube(face, grid[i], grid[j])
                 for i in range(n + 1) for j in range(n + 1)}
        for i in range(n + 1):
            for j in range(n + 1):
                if i + 1 <= n:
                    segs.append((verts[(i, j)], verts[(i + 1, j)]))
                if j + 1 <= n:
                    segs.append((verts[(i, j)], verts[(i, j + 1)]))
    return segs


def rotate(vec: np.ndarray, yaw: float, pitch: float) -> np.ndarray:
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    m = np.array([
        [cy, 0.0, sy],
        [0.0, 1.0, 0.0],
        [-sy, 0.0, cy],
    ]) @ np.array([
        [1.0, 0.0, 0.0],
        [0.0, cp, -sp],
        [0.0, sp, cp],
    ])
    return m @ vec


def project(vec: np.ndarray, yaw: float, pitch: float):
    r = rotate(vec, yaw, pitch)
    if r[2] <= 0.0:
        return None
    return (r[0], r[1], r[2])
