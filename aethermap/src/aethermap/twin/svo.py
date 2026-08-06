from __future__ import annotations

import numpy as np

ROCK, SNOW, VEG, EMPTY = 0, 1, 2, 3
_N = 16


class SparseVolume:
    """Volume SVO minimale (ottree sparso) per una montagna.

    Produzione: un Sparse Voxel Octree reale gerarchico. Qui usiamo
    una grglia N^3 + dizionario sparso dei voxel pieni, abbastanza
    per mostrare il concetto di montagna-come-volume-vivo (neve/rock/veg
    interni) anziche come "pelle" superficiele.
    """

    def __init__(self, base_alt: float, height: float, radius: float,
                 versanti: list[str], temp_c: float = 15.0) -> None:
        self.base_alt = base_alt
        self.height = height
        self.radius = radius
        self.versanti = versanti
        self.temp_c = temp_c
        self.grid = np.full((_N, _N, _N), EMPTY, dtype=np.int8)
        self._build()

    def _build(self) -> None:
        h, r0 = self.height, self.radius
        snow_line = self.base_alt + 1500.0 + (self.temp_c - 15.0) * 100.0
        for i in range(_N):
            x = (i / (_N - 1)) * 2.0 - 1.0
            for j in range(_N):
                y = (j / (_N - 1)) * 2.0 - 1.0
                for k in range(_N):
                    z = (k / (_N - 1)) * 2.0 - 1.0
                    rad = np.hypot(x, y)
                    if rad > (1.0 - (z + 1.0) / 2.0) * (r0 / self.radius):
                        continue
                    alt = self.base_alt + (z + 1.0) / 2.0 * h
                    if alt >= snow_line:
                        self.grid[i, j, k] = SNOW
                    elif alt < self.base_alt + 600.0:
                        self.grid[i, j, k] = VEG
                    else:
                        self.grid[i, j, k] = ROCK

    def material_at(self, i: int, j: int, k: int) -> int:
        return int(self.grid[i, j, k])

    def _count(self, mat: int) -> int:
        return int(np.count_nonzero(self.grid == mat))

    def snow_fraction(self) -> float:
        full = int(np.count_nonzero(self.grid != EMPTY))
        return round(self._count(SNOW) / full, 3) if full else 0.0

    def stats(self) -> dict:
        full = int(np.count_nonzero(self.grid != EMPTY))
        return {
            "voxel_totali": full,
            "snow_%": round(100.0 * self._count(SNOW) / full, 1) if full else 0.0,
            "rock_%": round(100.0 * self._count(ROCK) / full, 1) if full else 0.0,
            "veg_%": round(100.0 * self._count(VEG) / full, 1) if full else 0.0,
        }

    def fraction_per_versant(self) -> dict:
        out: dict[str, float] = {}
        half = _N // 2
        for name, slab in [
            ("W", self.grid[:half]),
            ("E", self.grid[half:]),
            ("S", self.grid[:, :half]),
            ("N", self.grid[:, half:]),
        ]:
            flat = slab.reshape(-1)
            full = int(np.count_nonzero(flat != EMPTY))
            out[name] = round(100.0 * int(np.count_nonzero(flat == SNOW)) / full, 1) if full else 0.0
        return out
