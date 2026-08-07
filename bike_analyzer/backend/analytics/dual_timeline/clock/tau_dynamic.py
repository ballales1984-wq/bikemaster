"""Dynamic tau(t) — adjusts time-constant based on measurable signals."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def instantaneous_tau(
    tau_baseline: float,
    stress_score: float = 0.0,
    sleep_debt_h: float = 0.0,
    is_sick: bool = False,
) -> float:
    """Compute a context-adjusted tau from measurable signals.

    Higher stress, sleep debt, or illness shorten tau (faster clock).
    Coefficients are placeholders — calibrate on real data.

    Args:
        tau_baseline:  Personal baseline tau (days).
        stress_score:  0.0–1.0 normalized stress level.
        sleep_debt_h:  Hours of sleep debt vs personal baseline.
        is_sick:       Whether the athlete is currently sick.

    Returns:
        Adjusted tau in days.
    """
    modifier = 1.0
    modifier *= 1.0 + 0.3 * max(0.0, min(1.0, stress_score))
    modifier *= 1.0 + 0.1 * max(0.0, sleep_debt_h)
    if is_sick:
        modifier *= 1.8

    result = tau_baseline / modifier
    return max(0.5, result)
