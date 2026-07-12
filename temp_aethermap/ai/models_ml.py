"""AetherMap Fase 3 — stimatore ML minimale ma reale (solo numpy, no sklearn).

Obiettivo: rendere "reale" l'hook ML del ricercatore. Al posto delle pure
euristiche, `RoadPlausibilityEstimator` apprende (offline, deterministico,
senza rete) una mappa da feature del GPX a:
  (a) `road_score`  : quanto il tracciato e' una strada plausibile (0..1)
  (b) `confidence`  : confidenza del modello sulla stima (0..1)

Il modello e' una RIDGE REGRESSION (chiusa, via equazioni normali) su feature
standardizzate, seguita da sigmoide soft-clip. E' addestrato su pochi campioni
SINTETICI generati nel modulo stesso, ma il path di training e' identico a
quello che useremmo su dati reali: feature -> standardizzazione -> minimi
quadrati regolarizzati. Niente `pip install`, niente rete.

Vincoli rispettati:
  - solo numpy (float32 per lo storage dei pesi, double per i calcoli)
  - coordinate via `core/coordinates.py` (cube-sphere / ECEF)
  - deterministico e runnable ovunque

PUNTO DI INNESTO ML (Fase futura): qui sotto, al posto dei campioni sintetici,
si innestera' un vero modello (es. segmentazione da immagini satellitari /
rete su tracciati OSM + raster) che produce le stesse feature o le arricchisce.
L'interfaccia `estimate_gpx(points) -> (plausibility, confidence)` resta fissa,
quindi il ricercatore non cambia quando il modello "vero" subentra.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aethermap.ai.ingest import RawPoint
from aethermap.core.coordinates import geodetic_to_ecef

_EPS = 1e-6
_LAMBDA = 1.0  # regolarizzazione ridge


@dataclass(frozen=True)
class GpxFeatures:
    """Feature estratte da un tracciato GPX (tutte in double, storage float32)."""

    n_points: int
    spanning_deg: float       # estensione spaziale (range lat + range lon)
    elevation_variance: float # varianza quota (m^2)
    spatial_regularity: float # 1 - CV delle lunghezze di segmento (0..1)

    def to_vector(self) -> np.ndarray:
        return np.array(
            [self.n_points, self.spanning_deg, self.elevation_variance,
             self.spatial_regularity],
            dtype=np.float64,
        )


def extract_gpx_features(points: list[RawPoint]) -> GpxFeatures:
    """Estrae le 4 feature del GPX usando ECEF per le distanze spaziali reali."""
    n = len(points)
    if n == 0:
        return GpxFeatures(0, 0.0, 0.0, 0.0)
    if n == 1:
        return GpxFeatures(1, 0.0, 0.0, 0.0)

    lats = np.array([p.lat for p in points], dtype=np.float64)
    lons = np.array([p.lon for p in points], dtype=np.float64)
    span = float((lats.max() - lats.min()) + (lons.max() - lons.min()))

    eles = np.array(
        [p.ele if p.ele is not None else 0.0 for p in points], dtype=np.float64
    )
    elev_var = float(eles.var()) if n > 1 else 0.0

    # regolarita spaziale: 1 - coefficiente di variazione delle lunghezze segmento
    seg = np.zeros(n - 1, dtype=np.float64)
    for i in range(n - 1):
        a = geodetic_to_ecef(points[i].lat, points[i].lon)
        b = geodetic_to_ecef(points[i + 1].lat, points[i + 1].lon)
        dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
        seg[i] = float(np.sqrt(dx * dx + dy * dy + dz * dz))
    seg_mean = float(seg.mean())
    regularity = 1.0 - (float(seg.std()) / seg_mean) if seg_mean > _EPS else 0.0
    regularity = float(np.clip(regularity, 0.0, 1.0))

    return GpxFeatures(n, span, elev_var, regularity)


def _ground_truth(n: np.ndarray, span: np.ndarray,
                  elev: np.ndarray, reg: np.ndarray) -> np.ndarray:
    """Ground-truth sintetico: strada plausibile = tanti punti, regolari,
    poca varianza quota, estensione moderata. Soft (0..1)."""
    c_n = np.clip(n / 100.0, 0.0, 1.0)
    c_span = 1.0 - np.abs(span - 0.03) / 0.20
    c_span = np.clip(c_span, 0.0, 1.0)
    c_elev = 1.0 - np.clip(elev / 500.0, 0.0, 1.0)
    c_reg = np.clip(reg, 0.0, 1.0)
    y = 0.25 * c_n + 0.20 * c_span + 0.25 * c_elev + 0.30 * c_reg
    return np.clip(y, 0.0, 1.0)


class RoadPlausibilityEstimator:
    """Ridge regression allenata su campioni sintetici; stima plausibilita strada.

    Deterministico: training generato con seed fisso. I pesi sono in float32
    (vincolo storage), i calcoli in float64.
    """

    def __init__(self, weights: np.ndarray, mean: np.ndarray, std: np.ndarray,
                 fitted: bool = True) -> None:
        self._w = weights.astype(np.float32)      # (5,) incl. bias, float32
        self._mean = mean.astype(np.float32)      # (4,)
        self._std = np.clip(std.astype(np.float32), _EPS, None)
        self._fitted = fitted

    @classmethod
    def from_synthetic(cls, n_samples: int = 400, seed: int = 42) -> "RoadPlausibilityEstimator":
        """Genera campioni sintetici (strade positive + tracciati spuri) e
        addestra la ridge regression in modo chiuso."""
        rng = np.random.default_rng(seed)
        half = n_samples // 2

        # --- campioni POSITIVI (strade plausibili) ---
        n_pos = rng.integers(30, 300, half)
        span_pos = rng.uniform(0.001, 0.20, half)
        elev_pos = rng.uniform(0.0, 200.0, half)
        reg_pos = rng.uniform(0.55, 0.98, half)

        # --- campioni NEGATIVI (tracciati spuri / rumorosi) ---
        neg = n_samples - half
        n_neg = rng.integers(2, 40, neg)
        span_neg = rng.uniform(0.0001, 0.05, neg)
        elev_neg = rng.uniform(100.0, 2000.0, neg)
        reg_neg = rng.uniform(0.0, 0.50, neg)

        n = np.concatenate([n_pos, n_neg]).astype(np.float64)
        span = np.concatenate([span_pos, span_neg]).astype(np.float64)
        elev = np.concatenate([elev_pos, elev_neg]).astype(np.float64)
        reg = np.concatenate([reg_pos, reg_neg]).astype(np.float64)

        X = np.stack([n, span, elev, reg], axis=1)        # (N, 4)
        y = _ground_truth(n, span, elev, reg)             # (N,)

        # standardizzazione delle feature
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std = np.where(std < _EPS, _EPS, std)
        Xs = (X - mean) / std

        # minimi quadriti regolarizzati (equazioni normali) con bias
        Xb = np.hstack([np.ones((Xs.shape[0], 1), dtype=np.float64), Xs])  # (N,5)
        ata = Xb.T @ Xb + _LAMBDA * np.eye(Xb.shape[1], dtype=np.float64)
        try:
            w = np.linalg.solve(ata, Xb.T @ y)
        except np.linalg.LinAlgError:
            # fallback: pseudoinversa (non dovrebbe accadere con lambda>0)
            w, *_ = np.linalg.lstsq(Xb, y, rcond=None)
            fitted = not np.all(np.isfinite(w))
        else:
            fitted = True

        return cls(weights=w, mean=mean, std=std, fitted=fitted)

    def _standardize(self, feat: GpxFeatures) -> np.ndarray:
        v = feat.to_vector()
        vs = (v - self._mean.astype(np.float64)) / self._std.astype(np.float64)
        return np.concatenate([[1.0], vs])  # bias + features

    def road_score(self, points: list[RawPoint]) -> float:
        """Stima 0..1: quanto il tracciato e' una strada plausibile."""
        if not self._fitted:
            return 0.0
        feat = extract_gpx_features(points)
        if feat.n_points < 2:
            return 0.0
        xb = self._standardize(feat).astype(np.float64)
        w = self._w.astype(np.float64)
        raw = float(xb @ w)
        score = 1.0 / (1.0 + np.exp(-raw))  # sigmoide soft-clip
        return float(np.clip(score, 0.0, 1.0))

    def confidence(self, points: list[RawPoint]) -> float:
        """Confidenza 0..1: certezza del modello (score lontano da 0.5)
        modulata dalla adeguatezza del campione (n. punti)."""
        score = self.road_score(points)
        feat = extract_gpx_features(points)
        # adeguatezza del dato: piu punti -> stima piu affidabile (pavimento 0.5)
        data_adequacy = min(1.0, 0.5 + 0.5 * min(1.0, feat.n_points / 40.0))
        conf = data_adequacy * (0.6 + 0.4 * score)
        return float(np.clip(round(conf, 3), 0.0, 0.98))


_DEFAULT_ESTIMATOR = RoadPlausibilityEstimator.from_synthetic()


def estimate_gpx(points: list[RawPoint]) -> tuple[float, float]:
    """Interfaccia stabile del ricercatore.

    Ritorna (road_plausibility, confidence). Quando un vero modello ML
    (es. segmentazione satellitare + OSM) subentra, basta rimpiazzare
    `_DEFAULT_ESTIMATOR` / questa funzione mantenendo la firma.
    """
    return _DEFAULT_ESTIMATOR.road_score(points), _DEFAULT_ESTIMATOR.confidence(points)
