"""Time-weighted resampling for CONTINUOUS and RATE signals."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime

import numpy as np

from ..models import DataPoint

utc = UTC

CONTINUOUS_MAX_GAP_SECONDS = 3 * 86400  # 3 days
RATE_MAX_GAP_SECONDS = 7 * 86400  # 7 days


def _to_naive_utc(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        return ts.astimezone(utc).replace(tzinfo=None)
    return ts


def _timestamp_to_epoch(ts: datetime) -> float:
    dt = _to_naive_utc(ts)
    return dt.replace(tzinfo=utc).timestamp()


def _epoch_to_timestamp(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=utc).replace(tzinfo=None)


def _parse_grid_spacing(grid_spacing: str) -> float:
    """Parse a compact offset string (e.g. '1D', '6H', '30m') to seconds."""
    m = re.fullmatch(r"\s*(\d+)\s*([dDhHmM])\s*", grid_spacing)
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
    """Exponential moving average — same form as Banister/CTL smoothing."""
    if not values:
        return []
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1.0 - alpha) * smoothed[-1])
    return smoothed


def _max_gap_for(kind: str) -> float:
    if kind == "event":
        return 0.0  # never interpolate
    if kind == "rate":
        return RATE_MAX_GAP_SECONDS
    return CONTINUOUS_MAX_GAP_SECONDS


def resample_continuous(
    points: list[DataPoint],
    grid_spacing: str = "1D",
    ema_alpha: float = 0.3,
) -> tuple[list[datetime], list[float | None], list[float]]:
    """Resample CONTINUOUS/RATE points to a regular time grid.

    Steps:
    1. Sort by timestamp.
    2. Apply EMA pre-filter to smooth high-frequency noise.
    3. Build uniform grid from first to last point.
    4. ``numpy.interp`` on epoch seconds — inherently time-weighted.
    5. Grid points that fall within an acceptable gap of valid data are
       interpolated; points in too-large gaps are set to None.
    6. Confidence decays with distance from nearest original point.

    Returns:
        (grid_timestamps, grid_values, confidences)
        grid_values contains None where data is too sparse to interpolate.
    """
    if not points:
        return [], [], []

    sorted_pts = sorted(points, key=lambda p: p.timestamp)

    # Separate valid points from None-valued points
    valid_pts = [p for p in sorted_pts if p.value is not None]
    if len(valid_pts) < 2:
        spacing_sec = _parse_grid_spacing(grid_spacing)
        t_epoch_all = [_timestamp_to_epoch(p.timestamp) for p in sorted_pts]
        t0 = t_epoch_all[0]
        t1 = t_epoch_all[-1]
        n = max(1, int(math.ceil((t1 - t0) / max(spacing_sec, 1))) + 1)
        grid_epoch = [t0 + j * spacing_sec for j in range(n)]
        grid_ts = [_epoch_to_timestamp(e) for e in grid_epoch]
        fill = valid_pts[0].value if valid_pts else None
        return grid_ts, [fill] * len(grid_ts), [0.0] * len(grid_ts)

    # Determine max gap based on signal kind
    kind = valid_pts[0].kind.value if hasattr(valid_pts[0].kind, 'value') else str(valid_pts[0].kind)
    max_gap = _max_gap_for(kind)

    # EMA on valid values
    raw_values = [p.value for p in valid_pts]
    smoothed = _ema(raw_values, ema_alpha)

    valid_t = [_timestamp_to_epoch(p.timestamp) for p in valid_pts]
    raw_conf = [p.confidence for p in valid_pts]

    t0 = valid_t[0]
    t1 = valid_t[-1]
    spacing_sec = _parse_grid_spacing(grid_spacing)
    n_points = max(1, int(math.ceil((t1 - t0) / max(spacing_sec, 1))) + 1)
    grid_epoch = [t0 + j * spacing_sec for j in range(n_points)]

    # Interpolate, respecting max gap
    arr = np.array(smoothed, dtype=np.float64)
    t = np.array(valid_t, dtype=np.float64)
    g = np.array(grid_epoch, dtype=np.float64)

    interpolated = np.interp(g, t, arr)

    # Mark grid points in too-large gaps as None.
    # A grid point is in a valid region only if it falls between two
    # bracketing valid points whose gap is within max_gap.
    if max_gap > 0:
        valid_t_arr = np.array(valid_t, dtype=np.float64)
        for idx, ge in enumerate(grid_epoch):
            # Find bracketing valid points
            before = valid_t_arr[valid_t_arr <= ge]
            after = valid_t_arr[valid_t_arr >= ge]
            if len(before) == 0 or len(after) == 0:
                # Outside the range of valid data
                interpolated[idx] = np.nan
                continue
            t_before = float(before[-1]) if len(before) > 0 else None
            t_after = float(after[0]) if len(after) > 0 else None
            if t_before is not None and t_after is not None:
                gap = t_after - t_before
                if gap > max_gap:
                    interpolated[idx] = np.nan
            elif t_before is not None:
                # Grid point after last valid point — extrapolation, not allowed
                interpolated[idx] = np.nan
            elif t_after is not None:
                # Grid point before first valid point — extrapolation
                interpolated[idx] = np.nan

    grid_values = [v if np.isfinite(v) else None for v in interpolated]

    # Confidence: 1.0 at original measurement points, decays for interpolated
    grid_conf: list[float] = []
    for ge in grid_epoch:
        dists = [abs(ge - vt) for vt in valid_t]
        nearest_dist = min(dists)
        nearest_val = raw_conf[dists.index(nearest_dist)]
        if nearest_dist < 1e-6:
            conf = nearest_val  # exact match with measured point
        else:
            decay = max(0.0, 1.0 - nearest_dist / (spacing_sec * 2.0))
            conf = nearest_val * decay
        grid_conf.append(round(conf, 4))

    grid_ts = [_epoch_to_timestamp(ge) for ge in grid_epoch]
    return grid_ts, grid_values, grid_conf


def aggregate_events(
    points: list[DataPoint],
    window: str = "1D",
) -> tuple[list[datetime], list[float], list[float]]:
    """Aggregate EVENT points into fixed windows (count or sum)."""
    if not points:
        return [], [], []

    sorted_pts = sorted(points, key=lambda p: p.timestamp)
    spacing_sec = _parse_grid_spacing(window)

    t0 = _timestamp_to_epoch(sorted_pts[0].timestamp)
    t1 = _timestamp_to_epoch(sorted_pts[-1].timestamp)
    n_windows = max(1, int(math.ceil((t1 - t0) / max(spacing_sec, 1))) + 1)

    window_starts: list[datetime] = []
    counts: list[float] = []
    confidences: list[float] = []

    for w in range(n_windows):
        w_start = t0 + w * spacing_sec
        w_end = w_start + spacing_sec

        events_in_window = [
            p for p in sorted_pts
            if w_start <= _timestamp_to_epoch(p.timestamp) < w_end
        ]

        window_starts.append(_epoch_to_timestamp(w_start))
        counts.append(float(len(events_in_window)))

        if events_in_window:
            avg_conf = sum(p.confidence for p in events_in_window) / len(events_in_window)
            confidences.append(round(avg_conf, 4))
        else:
            confidences.append(0.0)

    return window_starts, counts, confidences
