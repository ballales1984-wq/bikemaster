"""Conflict resolution using reliability_score and last_modified timestamps.

Resolution strategy (per deployment plan §3.2):
1. Higher reliability_score wins.
2. On tie: most recent last_modified wins.
3. Unresolvable conflicts are flagged for user review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..utils.logger import get_logger
from .models import ConflictRecord, ConflictResolution, SyncStatus

logger = get_logger(__name__)

# Minimum reliability score that a source must have to be considered "authoritative".
_AUTHORITATIVE_THRESHOLD = 0.8

# Maximum time delta (in seconds) that still allows auto-resolution.
_MAX_AUTO_RESOLVE_AGE_S = 86400 * 30  # 30 days


@dataclass
class ResolutionResult:
    """Outcome of a conflict resolution attempt."""

    resolution: str
    merged_data: dict[str, Any] | None
    reason: str
    needs_user_review: bool = False


def resolve_conflict(conflict: ConflictRecord) -> ResolutionResult:
    """Resolve a single conflict between local and remote data.

    Strategy:
    1. If one side has reliability_score >= _AUTHORITATIVE_THRESHOLD
       and the other does not, the authoritative side wins.
    2. Otherwise, compare reliability_score (higher wins).
    3. On equal reliability_score, compare last_modified (newer wins).
    4. If both scores and timestamps are effectively equal, flag for user review.
    """
    local = conflict.local_data
    remote = conflict.remote_data
    local_rel = conflict.local_reliability
    remote_rel = conflict.remote_reliability

    local_is_authoritative = local_rel >= _AUTHORITATIVE_THRESHOLD
    remote_is_authoritative = remote_rel >= _AUTHORITATIVE_THRESHOLD

    if local_is_authoritative and not remote_is_authoritative:
        return ResolutionResult(
            resolution=ConflictResolution.LOCAL_WINS,
            merged_data=local,
            reason=f"Local source has higher reliability ({local_rel:.2f} >= {_AUTHORITATIVE_THRESHOLD})",
            needs_user_review=False,
        )

    if remote_is_authoritative and not local_is_authoritative:
        return ResolutionResult(
            resolution=ConflictResolution.REMOTE_WINS,
            merged_data=remote,
            reason=f"Remote source has higher reliability ({remote_rel:.2f} >= {_AUTHORITATIVE_THRESHOLD})",
            needs_user_review=False,
        )

    rel_diff = abs(local_rel - remote_rel)
    if rel_diff > 0.05:
        winner = ConflictResolution.LOCAL_WINS if local_rel > remote_rel else ConflictResolution.REMOTE_WINS
        winner_data = local if winner == ConflictResolution.LOCAL_WINS else remote
        return ResolutionResult(
            resolution=winner,
            merged_data=winner_data,
            reason=f"Reliability score difference ({rel_diff:.2f})",
            needs_user_review=False,
        )

    try:
        from datetime import datetime as dt

        local_ts = dt.fromisoformat(conflict.local_modified.replace("Z", "+00:00"))
        remote_ts = dt.fromisoformat(conflict.remote_modified.replace("Z", "+00:00"))
        ts_diff = abs((local_ts - remote_ts).total_seconds())
    except (ValueError, TypeError):
        ts_diff = None

    if ts_diff is not None and ts_diff > 1.0:
        winner = ConflictResolution.LOCAL_WINS if local_ts >= remote_ts else ConflictResolution.REMOTE_WINS
        winner_data = local if winner == ConflictResolution.LOCAL_WINS else remote
        return ResolutionResult(
            resolution=winner,
            merged_data=winner_data,
            reason=f"More recent last_modified ({ts_diff:.0f}s difference)",
            needs_user_review=False,
        )

    merged = _field_level_merge(local, remote)
    return ResolutionResult(
        resolution=ConflictResolution.UNRESOLVED,
        merged_data=merged,
        reason="Equal reliability and timestamp; field-level merge attempted",
        needs_user_review=merged is None,
    )


def _field_level_merge(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any] | None:
    """Attempt a best-effort field-level merge.

    For each field present in both dicts:
    - If values are equal, keep the value.
    - If values differ and both are non-null, the merge is ambiguous → return None.
    - If one is None, keep the non-None value.

    Returns the merged dict, or None if the merge is ambiguous.
    """
    if not local and not remote:
        return {}
    if not local:
        return dict(remote)
    if not remote:
        return dict(local)

    merged = dict(local)
    ambiguous = False

    all_keys = set(local.keys()) | set(remote.keys())
    for key in all_keys:
        local_val = local.get(key)
        remote_val = remote.get(key)
        if key not in remote:
            continue
        if key not in local:
            merged[key] = remote_val
            continue
        if local_val == remote_val:
            continue
        if local_val is None:
            merged[key] = remote_val
        elif remote_val is None:
            merged[key] = local_val
        else:
            ambiguous = True

    return None if ambiguous else merged


class ConflictResolver:
    """Resolves batches of conflicts with configurable strategies."""

    def __init__(self, authoritative_threshold: float = _AUTHORITATIVE_THRESHOLD) -> None:
        self.authoritative_threshold = authoritative_threshold

    def resolve(self, conflict: ConflictRecord) -> ResolutionResult:
        return resolve_conflict(conflict)

    def resolve_batch(self, conflicts: list[ConflictRecord]) -> list[ResolutionResult]:
        return [self.resolve(c) for c in conflicts]


__all__ = [
    "ResolutionResult",
    "resolve_conflict",
    "ConflictResolver",
    "_AUTHORITATIVE_THRESHOLD",
    "_MAX_AUTO_RESOLVE_AGE_S",
]
