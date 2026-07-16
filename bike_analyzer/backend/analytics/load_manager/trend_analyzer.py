"""Load Manager — Trend Analysis service.

Spec (agent): component #6. Analyzes CTL trend, performance trend and the
correlation between load and performance outcome. Pure and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TrendDirection(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"


@dataclass
class TrendResult:
    direction: TrendDirection
    slope: float
    delta: float
    window: int


@dataclass
class CorrelationResult:
    coefficient: float
    samples: int
    interpretation: str


def _linear_slope(values: list[float]) -> float:
    """Least-squares slope of a series indexed 0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den = sum((x - x_mean) ** 2 for x in xs)
    return num / den if den else 0.0


def _direction(slope: float, eps: float = 0.5) -> TrendDirection:
    if slope > eps:
        return TrendDirection.RISING
    if slope < -eps:
        return TrendDirection.FALLING
    return TrendDirection.STABLE


class TrendAnalyzer:
    """Analyze load and performance trends over time."""

    def __init__(self, sensitivity: float = 0.5) -> None:
        self.sensitivity = sensitivity

    def ctl_trend(self, ctl_series: list[float]) -> TrendResult:
        slope = _linear_slope(ctl_series)
        delta = (ctl_series[-1] - ctl_series[0]) if len(ctl_series) >= 1 else 0.0
        return TrendResult(_direction(slope, self.sensitivity), round(slope, 3),
                           round(delta, 1), len(ctl_series))

    def performance_trend(self, performance_series: list[float]) -> TrendResult:
        slope = _linear_slope(performance_series)
        delta = (performance_series[-1] - performance_series[0]) if len(performance_series) >= 1 else 0.0
        return TrendResult(_direction(slope, self.sensitivity), round(slope, 3),
                           round(delta, 1), len(performance_series))

    def load_performance_correlation(
        self, load_series: list[float], performance_series: list[float]
    ) -> CorrelationResult:
        n = min(len(load_series), len(performance_series))
        if n < 3:
            return CorrelationResult(0.0, n, "dati insufficienti")
        x = load_series[:n]
        y = performance_series[:n]
        xm = sum(x) / n
        ym = sum(y) / n
        cov = sum((a - xm) * (b - ym) for a, b in zip(x, y))
        var_x = sum((a - xm) ** 2 for a in x)
        var_y = sum((b - ym) ** 2 for b in y)
        denom = (var_x * var_y) ** 0.5
        coeff = round(cov / denom, 3) if denom else 0.0
        if coeff >= 0.5:
            interp = "carico correlato positivamente alla performance"
        elif coeff <= -0.5:
            interp = "carico elevato associato a calo di performance"
        else:
            interp = "correlazione debole tra carico e performance"
        return CorrelationResult(coeff, n, interp)


__all__ = [
    "TrendDirection",
    "TrendResult",
    "CorrelationResult",
    "TrendAnalyzer",
]
