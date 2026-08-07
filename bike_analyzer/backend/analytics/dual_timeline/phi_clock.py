"""Phi-clock builder: converts irregular time series into monotone internal-clock curves.

Each subsystem (metabolism, stress, recovery, load) has its own clock phi(t)
that ticks at a rate controlled by a time-varying time-constant tau(t):

    alpha(t) = 1 - exp(-delta_t / tau(t))
    phi(t)   = phi(t-1) + alpha(t) * delta_t

Short tau  -> alpha close to 1 -> clock runs fast (high stress, acute load)
Long  tau  -> alpha close to 0 -> clock runs slow (deep recovery)

Real-world time is the fixed grid; phi(t) is the curved path across it.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime

import numpy as np

from .models import ClockTrack, DataPoint, PhiConfig

_DEFAULT_CONFIG = PhiConfig()


def _to_naive_utc(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        return ts.astimezone(UTC).replace(tzinfo=None)
    return ts


utc = UTC


def _timestamp_to_epoch(ts: datetime) -> float:
    dt = _to_naive_utc(ts)
    return dt.replace(tzinfo=utc).timestamp()


def _epoch_to_timestamp(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=utc).replace(tzinfo=None)


def _parse_grid_spacing(grid_spacing: str) -> float:
    """Parse a pandas-style offset string (e.g. '1D', '6H') to seconds."""
    m = re.fullmatch(r"(\d+)([dDhHmM])", grid_spacing.strip())
    if not m:
        return 86400.0
    value = int(m.group(1))
    unit = m.group(2).lower()
    if unit == "d":
        return value * 86400.0
    if unit == "h":
        return value * 3600.0
    if unit == "m":
        return value * 60.0
    return 86400.0


def _ema(values: list[float], alpha: float) -> list[float]:
    if not values:
        return []
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1.0 - alpha) * smoothed[-1])
    return smoothed


def _tau_from_signal(
    values: list[float],
    tau_base: float,
    tau_min: float,
    tau_max: float,
) -> list[float]:
    """Derive a per-sample tau from the signal magnitude.

    Higher absolute values -> shorter tau (faster clock).
    Normalized against the median absolute value.
    """
    if not values:
        return []

    abs_vals = [abs(v) for v in values]
    median = float(np.median(abs_vals)) if abs_vals else 1.0
    median = max(median, 1e-6)

    taus = []
    for v in abs_vals:
        ratio = v / median
        tau = tau_base / max(ratio, 0.1)
        tau = max(tau_min, min(tau_max, tau))
        taus.append(tau)

    return taus


def _time_weighted_interpolation(
    t_epoch: list[float],
    values: list[float],
    grid_epoch: list[float],
) -> list[float]:
    """Interpolate values onto a regular time grid, weighted by real delta-t.

    numpy.interp on epoch seconds is inherently time-weighted because the
    x-axis is real-world time, not sample index.
    """
    if len(t_epoch) < 2:
        n = len(grid_epoch)
        if n and t_epoch:
            return [values[0]] * n
        return []

    arr = np.array(values, dtype=np.float64)
    t = np.array(t_epoch, dtype=np.float64)
    g = np.array(grid_epoch, dtype=np.float64)

    return np.interp(g, t, arr).tolist()


def resample_to_grid(
    points: list[DataPoint],
    grid_spacing: str = "1D",
) -> tuple[list[datetime], list[float], list[float]]:
    """Resample an irregular DataPoint series to a regular time grid.

    Steps:
    1. Sort by timestamp.
    2. Apply EMA pre-filter to smooth high-frequency noise.
    3. Build a uniform grid from first to last point.
    4. Time-weighted linear interpolation onto the grid.

    Returns:
        (grid_timestamps, grid_values, confidences)
        confidences decay with the gap size between original points.
    """
    if not points:
        return [], [], []

    sorted_pts = sorted(points, key=lambda p: p.timestamp)
    t_epoch = [_timestamp_to_epoch(p.timestamp) for p in sorted_pts]
    raw_values = [p.value for p in sorted_pts]
    raw_conf = [p.confidence for p in sorted_pts]

    ema_values = _ema(raw_values, _DEFAULT_CONFIG.ema_alpha)

    t0 = t_epoch[0]
    t1 = t_epoch[-1]
    spacing_sec = _parse_grid_spacing(grid_spacing)

    n_points = max(1, int(math.ceil((t1 - t0) / spacing_sec))) + 1
    grid_epoch = [t0 + i * spacing_sec for i in range(n_points)]

    grid_values = _time_weighted_interpolation(t_epoch, ema_values, grid_epoch)

    grid_conf: list[float] = []
    for ge in grid_epoch:
        dists = [abs(ge - te) for te in t_epoch]
        nearest_idx = int(np.argmin(dists))
        gap = dists[nearest_idx]
        max_gap = spacing_sec * 2.0
        conf = raw_conf[nearest_idx] * max(0.0, 1.0 - gap / max_gap)
        grid_conf.append(round(conf, 4))

    grid_ts = [_epoch_to_timestamp(ge) for ge in grid_epoch]
    return grid_ts, grid_values, grid_conf


def build_phi(
    points: list[DataPoint],
    config: PhiConfig | None = None,
    tau_override: list[float] | None = None,
) -> ClockTrack:
    """Build a ClockTrack from an irregular DataPoint series.

    Args:
        points:       Raw measurements (can have arbitrary timestamps).
        config:       PhiConfig with tau_base, grid_spacing, etc.
        tau_override: Optional per-sample tau values (seconds).  If None,
                      tau is derived automatically from signal magnitude.

    Returns:
        ClockTrack with phi(t), alpha(t), and tau(t) arrays.
    """
    cfg = config or _DEFAULT_CONFIG

    if not points:
        return ClockTrack(
            subsystem="",
            t_real=[],
            phi=[],
            alpha=[],
            tau=[],
            confidence=[],
        )

    subsystem = points[0].metric

    grid_ts, grid_values, grid_conf = resample_to_grid(points, cfg.grid_spacing)

    if len(grid_ts) < 2:
        return ClockTrack(
            subsystem=subsystem,
            t_real=grid_ts,
            phi=[0.0] * len(grid_ts),
            alpha=[0.0] * len(grid_ts),
            tau=[cfg.tau_base] * len(grid_ts),
            confidence=grid_conf,
        )

    grid_epoch = [_timestamp_to_epoch(ts) for ts in grid_ts]

    if tau_override is not None and len(tau_override) == len(grid_ts):
        taus = list(tau_override)
    else:
        taus = _tau_from_signal(
            grid_values, cfg.tau_base, cfg.tau_min, cfg.tau_max
        )

    phi: list[float] = [0.0]
    alpha: list[float] = [0.0]

    for i in range(1, len(grid_epoch)):
        delta_t = grid_epoch[i] - grid_epoch[i - 1]
        delta_t = max(delta_t, 1e-6)
        tau_i = max(taus[i], 1e-6)
        a = 1.0 - math.exp(-delta_t / tau_i)
        a = max(0.0, min(1.0, a))
        phi.append(phi[-1] + a * delta_t)
        alpha.append(a)

    return ClockTrack(
        subsystem=subsystem,
        t_real=grid_ts,
        phi=phi,
        alpha=alpha,
        tau=taus,
        confidence=grid_conf,
    )


def velocity(track: ClockTrack) -> list[float]:
    """Instantaneous clock speed dphi/dt for each time step.

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
