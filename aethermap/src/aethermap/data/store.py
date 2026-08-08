from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aethermap.ai.models import Oggetto
from aethermap.data.db import AetherMapDB


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _cube_cell_id_simple(cell_id: str) -> tuple[int, int, int, int]:
    parts = cell_id.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid cube cell id format: {cell_id}")
    face = int(parts[0])
    level = int(parts[1])
    u_int = int(parts[2])
    v_int = int(parts[3])
    return face, level, u_int, v_int


def _s2_prefixes(s2_token: str) -> list[str]:
    prefixes: list[str] = []
    for length in (4, 8, 12, 16, 20, 24):
        if len(s2_token) > length:
            prefixes.append(s2_token[:length])
    return prefixes


def _h3_prefixes(h3_token: str) -> list[str]:
    prefixes: list[str] = []
    for length in (5, 7, 9, 11, 13):
        if len(h3_token) > length:
            prefixes.append(h3_token[:length])
    return prefixes


@dataclass
class SpatialIndex:
    s2_map: dict[str, set[str]] = field(default_factory=dict)
    h3_map: dict[str, set[str]] = field(default_factory=dict)
    bbox_map: dict[str, list[tuple[float, float, float, float, str]]] = field(
        default_factory=dict
    )

    def insert(self, obj: Oggetto) -> None:
        h3 = getattr(obj.posizione, "h3", None)
        if h3:
            self.h3_map.setdefault(h3, set()).add(obj.id)
            for prefix in _h3_prefixes(h3):
                self.h3_map.setdefault(prefix, set()).add(obj.id)

        s2 = obj.posizione.s2
        if not s2:
            return
        if ":" in s2:
            try:
                face, level, u_int, v_int = _cube_cell_id_simple(s2)
                for bits in (0, 4, 8, 12, 16):
                    prefix = f"{face}:{level}:{u_int >> bits}:{v_int >> bits}"
                    self.s2_map.setdefault(prefix, set()).add(obj.id)
                return
            except (ValueError, TypeError):
                pass
        self.s2_map.setdefault(s2, set()).add(obj.id)
        for prefix in _s2_prefixes(s2):
            self.s2_map.setdefault(prefix, set()).add(obj.id)

        lat, lon = obj.posizione.lat, obj.posizione.lon
        alt = getattr(obj.posizione, "alt", 0.0) or 0.0
        self.bbox_map.setdefault(obj.id, []).append((lat, lon, alt, alt, obj.id))

    def remove(self, obj_id: str) -> None:
        for ids in self.s2_map.values():
            ids.discard(obj_id)
        for ids in self.h3_map.values():
            ids.discard(obj_id)
        self.bbox_map.pop(obj_id, None)

    def query_s2(self, s2: str) -> set[str]:
        if not s2:
            return set()
        result: set[str] = set()
        if ":" in s2:
            try:
                face, level, u_int, v_int = _cube_cell_id_simple(s2)
                for bits in (0, 4, 8, 12, 16):
                    prefix = f"{face}:{level}:{u_int >> bits}:{v_int >> bits}"
                    result.update(self.s2_map.get(prefix, set()))
                return result
            except (ValueError, TypeError):
                pass
        result.update(self.s2_map.get(s2, set()))
        for prefix in _s2_prefixes(s2):
            result.update(self.s2_map.get(prefix, set()))
        return result

    def query_h3(self, h3: str) -> set[str]:
        if not h3:
            return set()
        result: set[str] = set()
        result.update(self.h3_map.get(h3, set()))
        for prefix in _h3_prefixes(h3):
            result.update(self.h3_map.get(prefix, set()))
        return result

    def query_radius(self, lat: float, lon: float, radius_m: float) -> set[str]:
        result: set[str] = set()
        dlat = radius_m / 111_320.0
        dlon = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.1))
        lat0, lat1 = lat - dlat, lat + dlat
        lon0, lon1 = lon - dlon, lon + dlon
        for _, boxes in self.bbox_map.items():
            for (la, lo, *_alt, oid2) in boxes:
                if lat0 <= la <= lat1 and lon0 <= lo <= lon1:
                    result.add(oid2)
                    break
        return result

    def query_bounds(self, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> set[str]:
        result: set[str] = set()
        for oid, boxes in self.bbox_map.items():
            for (la, lo, *_alt, oid2) in boxes:
                if lat_min <= la <= lat_max and lon_min <= lo <= lon_max:
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

    def query_h3(self, h3: str) -> list[Oggetto]:
        ids = self.index.query_h3(h3)
        return [self.objects[i] for i in ids if i in self.objects]

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        ids = self.index.query_radius(lat, lon, radius_m)
        return [self.objects[i] for i in ids if i in self.objects]

    def query_bounds(self, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> list[Oggetto]:
        ids = self.index.query_bounds(lat_min, lat_max, lon_min, lon_max)
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

    def query_h3(self, h3: str) -> list[Oggetto]:
        return self.store.query_h3(h3)

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        return self.store.query_radius(lat, lon, radius_m)

    def query_bounds(self, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> list[Oggetto]:
        return self.store.query_bounds(lat_min, lat_max, lon_min, lon_max)

    def all(self) -> Iterable[Oggetto]:
        return self.store.all()

    @property
    def objects(self) -> dict[str, Oggetto]:
        return self.store.objects

    def to_json(self) -> str:
        return json.dumps([o.model_dump() for o in self.store.objects.values()], default=str, indent=2)

    def save_geojson(self, path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        from aethermap.data.io import export_geojson
        export_geojson(self.store.objects.values(), path, metadata)

    def load_geojson(self, path: str | Path) -> int:
        from aethermap.data.io import import_geojson
        imported = 0
        for obj in import_geojson(path):
            self.store.add(obj)
            imported += 1
        return imported

    def save_parquet(self, path: str | Path) -> None:
        from aethermap.data.io import export_parquet
        export_parquet(self.store.objects.values(), path)

    def load_parquet(self, path: str | Path) -> int:
        try:
            import duckdb  # noqa: F401  # used for availability test
        except ImportError as exc:
            raise RuntimeError("duckdb required for parquet import") from exc

        from aethermap.data.io import import_parquet
        imported = 0
        for obj in import_parquet(path):
            self.store.add(obj)
            imported += 1
        return imported


class PersistentStore:
    def __init__(self, store: SpatialStore | None = None, db_path: str | Path | None = None) -> None:
        self.store = store or SpatialStore()
        self.db = AetherMapDB(db_path)
        self._load_from_db()

    def _load_from_db(self) -> None:
        for obj in self.db.iter_objects():
            self.store.add(obj)

    def add(self, obj: Oggetto) -> None:
        self.store.add(obj)
        self.db.add(obj)

    def get(self, oid: str) -> Oggetto | None:
        return self.store.get(oid)

    def remove(self, oid: str) -> bool:
        ok = self.store.remove(oid)
        if ok:
            self.db.remove(oid)
        return ok

    def query_s2(self, s2: str) -> list[Oggetto]:
        return self.store.query_s2(s2)

    def query_h3(self, h3: str) -> list[Oggetto]:
        return self.store.query_h3(h3)

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        return self.store.query_radius(lat, lon, radius_m)

    def query_bounds(self, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> list[Oggetto]:
        return self.store.query_bounds(lat_min, lat_max, lon_min, lon_max)

    def all(self) -> Iterable[Oggetto]:
        return self.store.all()

    @property
    def objects(self) -> dict[str, Oggetto]:
        return self.store.objects

    def sync_all(self) -> None:
        for obj in self.store.all():
            self.db.add(obj)

    def count(self) -> int:
        return len(self.store)

    def db_count(self) -> int:
        return self.db.count()

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> PersistentStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
