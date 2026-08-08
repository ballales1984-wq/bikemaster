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
from contextlib import suppress
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
    return _terrain_mesh_from_hf(_build_full_heightfield(n, base_alt, height_scale).flatten(), n)


def _build_full_heightfield(n: int, base_alt: float, height_scale: float) -> np.ndarray:
    hf = _build_heightfield(n, base_alt, height_scale)
    return np.stack([hf] * 6, axis=0)



def _terrain_mesh_from_hf(hf: np.ndarray, n: int, with_skirt: bool = True) -> dict[str, Any]:
    """Build cube-sphere terrain mesh from a pre-flattened NxNx6 heightfield."""
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    hf = hf.reshape((6, n, n))

    for face in range(6):
        base_idx = len(positions)
        grid_size = n + 2 if with_skirt else n
        face_positions: list[list[float]] = []
        for i in range(grid_size):
            face_positions.append([])
            for j in range(grid_size):
                src_i = max(0, min(i - 1, n - 1)) if with_skirt else i
                src_j = max(0, min(j - 1, n - 1)) if with_skirt else j
                u = (src_i / (n - 1)) * 2.0 - 1.0
                v = (src_j / (n - 1)) * 2.0 - 1.0
                d = _face_direction(face, u, v)
                h = float(hf[face, src_i, src_j])
                is_skirt = with_skirt and (i == 0 or i == grid_size - 1 or j == 0 or j == grid_size - 1)
                if is_skirt:
                    h = min(h, 0.0) - 0.0001
                px = float(d[0] * (1.0 + h))
                py = float(d[1] * (1.0 + h))
                pz = float(d[2] * (1.0 + h))
                face_positions[i].append([px, py, pz])

        for i in range(grid_size):
            for j in range(grid_size):
                positions.append(face_positions[i][j])

        for i in range(grid_size):
            for j in range(grid_size):
                if i + 1 < grid_size and j + 1 < grid_size:
                    p = face_positions[i][j]
                    pi = face_positions[i + 1][j]
                    pj = face_positions[i][j + 1]
                    t1 = [pi[0] - p[0], pi[1] - p[1], pi[2] - p[2]]
                    t2 = [pj[0] - p[0], pj[1] - p[1], pj[2] - p[2]]
                    nx = t1[1] * t2[2] - t1[2] * t2[1]
                    ny = t1[2] * t2[0] - t1[0] * t2[2]
                    nz = t1[0] * t2[1] - t1[1] * t2[0]
                    length = math.sqrt(nx * nx + ny * ny + nz * nz)
                    if length > 1e-12:
                        nx, ny, nz = nx / length, ny / length, nz / length
                    else:
                        src_i = max(0, min(i - 1, n - 1)) if with_skirt else i
                        src_j = max(0, min(j - 1, n - 1)) if with_skirt else j
                        u = (src_i / (n - 1)) * 2.0 - 1.0
                        v = (src_j / (n - 1)) * 2.0 - 1.0
                        nd = _face_direction(face, u, v)
                        nx, ny, nz = nd[0], nd[1], nd[2]
                    normals.append([nx, ny, nz])

        for i in range(grid_size - 1):
            for j in range(grid_size - 1):
                a = base_idx + i * grid_size + j
                b = base_idx + (i + 1) * grid_size + j
                c = base_idx + (i + 1) * grid_size + (j + 1)
                d2 = base_idx + i * grid_size + (j + 1)
                indices.extend([a, b, d2])
                indices.extend([b, c, d2])

    return {
        "positions": positions,
        "normals": normals,
        "indices": indices,
        "grid_size": grid_size,
        "faces": 6,
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
        "s2": getattr(pos, "s2", None),
    }

    if tipo == "strada" or tipo == "segment":
        punti = obj.geometria.dati.get("punti", [])
        pts = []
        for p in punti:
            if not isinstance(p, dict):
                continue
            lat = p.get("lat")
            lon = p.get("lon")
            if lat is None or lon is None:
                continue
            d = geodetic_to_direction(lat, lon)
            r = 1.0 + (p.get("ele") or 0.0) / earth_r
            pts.append([float(d[0] * r), float(d[1] * r), float(d[2] * r)])
        if len(pts) < 2:
            return {
                "id": obj.id,
                "tipo": tipo,
                "kind": "line",
                "points": [],
                "color": color,
                "props": obj.proprieta,
                "confidence": obj.affidabilita.valore,
                "s2": getattr(pos, "s2", None),
            }
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
            try:
                stats = obj.volume_stats(temp_c=15.0)
                entry["props"]["svo_stats"] = {
                    "snow_pct": stats.get("snow_%", 0),
                    "rock_pct": stats.get("rock_%", 0),
                    "veg_pct": stats.get("veg_%", 0),
                    "voxels": stats.get("voxel_totali", 0),
                }
            except Exception:
                pass
        elif tipo == "albero":
            entry["kind"] = "point"
            height = obj.altezza() if hasattr(obj, "altezza") else (pos.alt or 5.0)
            entry["height_m"] = height
            entry["radius"] = max(0.0001, height / earth_r)
            entry["position"] = [px, py, pz]
        elif tipo in ("citta", "costa", "confine"):
            entry["kind"] = "point" if tipo != "costa" and tipo != "confine" else "line"
            if tipo in ("costa", "confine"):
                punti = obj.geometria.dati.get("punti", []) if obj.geometria else []
                pts = []
                for p in punti:
                    d = geodetic_to_direction(p["lat"], p["lon"])
                    r = 1.0 + (p.get("ele") or 0.0) / earth_r
                    pts.append([float(d[0] * r), float(d[1] * r), float(d[2] * r)])
                entry["kind"] = "line"
                entry["points"] = pts
            else:
                entry["position"] = [px, py, pz]
        else:
            entry["kind"] = "point"
            entry["position"] = [px, py, pz]

    return entry


def _natural_earth_entity_to_gl(entry: dict[str, Any], earth_r: float = 6371000.0) -> dict[str, Any]:
    if entry.get("kind") == "line":
        pts = []
        for p in entry.get("points", []):
            d = geodetic_to_direction(p["lat"], p["lon"])
            r = 1.0 + (p.get("ele") or 0.0) / earth_r
            pts.append([float(d[0] * r), float(d[1] * r), float(d[2] * r)])
        return {
            "id": entry["id"],
            "tipo": entry["tipo"],
            "color": entry.get("color", [0.8, 0.8, 0.8]),
            "kind": "line",
            "points": pts,
            "props": entry.get("props", {}),
            "confidence": entry.get("confidence", 1.0),
        }
    pos = entry.get("position", [0, 0])
    lat, lon = pos[0], pos[1]
    d = geodetic_to_direction(lat, lon)
    r = 1.0
    px, py, pz = float(d[0] * r), float(d[1] * r), float(d[2] * r)
    return {
        "id": entry["id"],
        "tipo": entry["tipo"],
        "color": entry.get("color", [0.8, 0.8, 0.8]),
        "kind": "point",
        "position": [px, py, pz],
        "radius": 1.0,
        "props": entry.get("props", {}),
        "confidence": entry.get("confidence", 1.0),
    }


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
    natural_earth: bool = False,
    ne_resolution: str = "110m",
) -> None:
    earth_r = 6_371_000.0
    if dem_base_url:
        from aethermap.render.terrain_enhancer import build_enhanced_heightfield
        hf = build_enhanced_heightfield(n_terrain, terrain_base_alt, terrain_scale, dem_base_url)
    else:
        hf = _build_full_heightfield(n_terrain, terrain_base_alt, terrain_scale).flatten()
    terrain = _terrain_mesh_from_hf(hf, n_terrain)

    entities = []
    for obj in twin.store.objects.values():
        entities.append(_entity_to_gl(obj, earth_r))

    if natural_earth:
        try:
            from aethermap.geo.natural_earth import load_cities, load_coastlines, load_country_borders
            from aethermap.geo.natural_earth import to_entities as ne_to_entities
            ne_data = ne_to_entities(
                coastlines=load_coastlines(resolution=ne_resolution),
                borders=load_country_borders(resolution=ne_resolution),
                cities=load_cities(resolution=ne_resolution, min_pop=50000),
            )
            for ne_ent in ne_data["entities"]:
                entities.append(_natural_earth_entity_to_gl(ne_ent, earth_r))
            print(f"[webgl_exporter] Natural Earth: +{ne_data['coastline_count']} coastlines, "
                  f"+{ne_data['border_count']} borders, +{ne_data['city_count']} cities")
        except Exception as exc:
            print(f"[webgl_exporter] Natural Earth data unavailable: {exc}")

    relations = []
    for obj in twin.store.objects.values():
        for rel in obj.relazioni:
            relations.append({
                "from": obj.id,
                "to": rel.target_id,
                "tipo": rel.tipo,
                "peso": rel.peso,
            })

    camera = {
        "yaw": 0.6,
        "pitch": 0.35,
    }

    data = {
        "version": "aethermap-webgl-1.0",
        "terrain": terrain,
        "entities": entities,
        "relations": relations,
        "camera": camera,
        "earth_r": earth_r,
    }

    Path(path).write_text(json.dumps(data, default=str), encoding="utf-8")


def export_world_geojson(
    twin: DigitalTwin,
    path: str | Path,
) -> None:
    """Export the DigitalTwin world as a GeoJSON FeatureCollection.

    Each entity becomes a GeoJSON Feature with properties:
    - tipo: entity type (strada, albero, montagna)
    - proprieta: entity properties dict
    - confidence: entity reliability score
    - relations: list of entity relations

    The FeatureCollection metadata includes engine info and
    H3 grid summary for spatial indexing.
    """
    features: list[dict[str, Any]] = []
    for obj in twin.store.objects.values():
        props = obj.proprieta.copy()
        props["confidence"] = obj.affidabilita.valore
        props["tipo"] = obj.tipo
        props["relations"] = [
            {"tipo": r.tipo, "target_id": r.target_id, "peso": r.peso}
            for r in obj.relazioni
        ]
        geometry: dict[str, Any] = {"type": "Point", "coordinates": [obj.posizione.lon, obj.posizione.lat]}
        if obj.geometria.tipo == "linea" and "punti" in obj.geometria.dati:
            coords = [
                [p["lon"], p["lat"], p.get("ele", 0.0)]
                for p in obj.geometria.dati["punti"]
            ]
            geometry = {"type": "LineString", "coordinates": coords}
        features.append(
            {
                "type": "Feature",
                "id": obj.id,
                "geometry": geometry,
                "properties": props,
            }
        )

    h3_summary: dict[str, dict[str, int]] = {}
    with suppress(Exception):
        h3_summary = twin.h3_summary()

    geojson: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "engine": "aethermap",
            "version": "1.0",
            "entity_count": len(features),
            "h3_summary": h3_summary,
        },
    }

    Path(path).write_text(
        json.dumps(geojson, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> None:
    import argparse

    from aethermap.twin.objects import make_albero, make_montagna, make_strada

    parser = argparse.ArgumentParser(description="AetherMap WebGL world exporter")
    parser.add_argument("output", nargs="?", default=None, help="Output JSON path")
    parser.add_argument("--dem-base-url", type=str, default=None, help="Backend URL per DEM reale")
    parser.add_argument("--natural-earth", action="store_true", help="Includi dati Natural Earth")
    parser.add_argument("--ne-resolution", type=str, default="110m", choices=["10m", "50m", "110m"])
    args = parser.parse_args()

    output = Path(args.output) if args.output else Path(__file__).resolve().parent / "world_data.json"

    twin = DigitalTwin()
    pts = [{"lat": 45.0 + i * 0.0005, "lon": 9.0 + i * 0.0006, "ele": 120 + (i % 2) * 2}
           for i in range(6)]
    twin.add(make_strada("strada-1", 45.0, 9.0, pts))
    twin.add(make_albero("albero-1", 45.005, 9.01, "quercia", 8.5))
    twin.add(make_montagna("montagna-1", 45.015, 9.03, 1800.0, ["nord", "sud", "est"]))

    env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
    twin.step(env)

    export_world(
        twin, output,
        dem_base_url=args.dem_base_url,
        natural_earth=args.natural_earth,
        ne_resolution=args.ne_resolution,
    )
    src_note = f" (DEM da {args.dem_base_url})" if args.dem_base_url else ""
    ne_note = " + Natural Earth" if args.natural_earth else ""
    print(f"[webgl_exporter] dati mondo esportati in {output}{src_note}{ne_note}")
    print("[webgl_exporter] aprire webgl_stub.html nel browser per visualizzare")


if __name__ == "__main__":
    main()
