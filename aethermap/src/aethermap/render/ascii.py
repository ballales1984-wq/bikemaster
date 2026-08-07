from __future__ import annotations

import numpy as np

from aethermap.render.camera import Camera
from aethermap.render.projection import cube_sphere_mesh, project_ecef
from aethermap.render.scene import Scene


def render_ascii(scene: Scene, camera: Camera | None = None,
                  w: int = 70, h: int = 35, mesh_n: int = 8) -> str:
    if camera is None:
        camera = Camera()
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
            p = project_ecef(a + (b - a) * t, camera)
            if p:
                plot(p[0], p[1], ".")
    _char_map = {"strada": "S", "albero": "A", "montagna": "M"}
    for ent in scene.entities:
        ch = _char_map.get(ent.tipo, ent.tipo[0].upper() if ent.tipo else "?")
        if ent.kind == "line":
            pts = ent.points
        elif ent.position is not None:
            pts = [ent.position]
        else:
            pts = []
        for pt in pts:
            p = project_ecef(pt, camera)
            if p:
                plot(p[0], p[1], ch)
    return "\n".join("".join(row) for row in grid)
