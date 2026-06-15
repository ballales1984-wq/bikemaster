"""Stress calculator (EWMA, TSS time series)."""

from __future__ import annotations


def ewma(values: list[float], tau_days: float) -> float:
    if not values:
        return 0.0
    alpha = 1.0 - 2.718281828459045 ** (-1.0 / tau_days)
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1.0 - alpha) * result
    return round(result, 1)
