from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aethermap.ai.models import Confidenza, Geometria, Oggetto, Posizione


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _cube_cell_id_simple(cell_id: str) -> tuple[str, int, int, int]:
    parts = cell_id.split(":")
    face = int(parts[0])
    level = int(parts[1])
    u_int = int(parts[2])
    v_int = int(parts[3])
    return face, level, u_int, v_int


def _cell_prefix(face: int, level: int, u_int: int, v_int: int, bits: int = 16) -> str:
    return f"{face}:{level}:{u_int >> bits}:{v_int >> bits}"


@dataclass
class SpatialIndex:
    s2_map: dict[str, set[str]] = field(default_factory=dict)
    bbox_map: dict[str, list[tuple[float, float, float, float, str]]] = field(
        default_factory=dict
    )

    def insert(self, obj: Oggetto) -> None:
        s2 = obj.posizione.s2 or ""
        if s2:
            face, level, u_int, v_int = _cube_cell_id_simple(s2)
            for bits in (0, 4, 8, 12, 16):
                prefix = f"{face}:{level}:{u_int >> bits}:{v_int >> bits}"
                self.s2_map.setdefault(prefix, set()).add(obj.id)

        lat, lon = obj.posizione.lat, obj.posizione.lon
        alt = getattr(obj.posizione, "alt", 0.0) or 0.0
        self.bbox_map.setdefault(obj.id, []).append((lat, lon, alt, alt, obj.id))

    def remove(self, obj_id: str) -> None:
        for ids in self.s2_map.values():
            ids.discard(obj_id)
        self.bbox_map.pop(obj_id, None)

    def query_s2(self, s2: str) -> set[str]:
        parts = s2.split(":")
        face = parts[0]
        level = parts[1]
        u_int = int(parts[2])
        v_int = int(parts[3])
        result: set[str] = set()
        for bits in (0, 4, 8, 12, 16):
            prefix = f"{face}:{level}:{u_int >> bits}:{v_int >> bits}"
            result.update(self.s2_map.get(prefix, set()))
        return result

    def query_radius(self, lat: float, lon: float, radius_m: float) -> set[str]:
        result: set[str] = set()
        dlat = radius_m / 111_320.0
        dlon = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.1))
        lat0, lat1 = lat - dlat, lat + dlat
        lon0, lon1 = lon - dlon, lon + dlon
        for _oid, boxes in self.bbox_map.items():
            for (la, lo, *_alt, oid2) in boxes:
                if lat0 <= la <= lat1 and lon0 <= lo <= lon1:
                    result.add(oid2)
                    break
        return result


@dataclass
class SpatialStore:
    objects: dict[str, Oggetto] = field(default_factory=dict)
    index: SpatialIndex = field(default_factory=SpatialIndex)

    def add(self, obj: Oggetto) -> None:
        self.objects[obj.id] = obj
        self.index.insert(obj)

    def get(self, oid: str) -> Oggetto | None:
        return self.objects.get(oid)

    def remove(self, oid: str) -> bool:
        obj = self.objects.pop(oid, None)
        if obj is None:
            return False
        self.index.remove(oid)
        return True

    def query_s2(self, s2: str) -> list[Oggetto]:
        ids = self.index.query_s2(s2)
        return [self.objects[i] for i in ids if i in self.objects]

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        ids = self.index.query_radius(lat, lon, radius_m)
        return [self.objects[i] for i in ids if i in self.objects]

    def all(self) -> Iterable[Oggetto]:
        return self.objects.values()

    def ids(self) -> Iterable[str]:
        return self.objects.keys()

    def __len__(self) -> int:
        return len(self.objects)

    def trim_stale(self, now: datetime | None = None) -> int:
        if now is None:
            now = _utcnow()
        removed = 0
        for obj in list(self.objects.values()):
            if obj.stale_after_s is None:
                continue
            cutoff = now.timestamp() - obj.stale_after_s
            if not obj.cronologia:
                continue
            before = len(obj.cronologia)
            obj.cronologia = [
                s for s in obj.cronologia if s.t.timestamp() >= cutoff
            ]
            removed += before - len(obj.cronologia)
        return removed


class WorldStore:
    def __init__(self, store: SpatialStore | None = None) -> None:
        self.store = store or SpatialStore()

    def add(self, obj: Oggetto) -> None:
        self.store.add(obj)

    def get(self, oid: str) -> Oggetto | None:
        return self.store.get(oid)

    def remove(self, oid: str) -> bool:
        return self.store.remove(oid)

    def query_s2(self, s2: str) -> list[Oggetto]:
        return self.store.query_s2(s2)

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        return self.store.query_radius(lat, lon, radius_m)

    def all(self) -> Iterable[Oggetto]:
        return self.store.all()

    @property
    def objects(self) -> dict[str, Oggetto]:
        return self.store.objects

    def to_json(self) -> str:
        return json.dumps(
            [o.model_dump() for o in self.store.objects.values()],
            default=str,
            indent=2,
        )

    def save_geojson(self, path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        features = []
        for obj in self.store.objects.values():
            geom = _oggetto_to_geojson_geometry(obj)
            feature = {
                "type": "Feature",
                "id": obj.id,
                "properties": {
                    "tipo": obj.tipo,
                    "affidabilita": obj.affidabilita.valore,
                    "proprieta": obj.proprieta,
                },
                "geometry": geom,
            }
            features.append(feature)
        fc: dict[str, Any] = {"type": "FeatureCollection", "features": features}
        if metadata:
            fc["metadata"] = metadata
        Path(path).write_text(json.dumps(fc, default=str, indent=2), encoding="utf-8")

    def load_geojson(self, path: str | Path) -> int:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        imported = 0
        for feat in features:
            try:
                obj = _geojson_to_oggetto(feat)
                self.store.add(obj)
                imported += 1
            except Exception:
                continue
        return imported

    def save_parquet(self, path: str | Path) -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb required for parquet export") from exc

        rows = []
        for obj in self.store.objects.values():
            rows.append({
                "id": obj.id,
                "tipo": obj.tipo,
                "lat": obj.posizione.lat,
                "lon": obj.posizione.lon,
                "alt": obj.posizione.alt,
                "s2": obj.posizione.s2 or "",
                "confidence": obj.affidabilita.valore,
                "n_stati": len(obj.cronologia),
            })
        if not rows:
            return
        con = duckdb.connect(":memory:")
        con.execute(
            "CREATE TABLE objects (id VARCHAR, tipo VARCHAR, lat DOUBLE, "
            "lon DOUBLE, alt DOUBLE, s2 VARCHAR, confidence DOUBLE, n_stati INTEGER)"
        )
        for r in rows:
            con.execute(
                "INSERT INTO objects VALUES (?,?,?,?,?,?,?,?)",
                [
                    r["id"], r["tipo"], r["lat"], r["lon"], r["alt"],
                    r["s2"], r["confidence"], r["n_stati"],
                ],
            )
        con.execute(f"COPY objects TO '{path}' (FORMAT PARQUET)")
        con.close()

    def load_parquet(self, path: str | Path) -> int:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb required for parquet import") from exc

        con = duckdb.connect(":memory:")
        df = con.execute(f"SELECT * FROM read_parquet('{path}')").fetchdf()
        imported = 0
        for _, row in df.iterrows():
            try:
                pos = Posizione(
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    alt=float(row.get("alt") or 0.0),
                    s2=row.get("s2") or None,
                )
                obj = Oggetto(
                    id=str(row["id"]),
                    tipo=str(row["tipo"]),
                    posizione=pos,
                    affidabilita=Confidenza(
                        valore=float(row.get("confidence") or 1.0)
                    ),
                )
                self.store.add(obj)
                imported += 1
            except Exception:
                continue
        con.close()
        return imported


def _oggetto_to_geojson_geometry(obj: Oggetto) -> dict:
    g = obj.geometria
    if g.tipo == "linea":
        coords = []
        for p in g.dati.get("punti", []):
            alt = p.get("ele") or 0.0
            coords.append([p["lon"], p["lat"], alt])
        return {"type": "LineString", "coordinates": coords}
    if g.tipo == "punto":
        alt = getattr(obj.posizione, "alt", 0.0) or 0.0
        return {
            "type": "Point",
            "coordinates": [obj.posizione.lon, obj.posizione.lat, alt],
        }
    return {"type": "Point", "coordinates": [obj.posizione.lon, obj.posizione.lat, 0.0]}


def _geojson_to_oggetto(feat: dict) -> Oggetto:
    props = feat.get("properties", {})
    geom = feat.get("geometry", {})
    gtype = geom.get("type", "Point")
    lon, lat = 0.0, 0.0
    alt = 0.0
    if gtype == "Point":
        coords = geom.get("coordinates", [0.0, 0.0])
        lon, lat = float(coords[0]), float(coords[1])
        alt = float(coords[2]) if len(coords) > 2 else 0.0
    elif gtype == "LineString":
        coords = geom.get("coordinates", [])
        if coords:
            lon, lat = float(coords[0][0]), float(coords[0][1])

    posizione = Posizione.from_latlon(lat, lon, alt)
    geometry_dict: dict[str, Any] = {"tipo": "punto"}
    if gtype == "LineString":
        punti = []
        for c in geom.get("coordinates", []):
            punti.append({"lat": float(c[1]), "lon": float(c[0]), "ele": float(c[2]) if len(c) > 2 else None})
        geometry_dict = {"tipo": "linea", "punti": punti}

    from aethermap.ai.models import Confidenza

    return Oggetto(
        id=str(feat.get("id") or props.get("id") or f"obj_{id(feat)}"),
        tipo=props.get("tipo", "oggetto"),
        posizione=posizione,
        geometria=Geometria(**geometry_dict),
        affidabilita=Confidenza(valore=float(props.get("affidabilita", 1.0))),
        proprieta=props.get("proprieta", {}),
    )
