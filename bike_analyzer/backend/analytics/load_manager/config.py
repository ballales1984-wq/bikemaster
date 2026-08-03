"""Load Manager — configurable thresholds and athlete-level load targets.

Pure, deterministic configuration for the training-load system. Thresholds are
keyed by athlete experience level so they can be tuned per athlete without
touching the calculation logic.

See .kilo/agent/load-manager.md for the full specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

AthleteLevel = Literal["beginner", "intermediate", "advanced", "elite"]


class AthleteLevelEnum(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"


@dataclass(frozen=True)
class LoadBalanceTarget:
    """Weekly TSS target band for an athlete level."""

    level: AthleteLevel
    min_tss_per_week: float
    max_tss_per_week: float


@dataclass(frozen=True)
class SafetyThresholds:
    """Configurable safety thresholds (agent constraints: must be tunable)."""

    acwr_high_risk: float = 1.5
    acwr_block: float = 2.0
    acwr_detraining: float = 0.8
    tsb_fatigue: float = -30.0
    tsb_freshness_loss: float = 20.0
    ctl_atl_sum_limit: float = 250.0


@dataclass(frozen=True)
class LoadManagerConfig:
    """Top-level configuration aggregated from the agent spec."""

    tau_ctl: int = 42
    tau_atl: int = 7
    acwr_short_days: int = 7
    acwr_long_days: int = 28
    thresholds: SafetyThresholds = field(default_factory=SafetyThresholds)
    targets: dict[AthleteLevel, LoadBalanceTarget] = field(
        default_factory=lambda: {
            AthleteLevelEnum.BEGINNER.value: LoadBalanceTarget("beginner", 200.0, 400.0),
            AthleteLevelEnum.INTERMEDIATE.value: LoadBalanceTarget("intermediate", 400.0, 700.0),
            AthleteLevelEnum.ADVANCED.value: LoadBalanceTarget("advanced", 700.0, 1000.0),
            AthleteLevelEnum.ELITE.value: LoadBalanceTarget("elite", 1000.0, 1600.0),
        }
    )

    def target_for(self, level: AthleteLevel) -> LoadBalanceTarget:
        return self.targets.get(
            AthleteLevelEnum(level).value,
            self.targets[AthleteLevelEnum.INTERMEDIATE.value],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tau_ctl": self.tau_ctl,
            "tau_atl": self.tau_atl,
            "acwr_short_days": self.acwr_short_days,
            "acwr_long_days": self.acwr_long_days,
            "thresholds": self.thresholds.__dict__,
            "targets": {k: v.__dict__ for k, v in self.targets.items()},
        }


DEFAULT_CONFIG = LoadManagerConfig()

__all__ = [
    "AthleteLevel",
    "AthleteLevelEnum",
    "LoadBalanceTarget",
    "SafetyThresholds",
    "LoadManagerConfig",
    "DEFAULT_CONFIG",
]
