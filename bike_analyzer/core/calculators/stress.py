import math


def ewma(values: list[float], tau_days: float) -> float:
    """Exponential Weighted Moving Average (EWMA) con costante di tempo tau_days."""
    if not values:
        return 0.0
    alpha = 1.0 - math.exp(-1.0 / max(tau_days, 1e-9))
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1.0 - alpha) * result
    return round(result, 1)
