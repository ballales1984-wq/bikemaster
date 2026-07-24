"""AetherMap Fase 4 — esporta dati del mondo per il renderer WebGL.

Genera un JSON che il renderer webgl_stub.html puo' consumare direttamente.
Contiene:
- vertici del cube-sphere con heightfield (terreno procedurale)
- entita (strade, alberi, montagne) con posizioni e stati
- matrice di rotazione camera iniziale

Uso:
    python -m aethermap.render.webgl_exporter [output.json]
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

from aethermap.core.coordinates import geodetic_to_direction
from aethermap.twin.world import DigitalTwin, Environment


# ===========================================================================
# Heightfield procedurale (terreno)
# ===========================================================================

def _fbm_noise(x: np.ndarray, y: np.ndarray, octaves: int = 4) -> np.ndarray:
    """Fractional Brownian Motion semplice (sin-based, deterministico)."""
    v = np.zeros_like(x)
    amp = 0.5
    freq = 1.0
    for _ in range(octaves):
        v += amp * (np.sin(x * freq * 3.17 + 1.3) * np.cos(y * freq * 2.71 + 0.7))
        amp *= 0.5
        freq *= 2.1
    return v


def _build_heightfield(n: int = 64, base_alt: float = 0.0, height_scale: float = 0.04) -> np.ndarray:
    """Genera heightfield NxN per faccia cube-sphere."""
    u = np.linspace(-1.0, 1.0, n)
    v = np.linspace(-1.0, 1.0, n)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    hf = _fbm_noise(uu, vv, octaves=5)
    hf = (hf - hf.min()) / (hf.max() - hf.min())
    hf = base_alt + hf * height_scale
    return hf


# ===========================================================================
# Generazione vertici cube-sphere con heightfield
# ===========================================================================

def _face_direction(face: int, u: float, v: float) -> np.ndarray:
    if face == 0:
        d = np.array([1.0, u, v])
    elif face == 1:
        d = np.array([-1.0, u, v])
    elif face == 2:
        d = np.array([u, 1.0, v])
    elif face == 3:
        d = np.array([u, -1.0, v])
    elif face == 4:
        d = np.array([u, v, 1.0])
    else:
        d = np.array([u, v, -1.0])
    return d / np.linalg.norm(d)


def _terrain_mesh(n: int = 48, base_alt: float = 0.0, height_scale: float = 0.04) -> dict[str, Any]:
    return _terrain_mesh_from_hf(_build_heightfield(n, base_alt, height_scale).flatten(), n)


def _terrain_mesh_from_hf(hf: np.ndarray, n: int) -> dict[str, Any]:
    """Build cube-sphere terrain mesh from a pre-flattened NxNx6 heightfield."""
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    hf = hf.reshape((6, n, n))

    for face in range(6):
        base_idx = len(positions)
        for i in range(n):
            for j in range(n):
                u = (i / (n - 1)) * 2.0 - 1.0
                v = (j / (n - 1)) * 2.0 - 1.0
                d = _face_direction(face, u, v)
                h = float(hf[face, i, j])
                px = float(d[0] * (1.0 + h))
                py = float(d[1] * (1.0 + h))
                pz = float(d[2] * (1.0 + h))
                positions.append([px, py, pz])
                normals.append([float(d[0]), float(d[1]), float(d[2])])

        for i in range(n - 1):
            for j in range(n - 1):
                a = base_idx + i * n + j
                b = base_idx + (i + 1) * n + j
                c = base_idx + (i + 1) * n + (j + 1)
                d2 = base_idx + i * n + (j + 1)
                indices.extend([a, b, d2])
                indices.extend([b, c, d2])

    return {
        "positions": positions,
        "normals": normals,
        "indices": indices,
    }


# ===========================================================================
# Entita' -> formato WebGL
# ===========================================================================

def _entity_color(tipo: str) -> list[float]:
    palette = {
        "strada": [0.95, 0.78, 0.22],
        "albero": [0.28, 0.92, 0.42],
        "montagna": [0.92, 0.32, 0.28],
        "sensore_traffico": [0.3, 0.7, 1.0],
        "edificio": [0.7, 0.7, 0.7],
        "via": [0.8, 0.75, 0.6],
    }
    return palette.get(tipo, [0.8, 0.8, 0.8])


def _entity_to_gl(obj: Any, earth_r: float = 6371000.0) -> dict[str, Any]:
    tipo = obj.tipo
    color = _entity_color(tipo)
    pos = obj.posizione
    dir_vec = geodetic_to_direction(pos.lat, pos.lon)

    entry: dict[str, Any] = {
        "id": obj.id,
        "tipo": tipo,
        "color": color,
        "props": obj.proprieta,
        "confidence": obj.affidabilita.valore,
    }

    if tipo == "strada":
        punti = obj.geometria.dati.get("punti", [])
        pts = []
        for p in punti:
            d = geodetic_to_direction(p["lat"], p["lon"])
            r = 1.0 + (p.get("ele") or 0.0) / earth_r
            pts.append([float(d[0] * r), float(d[1] * r), float(d[2] * r)])
        entry["kind"] = "line"
        entry["points"] = pts
    else:
        alt = pos.alt or 0.0
        r = 1.0 + alt / earth_r
        px, py, pz = float(dir_vec[0] * r), float(dir_vec[1] * r), float(dir_vec[2] * r)
        if tipo == "montagna":
            r_mountain = 1.0 + (alt + 800.0) / earth_r
            px, py, pz = float(dir_vec[0] * r_mountain), float(dir_vec[1] * r_mountain), float(dir_vec[2] * r_mountain)
            entry["kind"] = "point"
            entry["radius"] = float(r_mountain)
            entry["position"] = [px, py, pz]
        elif tipo == "albero":
            entry["kind"] = "point"
            entry["height_m"] = pos.alt or 5.0
            entry["position"] = [px, py, pz]
        else:
            entry["kind"] = "point"
            entry["position"] = [px, py, pz]

    return entry


# ===========================================================================
# Main export
# ===========================================================================

def export_world(
    twin: DigitalTwin,
    path: str | Path,
    n_terrain: int = 64,
    terrain_base_alt: float = 0.0,
    terrain_scale: float = 0.04,
    dem_base_url: str | None = None,
) -> None:
    earth_r = 6_371_000.0
    if dem_base_url:
        from aethermap.render.terrain_enhancer import build_enhanced_heightfield
        hf = build_enhanced_heightfield(n_terrain, terrain_base_alt, terrain_scale, dem_base_url)
    else:
        hf = _build_heightfield(n_terrain, terrain_base_alt, terrain_scale).flatten()
    terrain = _terrain_mesh_from_hf(hf, n_terrain)

    entities = []
    for obj in twin.store.objects.values():
        entities.append(_entity_to_gl(obj, earth_r))

    camera = {
        "yaw": 0.6,
        "pitch": 0.35,
    }

    data = {
        "version": "aethermap-webgl-1.0",
        "terrain": terrain,
        "entities": entities,
        "camera": camera,
        "earth_r": earth_r,
    }

    Path(path).write_text(json.dumps(data, default=str), encoding="utf-8")


def main() -> None:
    import sys
    from aethermap.twin.objects import make_albero, make_montagna, make_strada

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "world_data.json"
    dem_url = None
    if "--dem-base-url" in sys.argv:
        idx = sys.argv.index("--dem-base-url")
        if idx + 1 < len(sys.argv):
            dem_url = sys.argv[idx + 1]

    twin = DigitalTwin()
    pts = [{"lat": 45.0 + i * 0.0005, "lon": 9.0 + i * 0.0006, "ele": 120 + (i % 2) * 2}
           for i in range(6)]
    twin.add(make_strada("strada-1", 45.0, 9.0, pts))
    twin.add(make_albero("albero-1", 45.005, 9.01, "quercia", 8.5))
    twin.add(make_montagna("montagna-1", 45.015, 9.03, 1800.0, ["nord", "sud", "est"]))

    env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
    twin.step(env)

    export_world(twin, output, dem_base_url=dem_url)
    src_note = f" (DEM da {dem_url})" if dem_url else ""
    print(f"[webgl_exporter] dati mondo esportati in {output}{src_note}")
    print(f"[webgl_exporter] aprire webgl_stub.html nel browser per visualizzare")


if __name__ == "__main__":
    main()
