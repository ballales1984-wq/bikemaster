"""Fatigue model for cycling performance intelligence."""

from __future__ import annotations

from .calculators.fatigue import (
    calculate_fatigue_score,
    estimate_recovery_hours,
    get_recovery_recommendation,
)
