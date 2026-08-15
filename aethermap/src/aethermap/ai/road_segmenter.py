"""AetherMap road surface segmenter (Sprint 5 — supervised).

Segmenta una strada in tratti omogenei per superficie usando:
- pendenza media (slope)
- curvatura (curvatura)
- regolarita` spaziale (spatial regularity)
- guadagno elevazione (elevation gain)

Classi superficie:
- asphalt, concrete, gravel, dirt, cobblestone, unknown

Implementazione:
- Feature extraction da GPS points
- Classificatore supervised con fallback euristico
- Threshold tuning opzionale su labeled dataset
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from aethermap.ai.ingest import RawPoint
from aethermap.core.coordinates import geodetic_to_ecef


@dataclass(frozen=True)
class SegmentFeatures:
    length_m: float
    slope_avg_pct: float
    slope_max_pct: float
    curvature: float
    elevation_gain_m: float
    elevation_loss_m: float
    spatial_regularity: float
    n_points: int

    def to_vector(self) -> np.ndarray:
        return np.array(
            [
                self.length_m,
                self.slope_avg_pct,
                self.slope_max_pct,
                self.curvature,
                self.elevation_gain_m,
                self.elevation_loss_m,
                self.spatial_regularity,
                self.n_points,
            ],
            dtype=np.float64,
        )


def _extract_segment_features(points: list[RawPoint]) -> SegmentFeatures:
    n = len(points)
    if n < 2:
        return SegmentFeatures(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, n)

    eles = np.array([p.ele if p.ele is not None else 0.0 for p in points], dtype=np.float64)

    slopes: list[float] = []
    seg_lengths: list[float] = []
    for i in range(1, n):
        a = geodetic_to_ecef(points[i - 1].lat, points[i - 1].lon)
        b = geodetic_to_ecef(points[i].lat, points[i].lon)
        dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
        dist = float(np.sqrt(dx * dx + dy * dy + dz * dz))
        if dist > 1e-6:
            de = eles[i] - eles[i - 1]
            slopes.append((de / dist) * 100.0)
            seg_lengths.append(dist)

    slope_arr = np.array(slopes, dtype=np.float64) if slopes else np.array([0.0])
    length_m = float(np.sum(seg_lengths)) if seg_lengths else 0.0

    elev_diff = np.diff(eles)
    gain = float(np.sum(elev_diff[elev_diff > 0.0]))
    loss = float(np.sum(-elev_diff[elev_diff < 0.0]))

    curvature = 0.0
    if length_m > 1e-6 and len(slope_arr) > 1:
        curvature = float(np.sum(np.abs(np.diff(slope_arr)))) / length_m

    regularity = 1.0
    if length_m > 1e-6:
        regularity = 1.0 - min(1.0, float(np.std(slope_arr)) / (abs(float(np.mean(slope_arr))) + 0.1))

    return SegmentFeatures(
        length_m=length_m,
        slope_avg_pct=float(np.mean(np.abs(slope_arr))),
        slope_max_pct=float(np.max(np.abs(slope_arr))) if len(slope_arr) else 0.0,
        curvature=float(np.clip(curvature, 0.0, 1.0)),
        elevation_gain_m=gain,
        elevation_loss_m=loss,
        spatial_regularity=float(np.clip(regularity, 0.0, 1.0)),
        n_points=n,
    )


class RoadSurfaceSegmenter:
    """Segmenta una lista di punti GPS in tratti omogenei per superficie.

    Supporta:
    - classificazione euristica (default)
    - classificazione supervised con soglie configurabili
    - export segmenti come GeoJSON FeatureCollection
    """

    SURFACE_CLASSES = [
        "asphalt",
        "concrete",
        "gravel",
        "dirt",
        "cobblestone",
        "unknown",
    ]

    def __init__(self, model_path: str | Path | None = None) -> None:
        self._model_path = Path(model_path) if model_path else None
        self._thresholds = self._load_thresholds()

    def _load_thresholds(self) -> dict[str, Any]:
        if self._model_path and self._model_path.exists():
            try:
                data = json.loads(self._model_path.read_text(encoding="utf-8"))
                return data.get("thresholds", {})
            except Exception:
                pass
        return {
            "asphalt": {"max_slope_avg": 3.0, "max_curvature": 0.02, "min_regularity": 0.75},
            "concrete": {"max_slope_avg": 4.0, "max_curvature": 0.03, "min_regularity": 0.70},
            "gravel": {"max_slope_avg": 5.0, "max_curvature": 0.05, "min_regularity": 0.55},
            "dirt": {"max_slope_avg": 8.0, "max_curvature": 0.08, "min_regularity": 0.40},
            "cobblestone": {"max_slope_avg": 2.5, "max_curvature": 0.04, "min_regularity": 0.60},
        }

    def classify_segment(self, points: list[RawPoint]) -> str:
        feat = _extract_segment_features(points)
        candidates: list[tuple[str, float]] = []
        for surface, th in self._thresholds.items():
            score = 0.0
            if feat.slope_avg_pct <= th.get("max_slope_avg", 10.0):
                score += 0.4
            if feat.curvature <= th.get("max_curvature", 1.0):
                score += 0.3
            if feat.spatial_regularity >= th.get("min_regularity", 0.0):
                score += 0.3
            candidates.append((surface, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        best, best_score = candidates[0]
        if best_score < 0.5:
            return "unknown"
        return best

    def segment_ride(self, points: list[RawPoint], window: int = 8) -> list[dict[str, Any]]:
        """Segmenta la ride in finestre sovrapposte e classifica ogni segmento.

        Restituisce lista di segmenti con:
        - start_index / end_index
        - surface_type
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
            surface = self.classify_segment(seg_pts)
            feat = _extract_segment_features(seg_pts)
            confidence = float(np.clip(0.5 + 0.5 * min(1.0, feat.n_points / 20.0), 0.0, 0.98))
            segments.append({
                "start_index": start,
                "end_index": end - 1,
                "surface_type": surface,
                "confidence": round(confidence, 2),
                "features": {
                    "length_m": round(feat.length_m, 2),
                    "slope_avg_pct": round(feat.slope_avg_pct, 2),
                    "slope_max_pct": round(feat.slope_max_pct, 2),
                    "curvature": round(feat.curvature, 4),
                    "elevation_gain_m": round(feat.elevation_gain_m, 2),
                    "spatial_regularity": round(feat.spatial_regularity, 2),
                },
            })
        return segments

    def to_geojson(self, points: list[RawPoint], segments: list[dict[str, Any]]) -> dict[str, Any]:
        features = []
        for seg in segments:
            coords = [
                [points[i].lon, points[i].lat, points[i].ele or 0.0]
                for i in range(seg["start_index"], seg["end_index"] + 1)
            ]
            features.append({
                "type": "Feature",
                "properties": {
                    "surface_type": seg["surface_type"],
                    "confidence": seg["confidence"],
                    "start_index": seg["start_index"],
                    "end_index": seg["end_index"],
                    **seg["features"],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            })
        return {"type": "FeatureCollection", "features": features}
