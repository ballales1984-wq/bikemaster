"""TempoTrack — public API surface."""

from __future__ import annotations

from .clock.phase import build_phase_track, update_phase, velocity
from .clock.tau_dynamic import instantaneous_tau
from .clock.tau_estimation import estimate_tau_from_response
from .gap_policy import apply_gap_policy, classify_gap
from .models import (
    ClockTrack,
    DataPoint,
    PhiConfig,
    SignalKind,
    SyncIndex,
    Track,
)
from .resampling.continuous import aggregate_events, resample_continuous
from .scoring.coverage import composite_score, coverage_fraction
from .sync.drift import build_sync_index, compute_drift, velocity_correlation

__all__ = [
    "SignalKind",
    "DataPoint",
    "Track",
    "ClockTrack",
    "SyncIndex",
    "PhiConfig",
    "resample_continuous",
    "aggregate_events",
    "update_phase",
    "build_phase_track",
    "velocity",
    "estimate_tau_from_response",
    "instantaneous_tau",
    "compute_drift",
    "velocity_correlation",
    "build_sync_index",
    "composite_score",
    "coverage_fraction",
    "classify_gap",
    "apply_gap_policy",
]
