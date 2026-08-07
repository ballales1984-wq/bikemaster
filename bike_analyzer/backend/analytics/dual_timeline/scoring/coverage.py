"""Coverage scoring — weighted availability across multiple metrics."""

from __future__ import annotations


def composite_score(
    available: dict[str, float],
    weights: dict[str, float],
) -> tuple[float | None, float]:
    """Compute a weighted composite score from partial metric data.

    Missing metrics are handled by renormalizing weights on the available
    subset — no metric is forced to zero, and the day is not discarded.

    Args:
        available: dict of metric_name -> value for available metrics.
        weights:   dict of metric_name -> weight for each metric.

    Returns:
        (score, coverage) where:
            score    = weighted average over available metrics, or None if
                       no data is available at all.
            coverage = present_weight / total_weight (0.0–1.0).
    """
    if not available:
        return None, 0.0

    present_keys = [k for k in weights if k in available and available[k] is not None]
    if not present_keys:
        return None, 0.0

    present_weight = sum(weights[k] for k in present_keys)
    total_weight = sum(weights.values())

    if total_weight <= 0:
        return None, 0.0

    coverage = present_weight / total_weight
    score = sum(weights[k] * available[k] for k in present_keys) / present_weight

    return round(score, 4), round(coverage, 4)


def coverage_fraction(
    available: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Return just the coverage fraction (0.0–1.0) for a set of metrics."""
    _, cov = composite_score(available, weights)
    return cov


def weighted_zscore(value: float, mean: float, std: float) -> float | None:
    """Compute z-score, returning None if std is zero."""
    if std <= 0:
        return None
    return (value - mean) / std
