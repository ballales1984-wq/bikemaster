"""AetherMap Fase 2 — I/O utilities (GeoJSON, Parquet, 3D Tiles, CityGML).

Contratti:
- GeoJSON: interscambio standard WGS84 lat/lon, properties estese con S2/H3.
- Parquet: storage colonnare efficiente per batch analytics (richiede duckdb).
- 3D Tiles: esportazione/importazione b3dm con gerarchia S2 (implementato).
- CityGML 2.0: import/export XML con Building / SolitaryVegetation / Road
  (gml:pos ECEF, app:attribute).
"""
from __future__ import annotations

import json
import struct
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from aethermap.ai.models import Confidenza, Geometria, Oggetto, Posizione

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
# 3D Tiles
# ===========================================================================

def _oggetto_to_ecef(obj: Oggetto) -> tuple[float, float, float]:
    pos = obj.posizione
    from aethermap.core.coordinates import geodetic_to_ecef

    ecef = geodetic_to_ecef(pos.lat, pos.lon, pos.alt or 0.0)
    return ecef.x, ecef.y, ecef.z


def _oggetto_to_point(obj: Oggetto) -> dict[str, Any]:
    ecef = _oggetto_to_ecef(obj)
    return {
        "id": obj.id,
        "tipo": obj.tipo,
        "position": list(ecef),
        "confidence": obj.affidabilita.valore,
        "proprieta": obj.proprieta,
    }


def _build_tileset(
    tiles: list[dict],
    root_url: str = ".",
) -> dict[str, Any]:
    if not tiles:
        return {"asset": {"version": "1.0"}, "geometricError": 100.0, "root": None}

    def _tile_bounds(tile: dict) -> list[float]:
        return tile.get("boundingVolume", {}).get("region", [0, 0, 0, 0])

    def _max_geometric_error(tiles: list[dict]) -> float:
        return max((t.get("geometricError", 0.0) for t in tiles), default=0.0)

    root = {
        "boundingVolume": {
            "region": _tile_bounds(tiles[0]) if tiles else [0, 0, 0, 0],
        },
        "geometricError": _max_geometric_error(tiles),
        "refine": "ADD",
        "content": {"uri": tiles[0]["uri"]} if tiles else None,
        "children": [],
    }

    def _tile_uri(tile: dict) -> str:
        return tile.get("uri") or tile.get("content", {}).get("uri", "")

    def _build_tree(tile_list: list[dict], depth: int = 0) -> list[dict]:
        if depth > 4 or len(tile_list) <= 1:
            return tile_list
        mid = len(tile_list) // 2
        left = _build_tree(tile_list[:mid], depth + 1)
        right = _build_tree(tile_list[mid:], depth + 1)
        result: list[dict] = []
        if left:
            result.append(
                {
                    "boundingVolume": {
                        "region": _tile_bounds(left[0]),
                    },
                    "geometricError": left[0].get("geometricError", 0.0),
                    "refine": "ADD",
                    "content": {"uri": _tile_uri(left[0])},
                    "children": left[1:] if len(left) > 1 else [],
                }
            )
        if right:
            result.append(
                {
                    "boundingVolume": {
                        "region": _tile_bounds(right[0]),
                    },
                    "geometricError": right[0].get("geometricError", 0.0),
                    "refine": "ADD",
                    "content": {"uri": _tile_uri(right[0])},
                    "children": right[1:] if len(right) > 1 else [],
                }
            )
        return result

    root["children"] = _build_tree(tiles)

    return {
        "asset": {"version": "1.0", "generator": "aethermap"},
        "geometricError": _max_geometric_error(tiles),
        "root": root,
    }


def _write_b3dm(
    points: list[dict],
    path: Path,
) -> None:
    import struct

    positions = np.array(
        [p["position"] for p in points], dtype=np.float32
    )
    batch_table = {
        "id": [p["id"] for p in points],
        "tipo": [p["tipo"] for p in points],
        "confidence": [p["confidence"] for p in points],
    }

    positions_bytes = positions.tobytes()
    batch_length = len(points)

    feature_table_json = (
        f'{{"BATCH_LENGTH":{batch_length}}}'
        .encode()
    )
    feature_table_json_padded = feature_table_json + b"\x20" * (
        (16 - len(feature_table_json) % 16) % 16
    )
    feature_table_json_length = len(feature_table_json)

    batch_table_json = (
        '{"id":["'
        + '","'.join(batch_table["id"])
        + '"],"tipo":["'
        + '","'.join(str(t) for t in batch_table["tipo"])
        + '"],"confidence":['
        + ",".join(str(c) for c in batch_table["confidence"])
        + "]}"
    ).encode("utf-8")
    batch_table_json_padded = batch_table_json + b"\x20" * (
        (16 - len(batch_table_json) % 16) % 16
    )
    batch_table_json_length = len(batch_table_json)

    byte_length = (
        16
        + 4
        + len(feature_table_json_padded)
        + 4
        + len(batch_table_json_padded)
        + len(positions_bytes)
    )

    header = struct.pack(
        "<4sIII",
        b"b3dm",
        1,
        byte_length,
        batch_length,
    )

    body = positions_bytes

    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", feature_table_json_length))
        f.write(feature_table_json_padded)
        f.write(struct.pack("<I", batch_table_json_length))
        f.write(batch_table_json_padded)
        f.write(body)


def export_3dtiles(
    objects: Iterable[Oggetto],
    path: str | Path,
    s2_resolution: int = 12,
) -> None:
    """Export AetherMap objects as 3D Tiles (b3dm tileset).

    Creates a tileset.json with S2-based tile hierarchy and
    b3dm tiles containing point geometry with batch table attributes.

    Args:
        objects: Iterable of Oggetto instances to export.
        path: Output directory path (tileset.json + b3dm tiles written here).
        s2_resolution: S2 cell resolution for tile hierarchy (default 12).
    """

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    obj_list = list(objects)
    if not obj_list:
        tileset = {"asset": {"version": "1.0"}, "geometricError": 0.0, "root": None}
        (path / "tileset.json").write_text(
            json.dumps(tileset, indent=2), encoding="utf-8"
        )
        return

    tiles: list[dict] = []
    for obj in obj_list:
        s2 = getattr(obj.posizione, "s2", None) or ""
        if ":" in s2:
            try:
                face, level, u_int, v_int = s2.split(":")
                s2_token = s2
            except ValueError:
                s2_token = s2
        else:
            try:
                from aethermap.core.coordinates import s2_cell_id

                s2_token = s2_cell_id(
                    obj.posizione.lat, obj.posizione.lon, s2_resolution
                )
            except RuntimeError:
                s2_token = f"fallback_{obj.id}"

        tile_dir = path / s2_token
        tile_dir.mkdir(parents=True, exist_ok=True)
        tile_path = tile_dir / f"{obj.id}.b3dm"

        point = _oggetto_to_point(obj)
        _write_b3dm([point], tile_path)

        pos = obj.posizione
        lat = pos.lat
        lon = pos.lon
        alt = pos.alt or 0.0
        region = [
            lon - 0.001,
            lat - 0.001,
            lon + 0.001,
            lat + 0.001,
            alt - 10.0,
            alt + 10.0,
        ]

        tiles.append(
            {
                "uri": f"{s2_token}/{obj.id}.b3dm",
                "boundingVolume": {"region": region},
                "geometricError": 10.0,
            }
        )

    tileset = _build_tileset(tiles)
    (path / "tileset.json").write_text(
        json.dumps(tileset, indent=2, default=str), encoding="utf-8"
    )


def import_3dtiles(path: str | Path) -> list[Oggetto]:
    """Import AetherMap objects from a 3D Tiles tileset.

    Reads tileset.json and b3dm tiles, reconstructing Oggetto instances
    from the point geometry and batch table attributes.

    Args:
        path: Path to the tileset.json or directory containing it.

    Returns:
        List of Oggetto instances reconstructed from the 3D Tiles data.
    """
    path = Path(path)
    tileset_path = (
        path
        if path.name == "tileset.json"
        else path / "tileset.json"
    )

    if not tileset_path.exists():
        raise FileNotFoundError(f"tileset.json not found at {tileset_path}")

    tileset = json.loads(tileset_path.read_text(encoding="utf-8"))
    root = tileset.get("root")
    if root is None:
        return []

    objects: list[Oggetto] = []

    def _collect_tile_uris(tile: dict) -> list[str]:
        uris: list[str] = []
        uri = None
        content = tile.get("content")
        if content and isinstance(content, dict):
            uri = content.get("uri")
        if uri is None:
            uri = tile.get("uri")
        if uri:
            uris.append(uri)
        for child in tile.get("children", []):
            uris.extend(_collect_tile_uris(child))
        return uris

    uris = _collect_tile_uris(root)
    seen_paths: set[str] = set()

    for uri in uris:
        b3dm_path = path / uri
        if not b3dm_path.exists():
            continue
        str_path = str(b3dm_path.resolve())
        if str_path in seen_paths:
            continue
        seen_paths.add(str_path)

        try:
            data = b3dm_path.read_bytes()
            if len(data) < 28:
                continue

            magic = data[:4]
            if magic != b"b3dm":
                continue

            batch_length = struct.unpack("<I", data[12:16])[0]

            offset = 16
            ft_json_length = struct.unpack("<I", data[offset : offset + 4])[0]
            offset += 4
            padded_ft_json_length = ((ft_json_length + 15) // 16) * 16
            offset += padded_ft_json_length
            bt_json_length = struct.unpack("<I", data[offset : offset + 4])[0]
            offset += 4
            bt_json = json.loads(  # noqa: F841
                data[offset : offset + bt_json_length].decode("utf-8").strip()
            )
            padded_bt_json_length = ((bt_json_length + 15) // 16) * 16
            offset += padded_bt_json_length

            positions = np.frombuffer(
                data[offset : offset + batch_length * 12], dtype=np.float32
            ).reshape(batch_length, 3)

            for i in range(batch_length):
                pos = positions[i]
                from aethermap.core.coordinates import ecef_to_geodetic

                geo = ecef_to_geodetic(float(pos[0]), float(pos[1]), float(pos[2]))

                props: dict[str, Any] = {}
                if "proprieta" in bt_json:
                    props = bt_json["proprieta"]
                for key in ("id", "tipo", "confidence"):
                    if key in bt_json:
                        props[key] = bt_json[key]

                obj = Oggetto(
                    id=bt_json.get("id", [f"obj_{i}" for i in range(batch_length)])[
                        i
                    ]
                    if isinstance(bt_json.get("id"), list)
                    else f"obj_{i}",
                    tipo=bt_json.get("tipo", ["unknown"] * batch_length)[i]
                    if isinstance(bt_json.get("tipo"), list)
                    else "unknown",
                    posizione=Posizione(lat=geo.lat, lon=geo.lon, alt=geo.alt),
                    geometria=Geometria(tipo="punto"),
                    affidabilita=Confidenza(
                        valore=bt_json.get("confidence", [1.0] * batch_length)[i]
                        if isinstance(bt_json.get("confidence"), list)
                        else 1.0
                    ),
                    proprieta=props,
                )
                objects.append(obj)
        except Exception:
            continue

    return objects


# ===========================================================================
# CityGML 2.0 (import/export)
# ===========================================================================

_CG_NS = {
    "core": "http://www.opengis.net/citygml/2.0",
    "gml": "http://www.opengis.net/gml",
    "bldg": "http://www.opengis.net/citygml/building/2.0",
    "veg": "http://www.opengis.net/citygml/vegetation/2.0",
    "tran": "http://www.opengis.net/citygml/transportation/2.0",
    "gen": "http://www.opengis.net/citygml/generics/2.0",
    "app": "http://www.opengis.net/citygml/appearance/2.0",
}

_TYPE_TO_CITYGML = {
    "montagna": ("bldg", "Building"),
    "edificio": ("bldg", "Building"),
    "albero": ("veg", "SolitaryVegetation"),
    "strada": ("tran", "Road"),
}

_REV = {
    "Building": "montagna",
    "SolitaryVegetation": "albero",
    "Road": "strada",
    "GenericCityObject": "oggetto",
}

_QNAME = lambda prefix, local: f"{{{_CG_NS[prefix]}}}{local}"


def _obj_to_citygml(obj: Oggetto) -> Any:
    import xml.etree.ElementTree as ET

    from aethermap.core.coordinates import geodetic_to_ecef

    tipo = obj.tipo
    prefix, local = _TYPE_TO_CITYGML.get(tipo, ("gen", "GenericCityObject"))
    ns = _CG_NS[prefix]

    member = ET.Element(_QNAME("core", "cityObjectMember"))
    feat = ET.SubElement(member, _QNAME(prefix, local))
    feat.set(_QNAME("gml", "id"), obj.id)

    pos = obj.posizione
    ecef = geodetic_to_ecef(pos.lat, pos.lon, pos.alt or 0.0)

    if tipo in ("strada", "via") and obj.geometria.dati.get("punti"):
        points = obj.geometria.dati["punti"]
        coords = []
        for p in points:
            e = geodetic_to_ecef(p["lat"], p["lon"], p.get("ele") or 0.0)
            coords.extend([f"{e.x:.3f}", f"{e.y:.3f}", f"{e.z:.3f}"])
        pos_list = ET.SubElement(feat, _QNAME("gml", "posList"))
        pos_list.set("srsDimension", "3")
        pos_list.text = " ".join(coords)
    else:
        gml_pos = ET.SubElement(feat, _QNAME("gml", "pos"))
        gml_pos.set("srsDimension", "3")
        gml_pos.text = f"{ecef.x:.3f} {ecef.y:.3f} {ecef.z:.3f}"

    if tipo == "montagna":
        meas = ET.SubElement(feat, _QNAME("bldg", "measuredHeight"))
        meas.text = str(pos.alt or 0.0)

    for k, v in obj.proprieta.items():
        if k in ("tipo",):
            continue
        attr = ET.SubElement(feat, _QNAME("app", "attribute"))
        name_el = ET.SubElement(attr, _QNAME("app", "name"))
        name_el.text = str(k)
        val_el = ET.SubElement(attr, _QNAME("app", "value"))
        val_el.text = str(v)

    return member


def export_citygml(objects: Iterable[Oggetto], path: str | Path) -> None:
    """Export AetherMap objects as CityGML 2.0 XML.

    Maps AetherMap entity types to CityGML feature types:
    - montagna/edificio -> bldg:Building (gml:pos ECEF)
    - albero -> veg:SolitaryVegetation (gml:pos ECEF)
    - strada/via -> tran:Road (gml:posList ECEF)
    - others -> gen:GenericCityObject (gml:pos ECEF)

    Properties are exported as app:attribute name/value pairs.
    Geometry uses ECEF coordinates with srsDimension=3.
    """
    import xml.etree.ElementTree as ET

    root = ET.Element(_QNAME("core", "CityModel"))
    root.set("xmlns:core", _CG_NS["core"])
    root.set("xmlns:gml", _CG_NS["gml"])
    root.set("xmlns:bldg", _CG_NS["bldg"])
    root.set("xmlns:veg", _CG_NS["veg"])
    root.set("xmlns:tran", _CG_NS["tran"])
    root.set("xmlns:gen", _CG_NS["gen"])
    root.set("xmlns:app", _CG_NS["app"])

    for obj in objects:
        root.append(_obj_to_citygml(obj))

    Path(path).write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(root, encoding="unicode"),
        encoding="utf-8",
    )


def import_citygml(path: str | Path) -> list[Oggetto]:
    """Import AetherMap objects from CityGML 2.0 XML.

    Reads cityObjectMember elements and reconstructs Oggetto instances
    from gml:pos / gml:posList geometry and app:attribute properties.

    Supported feature types:
    - bldg:Building, veg:SolitaryVegetation, tran:Road, gen:GenericCityObject
    """
    import xml.etree.ElementTree as ET

    from aethermap.core.coordinates import ecef_to_geodetic

    try:
        import defusedxml.ElementTree as DefusedET
        tree = DefusedET.parse(path)
    except ImportError:
        tree = ET.parse(path)
    root = tree.getroot()

    objects: list[Oggetto] = []

    for member in root.findall(_QNAME("core", "cityObjectMember")):
        feat = member[0] if len(member) else None
        if feat is None:
            continue

        tag = feat.tag.split("}")[-1] if "}" in feat.tag else feat.tag
        tipo = _REV.get(tag, "oggetto")

        props: dict[str, Any] = {"tipo": tipo}
        for attr in feat.findall(_QNAME("app", "attribute")):
            name_el = attr.find(_QNAME("app", "name"))
            val_el = attr.find(_QNAME("app", "value"))
            if name_el is not None and val_el is not None:
                props[name_el.text or ""] = val_el.text or ""

        pos_el = feat.find(_QNAME("gml", "pos"))
        pos_list_el = feat.find(_QNAME("gml", "posList"))

        if pos_el is not None and pos_el.text:
            parts = pos_el.text.strip().split()
            if len(parts) >= 3:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                geo = ecef_to_geodetic(x, y, z)
                posizione = Posizione(
                    lat=geo.lat,
                    lon=geo.lon,
                    alt=geo.alt,
                )
                geom = Geometria(tipo="punto")
        elif pos_list_el is not None and pos_list_el.text:
            parts = pos_list_el.text.strip().split()
            punti: list[dict[str, Any]] = []
            for i in range(0, len(parts) // 3 * 3, 3):
                x, y, z = float(parts[i]), float(parts[i + 1]), float(parts[i + 2])
                geo = ecef_to_geodetic(x, y, z)
                punti.append({"lat": geo.lat, "lon": geo.lon, "ele": geo.alt})
            posizione = Posizione.from_latlon(punti[0]["lat"], punti[0]["lon"], punti[0]["ele"])
            geom = Geometria(tipo="linea", dati={"punti": punti})
        else:
            continue

        oid = feat.get(_QNAME("gml", "id"), f"obj_{len(objects):06d}")
        objects.append(
            Oggetto(
                id=oid,
                tipo=tipo,
                posizione=posizione,
                geometria=geom,
                proprieta=props,
            )
        )

    return objects
