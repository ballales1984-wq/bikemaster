from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from aethermap.render.camera import Camera
from aethermap.render.projection import latlon_to_vec, project_ecef


@dataclass
class Entity:
    tipo: str
    position: np.ndarray | None = None
    color: list[float] = field(default_factory=lambda: [0.8, 0.8, 0.8])
    kind: str = "point"
    points: list[np.ndarray] = field(default_factory=list)
    props: dict[str, Any] = field(default_factory=dict)
    s2: str | None = None
    radius: float = 1.0

    @classmethod
    def from_gl(cls, data: dict[str, Any]) -> Entity:
        ent = cls(
            tipo=data.get("tipo", "unknown"),
            color=data.get("color", [0.8, 0.8, 0.8]),
            kind=data.get("kind", "point"),
            props=data.get("props", {}),
            s2=data.get("s2"),
            radius=data.get("radius", 1.0),
        )
        if ent.kind == "line" and "points" in data:
            ent.points = [np.array(p, dtype=np.float64) for p in data["points"]]
        elif "position" in data:
            ent.position = np.array(data["position"], dtype=np.float64)
        return ent


class Scene:
    def __init__(self) -> None:
        self.entities: list[Entity] = []

    def add(self, entity: Entity) -> None:
        self.entities.append(entity)

    def load_from_world_data(self, data: dict[str, Any]) -> None:
        self.entities = [Entity.from_gl(e) for e in data.get("entities", [])]

    def visible(self, camera: Camera) -> list[Entity]:
        visible = []
        for ent in self.entities:
            if (
                (ent.kind == "line" and any(
                    project_ecef(p, camera) is not None for p in ent.points
                ))
                or (ent.position is not None and project_ecef(ent.position, camera) is not None)
            ):
                visible.append(ent)
        return visible

    def pick(
        self, sx: float, sy: float, cw: float, ch: float, camera: Camera, threshold: float = 20.0
    ) -> Entity | None:
        best = None
        best_dist = threshold
        for ent in self.visible(camera):
            if ent.kind == "line":
                for p in ent.points:
                    ndc = project_ecef(p, camera)
                    if ndc is None:
                        continue
                    px = (ndc[0] * 0.5 + 0.5) * cw
                    py = (1.0 - (ndc[1] * 0.5 + 0.5)) * ch
                    d = np.hypot(sx - px, sy - py)
                    if d < best_dist:
                        best_dist = d
                        best = ent
            elif ent.position is not None:
                ndc = project_ecef(ent.position, camera)
                if ndc is None:
                    continue
                px = (ndc[0] * 0.5 + 0.5) * cw
                py = (1.0 - (ndc[1] * 0.5 + 0.5)) * ch
                d = np.hypot(sx - px, sy - py)
                if d < best_dist:
                    best_dist = d
                    best = ent
        return best

    @classmethod
    def example(cls) -> Scene:
        s = cls()
        s.add(Entity(tipo="strada", kind="line",
                      points=[latlon_to_vec(45.0, 9.0), latlon_to_vec(45.01, 9.02)],
                      color=[0.95, 0.78, 0.22]))
        s.add(Entity(tipo="albero", position=latlon_to_vec(45.005, 9.01),
                      color=[0.28, 0.92, 0.42]))
        s.add(Entity(tipo="montagna", position=latlon_to_vec(45.015, 9.03, 8000.0),
                      color=[0.92, 0.32, 0.28]))
        return s
