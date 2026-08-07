"""Phase clock: builds monotone phi(t) curves from resampled data.

The recurrence follows the Banister model (CTL/ATL), generalized to
variable tau per subsystem:

    alpha(t) = 1 - exp(-delta_t / tau)
    phi(t)   = phi(t-1) + alpha(t) * (stimulus(t) - phi(t-1))

Where stimulus(t) is the resampled metric value at time t.  phi(t)
represents how much the subsystem has adapted to the stimulus —
it's an exponential smoother with time-varying time-constant tau.

Short tau -> alpha near 1 -> phi chases stimulus aggressively (stress, acute load)
Long  tau -> alpha near 0 -> phi moves slowly (deep recovery, chronic adaptation)
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from ..models import ClockTrack, PhiConfig

_DEFAULT_CONFIG = PhiConfig()
utc = UTC


def _to_naive_utc(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        return ts.astimezone(utc).replace(tzinfo=None)
    return ts


def _timestamp_to_epoch(ts: datetime) -> float:
    dt = _to_naive_utc(ts)
    return dt.replace(tzinfo=utc).timestamp()


def update_phase(
    phi_prev: float,
    delta_t: float,
    tau: float,
    stimulus: float | None,
) -> float:
    """Single step of the Banister-style exponential adaptation.

    Args:
        phi_prev:   Previous phi value.
        delta_t:    Real-world time elapsed since last step (seconds).
        tau:        Time-constant for this step (seconds).
        stimulus:   Current measured value.  If None, phi stays put.

    Returns:
        Updated phi value.
    """
    if stimulus is None or math.isnan(stimulus):
        return phi_prev

    delta_t = max(delta_t, 1e-6)
    tau = max(tau, 1e-6)
    alpha = 1.0 - math.exp(-delta_t / tau)
    alpha = max(0.0, min(1.0, alpha))
    return phi_prev + alpha * (stimulus - phi_prev)


def build_phase_track(
    t_real: list[datetime],
    stimulus: list[float | None],
    tau_values: list[float] | None = None,
    config: PhiConfig | None = None,
) -> ClockTrack:
    """Build a ClockTrack from resampled stimulus values.

    Args:
        t_real:      Real-world timestamps (uniform grid).
        stimulus:    Metric values aligned with t_real.  None = missing.
        tau_values:  Per-step tau in seconds.  If None, uses config.tau_baseline.
        config:      PhiConfig for defaults.

    Returns:
        ClockTrack with phi(t), alpha(t), tau(t).
    """
    cfg = config or _DEFAULT_CONFIG
    n = len(t_real)

    if n == 0:
        return ClockTrack(
            subsystem="",
            t_real=[],
            phi=[],
            alpha=[],
            tau=[],
            confidence=[],
        )

    taus = list(tau_values) if tau_values is not None and len(tau_values) == n else [cfg.tau_baseline] * n

    phi: list[float] = [0.0]
    alphas: list[float] = [0.0]
    confs: list[float] = [1.0]

    for i in range(1, n):
        dt = (t_real[i] - t_real[i - 1]).total_seconds()
        phi_i = update_phase(phi[-1], dt, taus[i], stimulus[i])
        dt_safe = max(dt, 1e-6)
        tau_i = max(taus[i], 1e-6)
        a = 1.0 - math.exp(-dt_safe / tau_i)
        a = max(0.0, min(1.0, a))

        phi.append(phi_i)
        alphas.append(a)

        if stimulus[i] is not None and stimulus[i - 1] is not None:
            confs.append(1.0)
        elif stimulus[i] is None:
            confs.append(confs[-1] * 0.5)
        else:
            confs.append(confs[-1] * 0.8)

    return ClockTrack(
        subsystem="",
        t_real=t_real,
        phi=phi,
        alpha=alphas,
        tau=taus,
        confidence=confs,
    )


def velocity(track: ClockTrack) -> list[float]:
    """Instantaneous clock speed dphi/dt per step.

    Returns a list of length len(track.t_real) - 1.
    """
    if len(track.phi) < 2:
        return []

    result: list[float] = []
    for i in range(1, len(track.phi)):
        dt = (track.t_real[i] - track.t_real[i - 1]).total_seconds()
        dt = max(dt, 1e-6)
        result.append((track.phi[i] - track.phi[i - 1]) / dt)
    return result
