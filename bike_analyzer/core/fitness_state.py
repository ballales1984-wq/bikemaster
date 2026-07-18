"""Fitness State Vector - snapshot fisiologico dell'atleta.

Il Fitness State Vector e' il cuore del sistema di monitoraggio del carico
di allenamento. Combina:

- **ATL** (Acute Training Load): fatica a breve termine (EWMA 7 giorni).
- **CTL** (Chronic Training Load): fitness a lungo termine (EWMA 42 giorni).
- **TSB** (Training Stress Balance): forma corrente (CTL - ATL).
- **Trend**: andamento a 7 e 30 giorni (in aumento, stabile, in calo).
- **Risk indicators**: segnali di allarme (overtraining, fatica accumulata).
- **Recommendation**: consiglio generato automaticamente.

I valori sono normalizzati e arrotondati a 1 decimale per l'output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class TrainingStressDay:
    """Dato giornaliero di carico di allenamento.

    Attributes:
        date: Giorno di riferimento.
        tss: Training Stress Score del giorno.
        atl: Acute Training Layer (fatica a breve termine).
        ctl: Chronic Training Layer (fitness a lungo termine).
        tsb: Training Stress Balance (forma corrente).
    """
    tss: float = 0.0
    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0


@dataclass
class FitnessStateVector:
    """Vettore di stato fisiologico dell'atleta.

    Attributes:
        athlete_id: Identificativo univoco dell'atleta.
        computed_at: Timestamp UTC del calcolo.
        atl: Acute Training Load (fatica a breve termine, default 7 giorni).
        ctl: Chronic Training Load (fitness a lungo termine, default 42 giorni).
        tsb: Training Stress Balance (forma corrente = CTL - ATL).
        fitness: Alias per CTL (fitness accumulata).
        fatigue: Alias per ATL (fatica accumulata).
        form: Alias per TSB (forma corrente).
        recovery_hours_needed: Ore di recupero stimate.
        weekly_tss: TSS accumulato negli ultimi 7 giorni.
        monthly_tss: TSS accumulato negli ultimi 30 giorni.
        trend_7d: Andamento ATL/CTL a 7 giorni ("in_aumento", "stable", "in_calo").
        trend_30d: Andamento ATL/CTL a 30 giorni.
        risk_indicators: Lista di segnali di allarme (es. "overtraining_risk").
        recommendation: Consiglio generato automaticamente dal sistema.
    """
    computed_at: datetime
    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0
    fitness: float = 0.0
    fatigue: float = 0.0
    form: float = 0.0
    recovery_hours_needed: float = 0.0
    weekly_tss: float = 0.0
    monthly_tss: float = 0.0
    trend_7d: str = "stable"
    trend_30d: str = "stable"
    risk_indicators: list[str] = field(default_factory=list)
    recommendation: str = ""

    @property
    def is_overtraining_risk(self) -> bool:
        """Indica se l'atleta e' a rischio di sovrallenamento.

        Condizione: ATL > 130% di CTL e TSB < -20.
        """
        return self.atl > self.ctl * 1.3 and self.tsb < -20

    @property
    def is_fresh(self) -> bool:
        """Indica se l'atleta e' in stato di freschezza (forma > 15)."""
        return self.tsb > 15

    @property
    def is_ready_for_hard_effort(self) -> bool:
        """Indica se l'atleta e' pronto per uno sforzo intenso.

        Condizione: TSB > 5 e ATL < 110% di CTL (fatica non eccessiva).
        """
        return self.tsb > 5 and self.atl < self.ctl * 1.1

    def to_dict(self) -> dict:
        return {
            "athlete_id": self.athlete_id,
            "computed_at": self.computed_at.isoformat(),
            "atl": round(self.atl, 1),
            "ctl": round(self.ctl, 1),
            "tsb": round(self.tsb, 1),
            "fitness": round(self.fitness, 1),
            "fatigue": round(self.fatigue, 1),
            "form": round(self.form, 1),
            "recovery_hours_needed": round(self.recovery_hours_needed, 1),
            "weekly_tss": round(self.weekly_tss, 1),
            "monthly_tss": round(self.monthly_tss, 1),
            "trend_7d": self.trend_7d,
            "trend_30d": self.trend_30d,
            "risk_indicators": self.risk_indicators,
            "recommendation": self.recommendation,
            "is_overtraining_risk": self.is_overtraining_risk,
            "is_fresh": self.is_fresh,
            "is_ready_for_hard_effort": self.is_ready_for_hard_effort,
        }
