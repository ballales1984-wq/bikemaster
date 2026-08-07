"""Gap policy — decides how to handle missing data per SignalKind."""

from __future__ import annotations

import logging
from typing import Literal

from .models import DataPoint, SignalKind

logger = logging.getLogger(__name__)

# Maximum gap (seconds) for which interpolation of CONTINUOUS signals
# is considered acceptable.  Beyond this, confidence drops to 0.
CONTINUOUS_MAX_GAP_SECONDS = 3 * 86400  # 3 days

# Maximum gap for RATE signals (derived from EVENT windows).
RATE_MAX_GAP_SECONDS = 7 * 86400  # 7 days

# EVENT signals are NEVER interpolated, regardless of gap size.


def classify_gap(
    kind: SignalKind,
    gap_seconds: float,
) -> Literal["interpolate", "aggregate", "null", "none"]:
    """Return the handling policy for a gap of the given size.

    - "interpolate": fill via time-weighted interpolation (CONTINUOUS, short gap).
    - "aggregate":   leave as None; will be filled by window aggregation (EVENT).
    - "null":        gap is too large for interpolation, leave as None.
    - "none":        no gap / no action needed.
    """
    if gap_seconds <= 0:
        return "none"

    if kind == SignalKind.EVENT:
        return "aggregate"

    if kind == SignalKind.RATE:
        if gap_seconds <= RATE_MAX_GAP_SECONDS:
            return "interpolate"
        return "null"

    if kind == SignalKind.CONTINUOUS:
        if gap_seconds <= CONTINUOUS_MAX_GAP_SECONDS:
            return "interpolate"
        return "null"

    return "none"


def apply_gap_policy(points: list[DataPoint]) -> list[DataPoint]:
    """Post-process DataPoints: mark interpolated ones, clamp confidence.

    For gaps where interpolation is acceptable, inserts synthetic points
    with ``is_interpolated=True`` and reduced confidence.  For gaps that
    are too large, leaves the gap as None (no fabrication).

    NOTE: This operates on already-resampled grid data.  The actual
    interpolation is done in ``resampling.continuous``.
    """
    if len(points) < 2:
        return points

    result: list[DataPoint] = [points[0]]

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]

        gap = (curr.timestamp - prev.timestamp).total_seconds()

        if curr.value is None:
            result.append(curr)
            continue

        policy = classify_gap(curr.kind, gap)

        if policy == "interpolate" and prev.value is not None:
            # Reduce confidence for interpolated segments
            decay = max(0.0, 1.0 - gap / CONTINUOUS_MAX_GAP_SECONDS)
            curr = DataPoint(
                timestamp=curr.timestamp,
                source=curr.source,
                metric=curr.metric,
                value=curr.value,
                unit=curr.unit,
                kind=curr.kind,
                confidence=round(curr.confidence * decay, 4),
                is_interpolated=True,
            )

        result.append(curr)

    return result
