"""AetherMap Fase 3 — estimatore ML minimale ma reale (solo numpy, no sklearn).

Obiettivo: rendere "reale" l'hook ML del ricercatore. Due modelli:
1. Ridge regression lineare (chiusa, veloce, interpretabile) — default.
2. SimpleNN: rete densa 1-hidden-layer (8 neuroni, ReLU) con mini-batch SGD,
   serializzabile in JSON, riutilizzabile senza riaddestramento.

Vincoli rispettati:
  - solo numpy (float32 storage, float64 calcoli)
  - coordinate via `core/coordinates.py`
  - deterministico e runnable ovunque
  - persistenza JSON: il modello puo' essere salvato/ caricato

Interfaccia stabile: `estimate_gpx(points) -> (plausibility, confidence)`.
Quando un modello vero subentra, basta rimpiazzare `_load_default_model()`.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aethermap.ai.ingest import RawPoint
from aethermap.core.coordinates import geodetic_to_ecef

_EPS = 1e-6
_LAMBDA = 1.0  # regolarizzazione ridge
_MODEL_VERSION = "aethermap-ml-1.0"


# =========================
# Feature engineering
# =========================

@dataclass(frozen=True)
class GpxFeatures:
    n_points: int
    spanning_deg: float
    elevation_variance: float
    spatial_regularity: float

    def to_vector(self) -> np.ndarray:
        return np.array(
            [self.n_points, self.spanning_deg, self.elevation_variance,
             self.spatial_regularity],
            dtype=np.float64,
        )


def extract_gpx_features(points: list[RawPoint]) -> GpxFeatures:
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


# =========================
# Ground truth sintetico
# =========================

def _ground_truth(n: np.ndarray, span: np.ndarray,
                  elev: np.ndarray, reg: np.ndarray) -> np.ndarray:
    c_n = np.clip(n / 100.0, 0.0, 1.0)
    c_span = 1.0 - np.abs(span - 0.03) / 0.20
    c_span = np.clip(c_span, 0.0, 1.0)
    c_elev = 1.0 - np.clip(elev / 500.0, 0.0, 1.0)
    c_reg = np.clip(reg, 0.0, 1.0)
    y = 0.25 * c_n + 0.20 * c_span + 0.25 * c_elev + 0.30 * c_reg
    return np.clip(y, 0.0, 1.0)


# =========================
# SimpleNN (numpy-only)
# =========================

class SimpleNN:
    """Rete neurale densa 1-hidden-layer con mini-batch SGD.

    Architettura:
      input(4) -> Linear(8) + ReLU -> Linear(1) + Sigmoid
    """

    def __init__(self, input_size: int = 4, hidden_size: int = 8,
                 seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self._W1 = rng.normal(0, math.sqrt(2.0 / input_size),
                              (input_size, hidden_size)).astype(np.float32)
        self._b1 = np.zeros(hidden_size, dtype=np.float32)
        self._W2 = rng.normal(0, math.sqrt(2.0 / hidden_size),
                              (hidden_size, 1)).astype(np.float32)
        self._b2 = np.zeros(1, dtype=np.float32)

    @property
    def weights(self) -> dict:
        return {
            "W1": self._W1.tolist(),
            "b1": self._b1.tolist(),
            "W2": self._W2.tolist(),
            "b2": self._b2.tolist(),
        }

    @weights.setter
    def weights(self, data: dict) -> None:
        self._W1 = np.array(data["W1"], dtype=np.float32)
        self._b1 = np.array(data["b1"], dtype=np.float32)
        self._W2 = np.array(data["W2"], dtype=np.float32)
        self._b2 = np.array(data["b2"], dtype=np.float32)

    def _forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        z1 = x @ self._W1 + self._b1
        a1 = np.maximum(0.0, z1)
        z2 = a1 @ self._W2 + self._b2
        a2 = 1.0 / (1.0 + np.exp(-z2))
        return z1, a1, a2

    def predict(self, x: np.ndarray) -> np.ndarray:
        _, _, a2 = self._forward(x)
        return a2

    def train_step(self, x: np.ndarray, y: np.ndarray,
                   lr: float = 0.01) -> float:
        m = x.shape[0]
        z1, a1, a2 = self._forward(x)
        loss = float(np.mean((a2 - y) ** 2))

        dz2 = (a2 - y) / m
        dW2 = a1.T @ dz2
        db2 = dz2.sum(axis=0)
        da1 = dz2 @ self._W2.T
        dz1 = da1 * (z1 > 0.0).astype(np.float32)
        dW1 = x.T @ dz1
        db1 = dz1.sum(axis=0)

        self._W2 -= lr * dW2.astype(np.float32)
        self._b2 -= lr * db2.astype(np.float32)
        self._W1 -= lr * dW1.astype(np.float32)
        self._b1 -= lr * db1.astype(np.float32)

        return loss

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 200,
            batch_size: int = 16, lr: float = 0.01,
            val_split: float = 0.2, seed: int = 42) -> dict:
        rng = np.random.default_rng(seed)
        n = len(X)
        idx = rng.permutation(n)
        X, y = X[idx], y[idx]
        split = int(n * (1.0 - val_split))
        X_tr, y_tr = X[:split], y[:split]
        X_val, y_val = X[split:], y[split:] if split < n else (X[:0], y[:0])

        history = {"train_loss": [], "val_loss": []}
        for _ in range(epochs):
            bidx = rng.permutation(len(X_tr))
            for start in range(0, len(X_tr), batch_size):
                batch = bidx[start:start + batch_size]
                self.train_step(X_tr[batch], y_tr[batch], lr)
            history["train_loss"].append(
                float(np.mean((self.predict(X_tr) - y_tr) ** 2)))
            if len(X_val) > 0:
                history["val_loss"].append(
                    float(np.mean((self.predict(X_val) - y_val) ** 2)))
        return history


# =========================
# Model persistence
# =========================

def _model_to_dict(model_type: str, weights, mean, std, fitted: bool,
                   input_size: int = 4) -> dict:
    return {
        "version": _MODEL_VERSION,
        "type": model_type,
        "input_size": input_size,
        "weights": weights.tolist() if isinstance(weights, np.ndarray) else weights,
        "mean": mean.tolist() if isinstance(mean, np.ndarray) else mean,
        "std": std.tolist() if isinstance(std, np.ndarray) else std,
        "fitted": fitted,
    }


def _model_from_dict(data: dict):
    model_type = data["type"]
    weights = np.array(data["weights"], dtype=np.float32)
    mean = np.array(data["mean"], dtype=np.float32)
    std = np.array(data["std"], dtype=np.float32)
    fitted = data.get("fitted", True)
    if model_type == "nn":
        nn = SimpleNN(input_size=data.get("input_size", 4))
        nn.weights = data["weights"]
        return nn, mean, std, fitted
    return weights, mean, std, fitted


def save_model(estimator: RoadPlausibilityEstimator, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(_model_to_dict("linear", estimator._w, estimator._mean,
                                  estimator._std, estimator._fitted)),
        encoding="utf-8",
    )


def load_model(path: str | Path) -> RoadPlausibilityEstimator:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    weights, mean, std, fitted = _model_from_dict(data)
    if isinstance(weights, dict):
        return RoadPlausibilityEstimator(nn=weights["W1"].__class__.__name__,
                                         mean=mean, std=std, fitted=fitted)
    return RoadPlausibilityEstimator(weights=weights, mean=mean, std=std,
                                     fitted=fitted)


# =========================
# Estimator (ridge + NN option)
# =========================

class RoadPlausibilityEstimator:
    """Stima plausibilita' di una strada da feature GPX.

    Due modalita':
      - linear (default): ridge regression chiusa, veloce.
      - nn: SimpleNN addestrato via mini-batch SGD, serializzabile.
    """

    def __init__(self, weights: np.ndarray | None = None,
                 mean: np.ndarray | None = None,
                 std: np.ndarray | None = None,
                 nn: SimpleNN | None = None,
                 fitted: bool = True) -> None:
        if nn is not None:
            self._nn = nn
            self._w = np.zeros(5, dtype=np.float32)
            self._mean = (mean if mean is not None else
                          np.zeros(4, dtype=np.float32))
            self._std = np.clip(std if std is not None else
                                np.ones(4, dtype=np.float32), _EPS, None)
            self._type = "nn"
        else:
            self._w = (weights.astype(np.float32)
                       if weights is not None else np.zeros(5, dtype=np.float32))
            self._mean = (mean.astype(np.float32)
                          if mean is not None else np.zeros(4, dtype=np.float32))
            self._std = np.clip(
                (std.astype(np.float32) if std is not None
                 else np.ones(4, dtype=np.float32)), _EPS, None)
            self._type = "linear"
        self._fitted = fitted

    @property
    def model_type(self) -> str:
        return self._type

    @classmethod
    def from_synthetic(cls, n_samples: int = 400, seed: int = 42,
                       use_nn: bool = False, nn_epochs: int = 300,
                       nn_lr: float = 0.02) -> RoadPlausibilityEstimator:
        rng = np.random.default_rng(seed)
        half = n_samples // 2

        n_pos = rng.integers(30, 300, half)
        span_pos = rng.uniform(0.001, 0.20, half)
        elev_pos = rng.uniform(0.0, 200.0, half)
        reg_pos = rng.uniform(0.55, 0.98, half)

        neg = n_samples - half
        n_neg = rng.integers(2, 40, neg)
        span_neg = rng.uniform(0.0001, 0.05, neg)
        elev_neg = rng.uniform(100.0, 2000.0, neg)
        reg_neg = rng.uniform(0.0, 0.50, neg)

        n_arr = np.concatenate([n_pos, n_neg]).astype(np.float64)
        span = np.concatenate([span_pos, span_neg]).astype(np.float64)
        elev = np.concatenate([elev_pos, elev_neg]).astype(np.float64)
        reg = np.concatenate([reg_pos, reg_neg]).astype(np.float64)

        X = np.stack([n_arr, span, elev, reg], axis=1)
        y = _ground_truth(n_arr, span, elev, reg)

        mean = X.mean(axis=0)
        std = np.where(X.std(axis=0) < _EPS, _EPS, X.std(axis=0))
        Xs = (X - mean) / std

        if not use_nn:
            Xb = np.hstack([np.ones((Xs.shape[0], 1), dtype=np.float64), Xs])
            ata = Xb.T @ Xb + _LAMBDA * np.eye(Xb.shape[1], dtype=np.float64)
            try:
                w = np.linalg.solve(ata, Xb.T @ y)
            except np.linalg.LinAlgError:
                w, *_ = np.linalg.lstsq(Xb, y, rcond=None)
            return cls(weights=w, mean=mean, std=std, fitted=True)

        nn = SimpleNN(input_size=4, seed=seed)
        X_nn = Xs.astype(np.float64)
        y_nn = y.reshape(-1, 1).astype(np.float64)
        nn.fit(X_nn, y_nn, epochs=nn_epochs, batch_size=16, lr=nn_lr,
               val_split=0.2, seed=seed)
        return cls(nn=nn, mean=mean, std=std, fitted=True)

    def _standardize(self, feat: GpxFeatures) -> np.ndarray:
        v = feat.to_vector()
        return (v - self._mean.astype(np.float64)) / self._std.astype(np.float64)

    def road_score(self, points: list[RawPoint]) -> float:
        if not self._fitted or len(points) < 2:
            return 0.0
        feat = extract_gpx_features(points)
        x = self._standardize(feat)
        if self._type == "nn":
            raw = float(self._nn.predict(x.reshape(1, -1).astype(np.float64))[0, 0])
        else:
            xb = np.concatenate([[1.0], x])
            raw = float(xb @ self._w.astype(np.float64))
        score = 1.0 / (1.0 + np.exp(-raw))
        return float(np.clip(score, 0.0, 1.0))

    def confidence(self, points: list[RawPoint]) -> float:
        score = self.road_score(points)
        feat = extract_gpx_features(points)
        data_adequacy = min(1.0, 0.5 + 0.5 * min(1.0, feat.n_points / 40.0))
        conf = data_adequacy * (0.6 + 0.4 * score)
        return float(np.clip(round(conf, 3), 0.0, 0.98))


# =========================
# Default estimator
# =========================

def _load_default_model() -> RoadPlausibilityEstimator:
    return RoadPlausibilityEstimator.from_synthetic()


_DEFAULT_ESTIMATOR = _load_default_model()


def estimate_gpx(points: list[RawPoint]) -> tuple[float, float]:
    return (_DEFAULT_ESTIMATOR.road_score(points),
            _DEFAULT_ESTIMATOR.confidence(points))
