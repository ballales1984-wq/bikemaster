from __future__ import annotations

import numpy as np

from aethermap.render.projection import latlon_to_vec


class Scene:
    def __init__(self) -> None:
        self.entities: list[dict] = []

    def add(self, tipo: str, latlon, alt: float = 0.0, char: str = "o") -> None:
        if isinstance(latlon[0], (list, tuple)):
            pts = [latlon_to_vec(a, b, alt) for a, b in latlon]
        else:
            pts = [latlon_to_vec(latlon[0], latlon[1], alt)]
        self.entities.append({"tipo": tipo, "pts": pts, "char": char})

    @classmethod
    def example(cls) -> "Scene":
        s = cls()
        s.add("strada", [(45.0, 9.0), (45.01, 9.02), (45.02, 9.04)], char="S")
        s.add("albero", (45.005, 9.01), char="T")
        s.add("montagna", (45.015, 9.03), alt=8000.0, char="M")
        return s
