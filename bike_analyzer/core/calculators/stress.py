"""Training stress calculator - EWMA-based fitness/fatigue modeling.

Provides the exponential weighted moving average (EWMA) used to compute
ATL (Acute Training Load, 7-day), CTL (Chronic Training Load, 42-day),
and TSB (Training Stress Balance = CTL - ATL) from daily TSS values.
"""

from __future__ import annotations

import math


def ewma(values: list[float], tau_days: float) -> float:
    """Exponential Weighted Moving Average with configurable time constant.

    Uses the standard EWMA formula: alpha = 1 - exp(-1/tau), giving
    a smooth decay where older values contribute exponentially less.
    Typical values: tau=7 for ATL (acute fatigue), tau=42 for CTL (fitness).

    Args:
        values: Ordered series of daily TSS values (oldest to newest).
        tau_days: Time constant in days. Larger values = slower decay.

    Returns:
        The EWMA value rounded to 1 decimal place.
    """
    if not values:
        return 0.0
    alpha = 1.0 - math.exp(-1.0 / max(tau_days, 1e-9))
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1.0 - alpha) * result
    return round(result, 1)
