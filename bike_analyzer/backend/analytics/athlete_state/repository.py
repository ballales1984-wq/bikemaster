"""Athlete State Repository - persistence for AthleteStateModel.

Reuses the existing ``FitnessStateRepository`` for the overlapping columns and
stores additional athlete-state fields (fatigue_score, readiness, acwr,
risk_level) inside the ``risk_indicators`` JSON payload so no DB migration is
required.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..repositories.fitness_state_repository import FitnessStateRepository
from .models import AthleteState


class AthleteStateRepository:
    """Repository for AthleteStateModel persistence."""

    def __init__(self, session_factory=None, sync_conn=None):
        self._fitness_repo = FitnessStateRepository(session_factory, sync_conn)

    async def save(self, state: AthleteState, tenant_id: int = 0) -> int:
        payload = self._to_fitness_dict(state, tenant_id)
        return await self._fitness_repo.save(payload, tenant_id)

    async def get_latest(self, athlete_id: int, tenant_id: int = 0) -> AthleteState | None:
        row = await self._fitness_repo.get_latest(athlete_id, tenant_id)
        if row is None:
            return None
        return self._from_fitness_row(row)

    async def get_history(
        self, athlete_id: int, days: int = 30, tenant_id: int = 0
    ) -> list[AthleteState]:
        rows = await self._fitness_repo.get_history(athlete_id, days, tenant_id)
        return [self._from_fitness_row(r) for r in rows]

    def _to_fitness_dict(self, state: AthleteState, tenant_id: int) -> dict[str, Any]:
        extra = {
            "fatigue_score": state.fatigue_score,
            "readiness": state.readiness,
            "acwr": state.acwr,
            "risk_level": state.risk_level,
        }
        existing = (state.risk_indicators or []) + [json.dumps(extra)]
        return {
            "athlete_id": state.athlete_id,
            "tenant_id": tenant_id,
            "date": state.computed_at.date().isoformat(),
            "computed_at": state.computed_at,
            "fitness": state.ctl,
            "form": state.tsb,
            "atl": state.atl,
            "ctl": state.ctl,
            "tsb": state.tsb,
            "recovery_hours_needed": state.recovery_hours_needed,
            "weekly_tss": state.weekly_tss,
            "monthly_tss": state.monthly_tss,
            "trend_7d": state.trend_7d,
            "trend_30d": state.trend_30d,
            "risk_indicators": existing,
            "recommendation": state.recommendation,
        }

    def _from_fitness_row(self, row: dict[str, Any]) -> AthleteState:
        extra: dict[str, Any] = {}
        raw = row.get("risk_indicators") or []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    try:
                        parsed = json.loads(item)
                        if isinstance(parsed, dict):
                            extra.update(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    extra.update(parsed)
            except (json.JSONDecodeError, TypeError):
                pass

        return AthleteState(
            athlete_id=row.get("athlete_id", 0),
            computed_at=row.get("computed_at") or datetime.now(UTC),
            atl=row.get("atl", 0.0) or 0.0,
            ctl=row.get("ctl", 0.0) or 0.0,
            tsb=row.get("tsb", 0.0) or 0.0,
            fitness=row.get("fitness", 0.0) or 0.0,
            form=row.get("form", 0.0) or 0.0,
            fatigue_score=extra.get("fatigue_score", 0.0),
            readiness=extra.get("readiness", 100.0),
            acwr=extra.get("acwr", 1.0),
            recovery_hours_needed=row.get("recovery_hours_needed", 0.0) or 0.0,
            weekly_tss=row.get("weekly_tss", 0.0) or 0.0,
            monthly_tss=row.get("monthly_tss", 0.0) or 0.0,
            trend_7d=row.get("trend_7d", "stable") or "stable",
            trend_30d=row.get("trend_30d", "stable") or "stable",
            risk_indicators=row.get("risk_indicators", []) if isinstance(row.get("risk_indicators"), list) else [],
            recommendation=row.get("recommendation", "") or "",
            risk_level=extra.get("risk_level", "ok"),
        )


__all__ = ["AthleteStateRepository"]
