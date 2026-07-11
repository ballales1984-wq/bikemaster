from __future__ import annotations

import numpy as np

from aethermap.render.projection import cube_sphere_mesh, project
from aethermap.render.scene import Scene


def render_ascii(scene: Scene, yaw: float = 0.6, pitch: float = 0.4,
                 w: int = 70, h: int = 35, mesh_n: int = 8) -> str:
    grid = [[" " for _ in range(w)] for _ in range(h)]
    segs = cube_sphere_mesh(mesh_n)

    def plot(x: float, y: float, ch: str) -> None:
        cx = int((x * 0.5 + 0.5) * (w - 1))
        cy = int((0.5 - y * 0.5) * (h - 1))
        if 0 <= cx < w and 0 <= cy < h:
            grid[cy][cx] = ch

    for a, b in segs:
        steps = 4
        for k in range(steps + 1):
            t = k / steps
            p = project(a + (b - a) * t, yaw, pitch)
            if p:
                plot(p[0], p[1], ".")
    for ent in scene.entities:
        ch = ent["char"]
        for pt in ent["pts"]:
            p = project(np.array(pt), yaw, pitch)
            if p:
                plot(p[0], p[1], ch)
    return "\n".join("".join(row) for row in grid)
