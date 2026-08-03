"""Load Manager — Safety thresholds & Load Balance & Load Redistribution.

Spec (agent): services ``LoadManager`` covering Safety Thresholds (#4),
Load Balance (#3) and Load Redistribution (#5).
Agent rule: suggest, never forbid (constraint #4). Thresholds configurable (#3).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .config import DEFAULT_CONFIG, AthleteLevel, LoadManagerConfig
from .models import ChronicLoad, LoadBalance


class RiskLevel(StrEnum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    BLOCK = "block"


@dataclass
class SafetyAlert:
    code: str
    level: RiskLevel
    message: str
    metric: str
    value: float


@dataclass
class RedistributionPlan:
    remaining_rides: int
    remaining_tss: float
    recommended_per_ride: float
    feasible: bool
    notes: list[str]
    per_ride: list[float]


class LoadManager:
    """Evaluate safety and balance, and redistribute load when needed."""

    def __init__(self, config: LoadManagerConfig = DEFAULT_CONFIG) -> None:
        self.config = config

    # ---- Safety Thresholds -------------------------------------------------
    def evaluate_safety(self, load: ChronicLoad) -> list[SafetyAlert]:
        t = self.config.thresholds
        alerts: list[SafetyAlert] = []
        if load.acwr is not None:
            if load.acwr > t.acwr_block:
                alerts.append(SafetyAlert("acwr_block", RiskLevel.BLOCK,
                                          "Blocco carico aggiuntivo: ACWR troppo alto.", "acwr", load.acwr))
            elif load.acwr > t.acwr_high_risk:
                alerts.append(SafetyAlert("acwr_high_risk", RiskLevel.HIGH,
                                          "Rischio infortunio alto (ACWR).", "acwr", load.acwr))
            elif load.acwr < t.acwr_detraining:
                alerts.append(SafetyAlert("acwr_detraining", RiskLevel.INFO,
                                          "Carico basso: rischio di detraining.", "acwr", load.acwr))

        if load.tsb < t.tsb_fatigue:
            alerts.append(SafetyAlert("tsb_fatigue", RiskLevel.HIGH,
                                      "Fatica eccessiva (TSB molto negativo).", "tsb", load.tsb))
        elif load.tsb > t.tsb_freshness_loss:
            alerts.append(SafetyAlert("tsb_freshness", RiskLevel.INFO,
                                      "Ottima forma ma rischio perdita fitness.", "tsb", load.tsb))

        if load.ctl + load.atl > t.ctl_atl_sum_limit:
            alerts.append(SafetyAlert("ctl_atl_sum", RiskLevel.WARNING,
                                      "Ridurre volume: CTL+ATL sopra soglia.", "ctl_atl_sum",
                                      round(load.ctl + load.atl, 1)))
        return alerts

    # ---- Load Balance ------------------------------------------------------
    def balance(
        self,
        level: AthleteLevel,
        current_week_tss: float,
        remaining_rides: int,
        planned_week_total: float | None = None,
    ) -> LoadBalance:
        target = self.config.target_for(level)
        desired = planned_week_total if planned_week_total is not None else (
            (target.min_tss_per_week + target.max_tss_per_week) / 2.0
        )
        remaining_tss = max(desired - current_week_tss, 0.0)
        recommended = remaining_tss / remaining_rides if remaining_rides > 0 else 0.0
        in_balance = target.min_tss_per_week <= current_week_tss <= target.max_tss_per_week
        return LoadBalance(
            level=level,
            min_tss_per_week=target.min_tss_per_week,
            max_tss_per_week=target.max_tss_per_week,
            target_tss_per_week=round(desired, 1),
            current_week_tss=round(current_week_tss, 1),
            remaining_tss=round(remaining_tss, 1),
            remaining_rides=remaining_rides,
            recommended_per_ride=round(recommended, 1),
            in_balance=in_balance,
        )

    # ---- Load Redistribution ----------------------------------------------
    def redistribute(
        self,
        remaining_rides: int,
        remaining_tss: float,
        residual_capacity: float | None = None,
        recovery_factor: float = 1.0,
    ) -> RedistributionPlan:
        """Distribute remaining TSS across remaining rides.

        Base math (agent): remaining_tss / remaining_rides = new per-ride load.
        Recovery factor scales load down when fatigue is high; residual capacity
        caps the per-ride suggestion. Always suggests — never forbids (#4).
        """
        notes: list[str] = []
        if remaining_rides <= 0:
            return RedistributionPlan(0, round(remaining_tss, 1), 0.0, False,
                                      ["Nessuna uscita rimanente."], [])
        if remaining_tss <= 0:
            return RedistributionPlan(remaining_rides, 0.0, 0.0, True,
                                      ["Obiettivo settimanale gia raggiunto."],
                                      [0.0] * remaining_rides)

        per_ride = (remaining_tss / remaining_rides) * recovery_factor
        if residual_capacity is not None and per_ride > residual_capacity:
            per_ride = residual_capacity
            notes.append("Limitato dalla capacita residua: suddividere su piu uscite.")
        feasible = True
        per_ride = round(per_ride, 1)
        spread = [per_ride] * remaining_rides
        return RedistributionPlan(remaining_rides, round(remaining_tss, 1),
                                  per_ride, feasible, notes, spread)


__all__ = [
    "RiskLevel",
    "SafetyAlert",
    "RedistributionPlan",
    "LoadManager",
]
