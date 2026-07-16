"""Load Manager package — orchestrates the full training-load pipeline.

Public surface referenced by the agent:
- pure functions: calculate_tss, calculate_ewma, calculate_acwr
- services: TrainingStressCalculator, LoadManager, TrendAnalyzer
- models: TrainingStress, ChronicLoad, LoadBalance
"""

from __future__ import annotations

from .calculators import calculate_acwr, calculate_ewma, calculate_tss, terrain_correction
from .chronic_load import ChronicLoadManager
from .config import (
    DEFAULT_CONFIG,
    AthleteLevel,
    AthleteLevelEnum,
    LoadBalanceTarget,
    LoadManagerConfig,
    SafetyThresholds,
)
from .models import ChronicLoad, LoadBalance, StressMethod, TrainingStress
from .safety_balance import (
    LoadManager,
    RedistributionPlan,
    RiskLevel,
    SafetyAlert,
)
from .training_stress_calculator import TrainingStressCalculator
from .trend_analyzer import (
    CorrelationResult,
    TrendAnalyzer,
    TrendDirection,
    TrendResult,
)

__all__ = [
    "DEFAULT_CONFIG",
    "AthleteLevel",
    "AthleteLevelEnum",
    "LoadBalanceTarget",
    "SafetyThresholds",
    "LoadManagerConfig",
    "TrainingStress",
    "ChronicLoad",
    "LoadBalance",
    "StressMethod",
    "TrainingStressCalculator",
    "ChronicLoadManager",
    "LoadManager",
    "TrendAnalyzer",
    "RiskLevel",
    "SafetyAlert",
    "RedistributionPlan",
    "CorrelationResult",
    "TrendDirection",
    "TrendResult",
    "calculate_tss",
    "calculate_ewma",
    "calculate_acwr",
    "terrain_correction",
]
