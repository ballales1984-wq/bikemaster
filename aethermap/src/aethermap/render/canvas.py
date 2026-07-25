"""AetherMap Fase 4 — Canvas 2D renderer (fallback when WebGL is unavailable).

Renders the cube-sphere globe and entities on an HTML5 Canvas using 2D
context. Useful for environments without WebGL2 support or for quick
debugging without GPU.
"""
from __future__ import annotations

import json
import math
from typing import Any

import numpy as np

from aethermap.render.camera import Camera
from aethermap.render.projection import cube_sphere_mesh, project_ecef
from aethermap.render.scene import Entity, Scene


def render_canvas(
    scene: Scene,
    camera: Camera | None = None,
    width: int = 800,
    height: int = 600,
    bg: tuple[int, int, int] = (10, 12, 20),
    globe_color: tuple[int, int, int] = (60, 90, 130),
    grid: bool = False,
) -> str:
    """Render the scene to an SVG string.

    Falls back to 2D projection when WebGL is not available.
    """
    if camera is None:
        camera = Camera()

    cx, cy = width // 2, height // 2
    scale = min(width, height) * 0.42
    segs = cube_sphere_mesh(12)

    lines_svg: list[str] = []
    for a, b in segs:
        pa = project_ecef(a, camera)
        pb = project_ecef(b, camera)
        if pa and pb:
            x1 = cx + pa[0] * scale
            y1 = cy - pa[1] * scale
            x2 = cx + pb[0] * scale
            y2 = cy - pb[1] * scale
            lines_svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                            f'stroke="rgb({globe_color[0]},{globe_color[1]},{globe_color[2]})" '
                            f'stroke-width="1" stroke-opacity="0.6"/>')

    entity_svg: list[str] = []
    color_map = {
        "strada": (242, 199, 56),
        "albero": (71, 235, 107),
        "montagna": (235, 82, 71),
        "sensore_traffico": (77, 179, 255),
        "edificio": (179, 179, 179),
        "via": (204, 191, 153),
    }

    for ent in scene.entities:
        col = color_map.get(ent.tipo, (204, 204, 204))
        rgb = f"rgb({col[0]},{col[1]},{col[2]})"

        if ent.kind == "line":
            pts = []
            for p in ent.points:
                ndc = project_ecef(p, camera)
                if ndc is None:
                    continue
                px = cx + ndc[0] * scale
                py = cy - ndc[1] * scale
                pts.append(f"{px:.1f},{py:.1f}")
            if len(pts) >= 2:
                entity_svg.append(f'<polyline points="{" ".join(pts)}" '
                                 f'stroke="{rgb}" stroke-width="2" fill="none" stroke-opacity="0.9"/>')
        elif ent.position is not None:
            ndc = project_ecef(ent.position, camera)
            if ndc is None:
                continue
            px = cx + ndc[0] * scale
            py = cy - ndc[1] * scale
            r = max(3, min(8, ent.radius * scale * 0.02))
            entity_svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                             f'fill="{rgb}" fill-opacity="0.85" stroke="#fff" stroke-width="1"/>')

    grid_svg: list[str] = []
    if grid:
        step = 15
        for lat in range(-90 + step, 90, step):
            pts = []
            for lon in range(-180, 181, 2):
                v = np.array([math.cos(math.radians(lat)) * math.cos(math.radians(lon)),
                              math.cos(math.radians(lat)) * math.sin(math.radians(lon)),
                              math.sin(math.radians(lat))], dtype=np.float64) * 6371000.0
                ndc = project_ecef(v, camera)
                if ndc is None:
                    pts.clear()
                    continue
                pts.append(f"{cx + ndc[0] * scale:.1f},{cy - ndc[1] * scale:.1f}")
            if len(pts) >= 2:
                grid_svg.append(f'<polyline points="{" ".join(pts)}" '
                               f'stroke="rgba(127,255,221,0.12)" stroke-width="1" fill="none"/>')
        for lon in range(-180 + step, 180, step):
            pts = []
            for lat in range(-90, 91, 2):
                v = np.array([math.cos(math.radians(lat)) * math.cos(math.radians(lon)),
                              math.cos(math.radians(lat)) * math.sin(math.radians(lon)),
                              math.sin(math.radians(lat))], dtype=np.float64) * 6371000.0
                ndc = project_ecef(v, camera)
                if ndc is None:
                    pts.clear()
                    continue
                pts.append(f"{cx + ndc[0] * scale:.1f},{cy - ndc[1] * scale:.1f}")
            if len(pts) >= 2:
                grid_svg.append(f'<polyline points="{" ".join(pts)}" '
                               f'stroke="rgba(127,255,221,0.12)" stroke-width="1" fill="none"/>')

    bg_hex = f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}"

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="{bg_hex}"/>
  <g id="grid">
    {"".join(grid_svg)}
  </g>
  <g id="globe">
    {"".join(lines_svg)}
  </g>
  <g id="entities">
    {"".join(entity_svg)}
  </g>
</svg>"""
    return svg


def render_canvas_html(
    scene: Scene,
    camera: Camera | None = None,
    width: int = 800,
    height: int = 600,
) -> str:
    """Return a standalone HTML document with an inline SVG render."""
    svg = render_canvas(scene, camera, width, height)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>AetherMap — Canvas 2D fallback</title>
<style>
  html,body{{margin:0;height:100%;background:#0a0c14;overflow:hidden;font-family:monospace}}
  svg{{display:block;width:100vw;height:100vh}}
  #hud{{position:fixed;left:10px;top:10px;color:#7fd;font-size:12px;line-height:1.5;
       background:rgba(0,0,0,.35);padding:8px 10px;border-radius:6px;z-index:2}}
  #hud b{{color:#fff}}
</style>
</head>
<body>
  {svg}
  <div id="hud">
    <b>AetherMap</b> — Canvas 2D fallback<br />
    entities: {len(scene.entities)}
  </div>
</body>
</html>"""


def main() -> None:
    scene = Scene.example()
    camera = Camera()
    svg = render_canvas(scene, camera)
    out = "/tmp/aethermap_canvas.svg"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"[canvas] SVG salvato in {out}")

    html = render_canvas_html(scene, camera)
    out_html = "/tmp/aethermap_canvas.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[canvas] HTML salvato in {out_html}")


if __name__ == "__main__":
    main()
