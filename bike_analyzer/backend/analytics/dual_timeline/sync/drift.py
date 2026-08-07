"""Drift computation and cross-correlation between two ClockTracks."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import numpy as np

from ..models import ClockTrack, SyncIndex

utc = UTC

logger = logging.getLogger(__name__)


def compute_drift(track_a: ClockTrack, track_b: ClockTrack) -> list[float]:
    """Compute cumulative drift phi_a - phi_b at each real-time step.

    Both tracks must share the same t_real grid.  If lengths differ,
    the shorter is interpolated onto the longer's grid.

    Positive drift  -> A's clock is ahead of B's (A adapted faster).
    Negative drift  -> B's clock is ahead.
    """
    t_a = np.array([t.timestamp() for t in track_a.t_real], dtype=np.float64)
    t_b = np.array([t.timestamp() for t in track_b.t_real], dtype=np.float64)

    phi_a = np.array(track_a.phi, dtype=np.float64)
    phi_b = np.array(track_b.phi, dtype=np.float64)

    if len(t_a) != len(t_b) or not np.allclose(t_a, t_b):
        # Interpolate B onto A's grid
        if len(t_b) < 2:
            phi_b_interp = np.full(len(t_a), phi_b[0] if len(phi_b) else 0.0)
        else:
            phi_b_interp = np.interp(t_a, t_b, phi_b)
    else:
        phi_b_interp = phi_b

    return (phi_a - phi_b_interp).tolist()


def velocity_correlation(track_a: ClockTrack, track_b: ClockTrack) -> float:
    """Pearson correlation of instantaneous velocities dphi/dt.

    Velocity is computed as (phi[i] - phi[i-1]) / dt for each step.
    If tracks are on different grids, B is interpolated onto A's grid.
    """
    vel_a = _to_velocity(track_a)
    vel_b = _to_velocity(track_b)

    if len(vel_a) < 2 or len(vel_b) < 2:
        return 0.0

    t_a = np.array([t.timestamp() for t in track_a.t_real], dtype=np.float64)
    t_b = np.array([t.timestamp() for t in track_b.t_real], dtype=np.float64)

    t_mid_a = 0.5 * (t_a[:-1] + t_a[1:])
    t_mid_b = 0.5 * (t_b[:-1] + t_b[1:])

    if len(t_mid_a) != len(t_mid_b) or not np.allclose(t_mid_a, t_mid_b):
        vel_b_interp = np.interp(t_mid_a, t_mid_b, vel_b)
    else:
        vel_b_interp = np.array(vel_b)

    va = np.array(vel_a)
    vb = vel_b_interp

    # Mask NaN
    mask = np.isfinite(va) & np.isfinite(vb)
    if mask.sum() < 2:
        return 0.0

    va_clean = va[mask]
    vb_clean = vb[mask]

    std_a = float(np.std(va_clean))
    std_b = float(np.std(vb_clean))

    if std_a < 1e-12 and std_b < 1e-12:
        # Both constant — check if same value
        if np.allclose(va_clean, vb_clean):
            return 1.0
        return -1.0 if np.allclose(va_clean, -vb_clean) else 0.0

    if std_a < 1e-12 or std_b < 1e-12:
        return 0.0

    corr = np.corrcoef(va_clean, vb_clean)[0, 1]
    return float(corr) if np.isfinite(corr) else 0.0


def compute_lag_correlation(
    track_a: ClockTrack,
    track_b: ClockTrack,
    max_lag_steps: int = 30,
) -> tuple[float, float]:
    """Find the optimal lag (in days) that maximizes cross-correlation.

    Uses ``scipy.signal.correlate`` on the velocity arrays.

    Returns:
        (lag_days, correlation) where lag_days is positive if B lags A.
    """
    vel_a = _to_velocity(track_a)
    vel_b = _to_velocity(track_b)

    if len(vel_a) < 3 or len(vel_b) < 3:
        return 0.0, 0.0

    va = np.array(vel_a, dtype=np.float64)
    vb = np.array(vel_b, dtype=np.float64)

    # Normalize
    va = (va - np.mean(va)) / (np.std(va) + 1e-12)
    vb = (vb - np.mean(vb)) / (np.std(vb) + 1e-12)

    n = min(len(va), len(vb))
    va = va[:n]
    vb = vb[:n]

    max_lag = min(max_lag_steps, n - 1)

    try:
        correlation = np.correlate(va, vb, mode="full")
        lags = np.arange(-n + 1, n)
        mask = (lags >= -max_lag) & (lags <= max_lag)
        valid_corr = correlation[mask]
        valid_lags = lags[mask]

        if len(valid_corr) == 0:
            return 0.0, 0.0

        best_idx = int(np.argmax(valid_corr))
        best_lag = int(valid_lags[best_idx])
        best_corr = float(valid_corr[best_idx])

        # Convert lag steps to days
        if len(track_a.t_real) >= 2:
            dt_days = (
                track_a.t_real[1] - track_a.t_real[0]
            ).total_seconds() / 86400.0
            lag_days = best_lag * dt_days
        else:
            lag_days = 0.0

        return round(lag_days, 2), round(best_corr, 4)
    except Exception as exc:
        logger.debug("lag correlation failed: %s", exc)
        return 0.0, 0.0


def build_sync_index(
    track_a: ClockTrack,
    track_b: ClockTrack,
) -> SyncIndex:
    """Build a SyncIndex from two ClockTracks.

    Computes drift, velocity correlation, and optimal lag.
    """
    drift = compute_drift(track_a, track_b)
    vel_corr = velocity_correlation(track_a, track_b)
    lag_days, lag_corr = compute_lag_correlation(track_a, track_b)

    conf_a = min(track_a.confidence) if track_a.confidence else 0.0
    conf_b = min(track_b.confidence) if track_b.confidence else 0.0
    overall_conf = round(min(conf_a, conf_b), 4)

    return SyncIndex(
        subsystem_a=track_a.subsystem,
        subsystem_b=track_b.subsystem,
        drift=drift,
        velocity_corr=round(vel_corr, 4),
        lag_days=lag_days,
        lag_correlation=lag_corr,
        computed_at=datetime.now(utc),
        confidence=overall_conf,
    )


def _to_velocity(track: ClockTrack) -> list[float]:
    """Extract velocity (dphi/dt) from a ClockTrack."""
    if len(track.phi) < 2:
        return []

    result: list[float] = []
    for i in range(1, len(track.phi)):
        dt = (track.t_real[i] - track.t_real[i - 1]).total_seconds()
        dt = max(dt, 1e-6)
        result.append((track.phi[i] - track.phi[i - 1]) / dt)
    return result
