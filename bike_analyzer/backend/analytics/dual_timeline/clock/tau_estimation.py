"""Tau estimation via system identification and dynamic tau(t) from signals."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

logger = logging.getLogger(__name__)


def estimate_tau_from_response(
    t_days: Sequence[float],
    response: Sequence[float],
    initial_guess: tuple[float, float] = (7.0, 1.0),
) -> tuple[float, float] | None:
    """Estimate tau via curve_fit on an exponential response curve.

    Fits: response(t) = amplitude * (1 - exp(-t / tau))

    This is the system identification step: given a known stimulus
    (e.g. caloric deficit) and the observed response (weight change),
    estimate the personal time-constant tau.

    Args:
        t_days:       Time points in days.
        response:     Observed response values.
        initial_guess: (tau_days, amplitude) starting point for fit.

    Returns:
        (tau_days, amplitude) or None if fit fails.
    """
    try:
        t_arr = np.array(t_days, dtype=np.float64)
        r_arr = np.array(response, dtype=np.float64)

        if len(t_arr) < 3:
            return None

        def model(t, tau, amp):
            return amp * (1.0 - np.exp(-t / max(tau, 1e-6)))

        popt, _ = curve_fit(model, t_arr, r_arr, p0=initial_guess, maxfev=10000)
        tau_days = float(popt[0])
        amplitude = float(popt[1])
        return tau_days, amplitude
    except Exception as exc:
        logger.debug("tau estimation failed: %s", exc)
        return None


# Import curve_fit lazily to keep the module importable without scipy
# in constrained environments (though scipy is a project dependency).
from scipy.optimize import curve_fit  # noqa: E402
