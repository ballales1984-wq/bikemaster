from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator


@dataclass
class RawPoint:
    lat: float
    lon: float
    ele: float | None = None
    t: datetime | None = None


@dataclass
class RawFeature:
    tipo: str
    posizione: tuple[float, float]
    payload: dict[str, Any]


def ingest_gpx(path: str) -> list[RawPoint]:
    tree = defusedxml.etree.ElementTree.parse(path)
    root = tree.getroot()
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    points: list[RawPoint] = []
    for trkpt in root.iter("{http://www.topografix.com/GPX/1/1}trkpt"):
        lat = float(trkpt.get("lat"))
        lon = float(trkpt.get("lon"))
        ele_el = trkpt.find("g:ele", ns)
        time_el = trkpt.find("g:time", ns)
        ele = float(ele_el.text) if ele_el is not None and ele_el.text else None
        t = datetime.fromisoformat(time_el.text.replace("Z", "+00:00")) if time_el is not None and time_el.text else None
        points.append(RawPoint(lat=lat, lon=lon, ele=ele, t=t))
    return points


def ingest_satellite_stub(bbox: tuple[float, float, float, float]) -> list[RawFeature]:
    lat0, lon0, lat1, lon1 = bbox
    return [
        RawFeature("edificio", ((lat0 + lat1) / 2, (lon0 + lon1) / 2),
                   {"piani_stimati": 3, "confidenza_sorgente": 0.6}),
    ]


def ingest_public_stub(region: str) -> list[RawFeature]:
    return [RawFeature("via", (0.0, 0.0), {"nome": f"via in {region}", "pubblico": True})]


def ingest_sensor_stream_stub(n: int = 5) -> Iterator[RawFeature]:
    for i in range(n):
        yield RawFeature("sensore_traffico", (45.0 + i * 0.001, 9.0 + i * 0.001),
                         {"traffico": (i * 20) % 100})
