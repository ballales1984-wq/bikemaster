from __future__ import annotations

import os
import sys

from aethermap.render.projection import cube_sphere_mesh, project
from aethermap.render.scene import Scene

_HERE = os.path.dirname(__file__)


def main() -> None:
    try:
        import pygame
    except ImportError:
        print("[render] pygame non installato: usa `python -m aethermap.render.demo` (ASCII).")
        sys.exit(0)

    pygame.init()
    size = (800, 600)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("AetherMap — cube-sphere prototype")
    clock = pygame.time.Clock()
    scene = Scene.example()
    segs = cube_sphere_mesh(14)
    yaw, pitch = 0.6, 0.4
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    yaw -= 0.1
                elif ev.key == pygame.K_RIGHT:
                    yaw += 0.1
                elif ev.key == pygame.K_UP:
                    pitch -= 0.1
                elif ev.key == pygame.K_DOWN:
                    pitch += 0.1
        screen.fill((10, 12, 20))
        cx, cy = size[0] // 2, size[1] // 2
        scale = min(size) * 0.42
        for a, b in segs:
            pa, pb = project(a, yaw, pitch), project(b, yaw, pitch)
            if pa and pb:
                pygame.draw.line(screen, (60, 90, 130),
                                 (cx + pa[0] * scale, cy - pa[1] * scale),
                                 (cx + pb[0] * scale, cy - pb[1] * scale), 1)
        for ent in scene.entities:
            col = {"S": (80, 200, 120), "T": (120, 220, 90), "M": (200, 170, 90)}.get(ent["char"], (220, 220, 220))
            for pt in ent["pts"]:
                p = project(__import__("numpy").array(pt), yaw, pitch)
                if p:
                    pygame.draw.circle(screen, col, (cx + p[0] * scale, cy - p[1] * scale), 4)
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()


if __name__ == "__main__":
    main()
