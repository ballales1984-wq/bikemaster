from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator, Iterator

from aethermap.ai.models import Oggetto, Stato


_DB_FILENAME = "aethermap.db"
_SCHEMA_VERSION = 1

_CREATE_OBJECTS = """\
CREATE TABLE IF NOT EXISTS objects (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    alt REAL DEFAULT 0.0,
    s2 TEXT,
    h3 TEXT,
    cube_face INTEGER,
    cube_u REAL,
    cube_v REAL,
    data JSON NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
)
"""

_CREATE_STATE_HISTORY = """\
CREATE TABLE IF NOT EXISTS state_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id TEXT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    campi JSON NOT NULL,
    t TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0
)
"""

_CREATE_META = """\
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

_CREATE_IDX_TIPO = "CREATE INDEX IF NOT EXISTS idx_objects_tipo ON objects(tipo)"
_CREATE_IDX_S2 = "CREATE INDEX IF NOT EXISTS idx_objects_s2 ON objects(s2)"
_CREATE_IDX_H3 = "CREATE INDEX IF NOT EXISTS idx_objects_h3 ON objects(h3)"

_INSERT_OBJECT = """\
INSERT OR REPLACE INTO objects (id, tipo, lat, lon, alt, s2, h3, cube_face, cube_u, cube_v, data)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE_TIMESTAMP = """\
UPDATE objects SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?
"""

_DELETE_OBJECT = "DELETE FROM objects WHERE id = ?"
_DELETE_HISTORY = "DELETE FROM state_history WHERE object_id = ?"

_INSERT_STATE = """\
INSERT INTO state_history (object_id, campi, t, confidence)
VALUES (?, ?, ?, ?)
"""

_GET_ALL_OBJECTS = "SELECT data FROM objects"
_GET_OBJECT_BY_ID = "SELECT data FROM objects WHERE id = ?"
_GET_OBJECTS_BY_TIPO = "SELECT data FROM objects WHERE tipo = ?"
_GET_STATES = "SELECT campi, t, confidence FROM state_history WHERE object_id = ? ORDER BY t"

_RADIUS_QUERY = """\
SELECT data FROM objects
WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
"""


def _serialize(obj: Oggetto) -> dict[str, Any]:
    return obj.model_dump(mode="json")


def _deserialize(data: dict[str, Any]) -> Oggetto:
    return Oggetto.model_validate(data)


def _datetime_to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _iso_to_datetime(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


class AetherMapDB:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = (
                Path(__file__).resolve().parent.parent.parent.parent.parent / _DB_FILENAME
            )
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(_CREATE_OBJECTS)
        cur.execute(_CREATE_STATE_HISTORY)
        cur.execute(_CREATE_META)
        cur.execute(_CREATE_IDX_TIPO)
        cur.execute(_CREATE_IDX_S2)
        cur.execute(_CREATE_IDX_H3)
        self._conn.commit()
        self._set_meta("schema_version", str(_SCHEMA_VERSION))

    def _set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    def _get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def add(self, obj: Oggetto) -> None:
        data = _serialize(obj)
        pos = obj.posizione
        with self._transaction() as cur:
            cur.execute(
                _INSERT_OBJECT,
                (
                    obj.id,
                    obj.tipo,
                    pos.lat,
                    pos.lon,
                    getattr(pos, "alt", 0.0) or 0.0,
                    pos.s2,
                    pos.h3,
                    pos.cube_face,
                    pos.cube_u,
                    pos.cube_v,
                    json.dumps(data, default=str),
                ),
            )
            cur.execute(_UPDATE_TIMESTAMP, (obj.id,))
            for stato in obj.cronologia:
                cur.execute(
                    _INSERT_STATE,
                    (
                        obj.id,
                        json.dumps(stato.campi, default=str),
                        _datetime_to_iso(stato.t),
                        stato.confidence,
                    ),
                )

    def remove(self, obj_id: str) -> bool:
        with self._transaction() as cur:
            cur.execute(_DELETE_HISTORY, (obj_id,))
            cur.execute(_DELETE_OBJECT, (obj_id,))
            return cur.rowcount > 0

    def get(self, obj_id: str) -> Oggetto | None:
        row = self._conn.execute(_GET_OBJECT_BY_ID, (obj_id,)).fetchone()
        if row is None:
            return None
        data = json.loads(row["data"])
        obj = _deserialize(data)
        states = self._conn.execute(_GET_STATES, (obj_id,)).fetchall()
        obj.cronologia = [
            Stato(
                campi=json.loads(s["campi"]),
                t=_iso_to_datetime(s["t"]),
                confidence=s["confidence"],
            )
            for s in states
        ]
        return obj

    def get_by_tipo(self, tipo: str) -> list[Oggetto]:
        rows = self._conn.execute(_GET_OBJECTS_BY_TIPO, (tipo,)).fetchall()
        return [_deserialize(json.loads(r["data"])) for r in rows]

    def iter_objects(self) -> Iterator[Oggetto]:
        for row in self._conn.execute(_GET_ALL_OBJECTS):
            yield _deserialize(json.loads(row["data"]))

    def all_objects(self) -> list[Oggetto]:
        return list(self.iter_objects())

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM objects").fetchone()
        return row["n"]

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        dlat = radius_m / 111_320.0
        dlon = radius_m / (
            111_320.0 * max(abs(math.cos(math.radians(lat))), 0.1)
        )
        lat0, lat1 = lat - dlat, lat + dlat
        lon0, lon1 = lon - dlon, lon + dlon
        rows = self._conn.execute(
            _RADIUS_QUERY,
            (lat0, lat1, lon0, lon1),
        ).fetchall()
        return [_deserialize(json.loads(r["data"])) for r in rows]

    def vacuum(self) -> None:
        self._conn.execute("VACUUM")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> AetherMapDB:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
