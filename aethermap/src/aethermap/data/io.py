"""AetherMap Fase 2 — I/O utilities (GeoJSON, Parquet, 3D Tiles, CityGML).

Contratti:
- GeoJSON: interscambio standard WGS84 lat/lon, properties estese con S2/H3.
- Parquet: storage colonnare efficiente per batch analytics (richiede duckdb).
- 3D Tiles / CityGML: placeholder documentati, pronti per implementazione futura.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from aethermap.ai.models import Oggetto


# ===========================================================================
# GeoJSON
# ===========================================================================

def oggetto_to_feature(obj: Oggetto) -> dict[str, Any]:
    g = obj.geometria
    if g.tipo == "linea":
        coords = [
            [p["lon"], p["lat"], p.get("ele") or 0.0]
            for p in g.dati.get("punti", [])
        ]
        geom: dict[str, Any] = {"type": "LineString", "coordinates": coords}
    else:
        alt = getattr(obj.posizione, "alt", 0.0) or 0.0
        geom = {"type": "Point", "coordinates": [obj.posizione.lon, obj.posizione.lat, alt]}

    props: dict[str, Any] = {
        "tipo": obj.tipo,
        "affidabilita": obj.affidabilita.valore,
        "proprieta": obj.proprieta,
    }
    s2 = getattr(obj.posizione, "s2", None)
    if s2:
        props["s2"] = s2
    h3 = getattr(obj.posizione, "h3", None)
    if h3:
        props["h3"] = h3

    return {
        "type": "Feature",
        "id": obj.id,
        "properties": props,
        "geometry": geom,
    }


def feature_to_oggetto(feat: dict[str, Any]) -> Oggetto:
    from aethermap.ai.models import Confidenza, Geometria, Posizione

    props = feat.get("properties", {})
    geom = feat.get("geometry", {})
    gtype = geom.get("type", "Point")
    coords = geom.get("coordinates", [0.0, 0.0])
    lon, lat = float(coords[0]), float(coords[1])
    alt = float(coords[2]) if len(coords) > 2 else 0.0

    posizione = Posizione(
        lat=lat, lon=lon, alt=alt,
        s2=props.get("s2") or None,
        h3=props.get("h3") or None,
    )

    geometry_dict: dict[str, Any] = {"tipo": "punto"}
    if gtype == "LineString":
        punti = []
        for c in geom.get("coordinates", []):
            punti.append({
                "lat": float(c[1]), "lon": float(c[0]),
                "ele": float(c[2]) if len(c) > 2 else None,
            })
        geometry_dict = {"tipo": "linea", "punti": punti}

    return Oggetto(
        id=str(feat.get("id") or props.get("id") or f"obj_{id(feat)}"),
        tipo=props.get("tipo", "oggetto"),
        posizione=posizione,
        geometria=Geometria(**geometry_dict),
        affidabilita=Confidenza(valore=float(props.get("affidabilita", 1.0))),
        proprieta=props.get("proprieta", {}),
    )


def export_geojson(objects: Iterable[Oggetto], path: str | Path, metadata: dict[str, Any] | None = None) -> None:
    features = [oggetto_to_feature(obj) for obj in objects]
    fc: dict[str, Any] = {"type": "FeatureCollection", "features": features}
    if metadata:
        fc["metadata"] = metadata
    Path(path).write_text(json.dumps(fc, default=str, indent=2), encoding="utf-8")


def import_geojson(path: str | Path) -> list[Oggetto]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    features = data.get("features", [])
    objects: list[Oggetto] = []
    for feat in features:
        try:
            objects.append(feature_to_oggetto(feat))
        except Exception:
            continue
    return objects


# ===========================================================================
# Parquet (richiede duckdb)
# ===========================================================================

def export_parquet(objects: Iterable[Oggetto], path: str | Path) -> None:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb required for parquet export") from exc

    rows = []
    for obj in objects:
        rows.append({
            "id": obj.id,
            "tipo": obj.tipo,
            "lat": obj.posizione.lat,
            "lon": obj.posizione.lon,
            "alt": obj.posizione.alt,
            "s2": obj.posizione.s2 or "",
            "h3": getattr(obj.posizione, "h3", None) or "",
            "confidence": obj.affidabilita.valore,
            "n_stati": len(obj.cronologia),
        })
    if not rows:
        Path(path).touch()
        return
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE objects (id VARCHAR, tipo VARCHAR, lat DOUBLE, "
        "lon DOUBLE, alt DOUBLE, s2 VARCHAR, h3 VARCHAR, confidence DOUBLE, n_stati INTEGER)"
    )
    for r in rows:
        con.execute(
            "INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?)",
            [r["id"], r["tipo"], r["lat"], r["lon"], r["alt"],
             r["s2"], r["h3"], r["confidence"], r["n_stati"]],
        )
    con.execute(f"COPY objects TO '{path}' (FORMAT PARQUET)")
    con.close()


def import_parquet(path: str | Path) -> list[Oggetto]:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb required for parquet import") from exc

    from aethermap.ai.models import Confidenza, Geometria, Posizione

    con = duckdb.connect(":memory:")
    df = con.execute(f"SELECT * FROM read_parquet('{path}')").fetchdf()
    objects: list[Oggetto] = []
    for _, row in df.iterrows():
        try:
            pos = Posizione(
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                alt=float(row.get("alt") or 0.0),
                s2=row.get("s2") or None,
                h3=row.get("h3") or None,
            )
            obj = Oggetto(
                id=str(row["id"]),
                tipo=str(row["tipo"]),
                posizione=pos,
                geometria=Geometria(),
                affidabilita=Confidenza(valore=float(row.get("confidence") or 1.0)),
            )
            objects.append(obj)
        except Exception:
            continue
    con.close()
    return objects


# ===========================================================================
# 3D Tiles (placeholder)
# ===========================================================================

def export_3dtiles(objects: Iterable[Oggetto], path: str | Path) -> None:
    """Placeholder per esportazione 3D Tiles (b3dm / i3dm / pnts).

    Implementazione futura: impacchetta le geometrie ECEF-relative in tile
    S2 gerarchiche secondo lo standard 3D Tiles OGC.
    """
    raise NotImplementedError(
        "3D Tiles export: da implementare in Fase 4 (Fase 2 design doc §7, doc 3D Tiles)."
    )


def import_3dtiles(path: str | Path) -> list[Oggetto]:
    """Placeholder per importazione 3D Tiles."""
    raise NotImplementedError(
        "3D Tiles import: da implementare in Fase 4 (Fase 2 design doc §7)."
    )


# ===========================================================================
# CityGML (placeholder)
# ===========================================================================

def export_citygml(objects: Iterable[Oggetto], path: str | Path) -> None:
    """Placeholder per esportazione CityGML.

    Implementazione futura: converte entita' in Building / Bridge / SolitaryVegetation
    CityGML con gml:pos (ECEF-relative) e app:attribute.
    """
    raise NotImplementedError(
        "CityGML export: da implementare in Fase 5 (Fase 2 design doc §7)."
    )


def import_citygml(path: str | Path) -> list[Oggetto]:
    """Placeholder per importazione CityGML."""
    raise NotImplementedError(
        "CityGML import: da implementare in Fase 5 (Fase 2 design doc §7)."
    )
