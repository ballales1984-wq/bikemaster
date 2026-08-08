"""AetherMap traffic classifier (Sprint 5 — unsupervised).

Classifica il traffico su una strada da pattern di velocita` GPS:
- stopped / slow / moderate / fast / free_flow

Implementazione:
- Calcolo statistica velocita` per segmento
- Clustering non supervisionato con threshold configurabili
- Export segmenti traffico come GeoJSON FeatureCollection
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from aethermap.ai.ingest import RawPoint


@dataclass(frozen=True)
class TrafficFeatures:
    avg_speed_kmh: float
    max_speed_kmh: float
    min_speed_kmh: float
    speed_std: float
    stops: int
    length_m: float
    duration_s: float

    def to_vector(self) -> np.ndarray:
        return np.array(
            [
                self.avg_speed_kmh,
                self.max_speed_kmh,
                self.min_speed_kmh,
                self.speed_std,
                float(self.stops),
                self.length_m,
                self.duration_s,
            ],
            dtype=np.float64,
        )


def _extract_traffic_features(points: list[RawPoint]) -> TrafficFeatures:
    n = len(points)
    if n < 2:
        return TrafficFeatures(0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0)

    speeds: list[float] = []
    for p in points:
        if p.speed is not None:
            speeds.append(float(p.speed))
    if not speeds:
        return TrafficFeatures(0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0)

    speed_arr = np.array(speeds, dtype=np.float64)
    stops = int(np.sum(speed_arr < 1.0))

    length_m = 0.0
    if n >= 2:
        for i in range(1, n):
            lat1, lon1 = points[i - 1].lat, points[i - 1].lon
            lat2, lon2 = points[i].lat, points[i].lon
            length_m += float(np.sqrt(
                (lat1 - lat2) ** 2 + (lon1 - lon2) ** 2
            )) * 111_320.0

    duration_s = 0.0
    if n >= 2 and points[0].t and points[-1].t:
        try:
            diff = points[-1].t - points[0].t
            duration_s = max(0.0, diff.total_seconds())
        except Exception:
            pass

    return TrafficFeatures(
        avg_speed_kmh=float(np.mean(speed_arr)),
        max_speed_kmh=float(np.max(speed_arr)),
        min_speed_kmh=float(np.min(speed_arr)),
        speed_std=float(np.std(speed_arr)),
        stops=stops,
        length_m=length_m,
        duration_s=duration_s,
    )


class TrafficClassifier:
    """Classifica il traffico da pattern di velocita` GPS.

    Classi:
    - free_flow: velocita` alta, bassa variabilita`
    - moderate: velocita` media, variabilita` contenuta
    - slow: velocita` bassa, possibili soste
    - congested: velocita` molto bassa, alta variabilita`, molte soste
    """

    CLASSES = ["free_flow", "moderate", "slow", "congested"]

    def __init__(self, thresholds_path: str | Path | None = None) -> None:
        self._thresholds = self._load_thresholds(thresholds_path)

    def _load_thresholds(self, path: str | Path | None) -> dict[str, Any]:
        if path and Path(path).exists():
            try:
                return json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "free_flow": {"min_avg_speed_kmh": 20.0, "max_speed_std": 5.0, "max_stops": 1},
            "moderate": {"min_avg_speed_kmh": 10.0, "max_speed_std": 8.0, "max_stops": 3},
            "slow": {"min_avg_speed_kmh": 3.0, "max_speed_std": 12.0, "max_stops": 6},
            "congested": {"min_avg_speed_kmh": 0.0, "max_speed_std": 20.0, "max_stops": 999},
        }

    def classify_segment(self, points: list[RawPoint]) -> str:
        feat = _extract_traffic_features(points)
        for cls_name in ["free_flow", "moderate", "slow"]:
            th = self._thresholds.get(cls_name, {})
            if (feat.avg_speed_kmh >= th.get("min_avg_speed_kmh", 0.0)
                    and feat.speed_std <= th.get("max_speed_std", 999.0)
                    and feat.stops <= th.get("max_stops", 999)):
                return cls_name
        return "congested"

    def classify_ride(self, points: list[RawPoint], window: int = 12) -> list[dict[str, Any]]:
        """Classifica il traffico su finestre sovrapposte della ride.

        Restituisce segmenti con:
        - start_index / end_index
        - traffic_level
        - confidence
        - features
        """
        if len(points) < 2:
            return []

        segments: list[dict[str, Any]] = []
        step = max(1, window // 2)
        for start in range(0, len(points) - 1, step):
            end = min(start + window, len(points))
            seg_pts = points[start:end]
            traffic = self.classify_segment(seg_pts)
            feat = _extract_traffic_features(seg_pts)
            confidence = float(np.clip(0.5 + 0.5 * min(1.0, feat.duration_s / 60.0), 0.0, 0.98))
            segments.append({
                "start_index": start,
                "end_index": end - 1,
                "traffic_level": traffic,
                "confidence": round(confidence, 2),
                "features": {
                    "avg_speed_kmh": round(feat.avg_speed_kmh, 2),
                    "max_speed_kmh": round(feat.max_speed_kmh, 2),
                    "min_speed_kmh": round(feat.min_speed_kmh, 2),
                    "speed_std": round(feat.speed_std, 2),
                    "stops": feat.stops,
                    "length_m": round(feat.length_m, 2),
                    "duration_s": round(feat.duration_s, 2),
                },
            })
        return segments

    def to_geojson(self, points: list[RawPoint], segments: list[dict[str, Any]]) -> dict[str, Any]:
        traffic_colors = {
            "free_flow": "#2ecc71",
            "moderate": "#f1c40f",
            "slow": "#e67e22",
            "congested": "#e74c3c",
        }
        features = []
        for seg in segments:
            coords = [
                [points[i].lon, points[i].lat, points[i].ele or 0.0]
                for i in range(seg["start_index"], seg["end_index"] + 1)
            ]
            features.append({
                "type": "Feature",
                "properties": {
                    "traffic_level": seg["traffic_level"],
                    "confidence": seg["confidence"],
                    "start_index": seg["start_index"],
                    "end_index": seg["end_index"],
                    "color": traffic_colors.get(seg["traffic_level"], "#95a5a6"),
                    **seg["features"],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            })
        return {"type": "FeatureCollection", "features": features}
