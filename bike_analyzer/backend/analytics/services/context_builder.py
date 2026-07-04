"""Context Builder for AI Coach 2.0 - aggregates athlete context for LLM reasoning."""

from __future__ import annotations

from typing import Any


class ContextBuilder:
    """Builds comprehensive context for AI Coach recommendations.

    Aggregates:
    - Current Fitness State Vector (CTL/ATL/TSB)
    - Recent rides (last 5-10)
    - Athlete goals and profile
    - Recovery status and trends
    """

    def __init__(self, athlete_id: int, session_factory=None):
        self.athlete_id = athlete_id
        self._session_factory = session_factory

    def build_training_context(
        self,
        athlete: dict[str, Any] | None = None,
        rides: list[dict[str, Any]] | None = None,
        fitness_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = {
            "athlete": athlete or {},
            "fitness_state": fitness_state or {},
            "recent_rides": rides[:10] if rides else [],
            "trends": self._compute_trends(rides),
            "recommendations": self._recommendations_from_state(fitness_state),
        }
        return context

    def build_recovery_context(
        self,
        athlete: dict[str, Any] | None = None,
        rides: list[dict[str, Any]] | None = None,
        fitness_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        recovery_score = 10.0
        if fitness_state:
            tsb = fitness_state.get("tsb", 0)
            recovery_score = max(0, min(10, 5 + tsb / 10))

        context = {
            "athlete": athlete or {},
            "fitness_state": fitness_state or {},
            "recovery_score": round(recovery_score, 1),
            "hours_needed": fitness_state.get("recovery_hours_needed", 0) if fitness_state else 0,
            "recent_rides": rides[:5] if rides else [],
            "recovery_needed": recovery_score < 5,
            "explanation": self._build_explanation(fitness_state),
        }
        return context

    def _compute_trends(self, rides: list[dict[str, Any]] | None) -> dict[str, str]:
        if not rides or len(rides) < 2:
            return {"short_term": "stable", "long_term": "stable"}

        scores = [r.get("performance_score", 5.0) for r in rides[-5:]]
        avg = sum(scores) / len(scores)
        prev_avg = sum(scores[: len(scores) // 2]) / max(1, len(scores) // 2)

        short_trend = "improving" if avg > prev_avg + 0.5 else "declining" if avg < prev_avg - 0.5 else "stable"

        weekly_change = (rides[-1].get("weekly_tss", 0) - rides[-1].get("monthly_tss", 0) / 4) if rides else 0
        long_trend = "improving" if weekly_change > 10 else "declining" if weekly_change < -10 else "stable"

        return {"short_term": short_trend, "long_term": long_trend}

    def _recommendations_from_state(self, fitness_state: dict[str, Any] | None) -> list[str]:
        if not fitness_state:
            return []

        recs = []
        tsb = fitness_state.get("tsb", 0)
        atl = fitness_state.get("atl", 0)
        ctl = fitness_state.get("ctl", 0)

        if tsb > 15:
            recs.append("Pronto per sforzi intensi - TSB positivo indica freschezza")
        elif tsb > 5:
            recs.append("Quasi pronto per lavori quality - TSB moderato")
        elif tsb < -20:
            recs.append("Recupero prioritario - TSB negativo indica affaticamento")

        if atl > ctl * 1.3:
            recs.append("Attenzione a sovrallenamento - ATL sopra CTL")

        return recs

    def _build_explanation(self, fitness_state: dict[str, Any] | None) -> str:
        if not fitness_state:
            return "Nessun dato fitness disponibile"

        tsb = fitness_state.get("tsb", 0)
        atl = fitness_state.get("atl", 0)
        ctl = fitness_state.get("ctl", 0)
        recovery_hours = fitness_state.get("recovery_hours_needed", 0)

        reasons = []
        if tsb < -20:
            reasons.append(f"TSB è {tsb:.1f}, indica affaticamento accumulato")
        elif tsb > 15:
            reasons.append(f"TSB è {tsb:.1f}, indica buona freschezza")

        if atl > ctl * 1.2:
            reasons.append(f"ATL ({atl:.1f}) sopra il CTL ({ctl:.1f})")

        if recovery_hours > 24:
            reasons.append(f"Recupero stimato: {recovery_hours:.0f} ore")

        return " | ".join(reasons) if reasons else "Stato di forma stabile"

    async def fetch_full_context(self, include_history: bool = True) -> dict[str, Any]:
        athlete = None
        rides = []
        fitness_state = None

        if self._session_factory:
            from ..repositories.athlete_repository import AthleteRepository
            from ..repositories.fitness_state_repository import FitnessStateRepository
            from ..repositories.ride_repository import RideRepository

            athlete_repo = AthleteRepository(session_factory=self._session_factory)
            athlete = await athlete_repo.get_by_id(self.athlete_id)

            ride_repo = RideRepository(session_factory=self._session_factory)
            rides = await ride_repo.get_by_athlete(self.athlete_id)

            fs_repo = FitnessStateRepository(session_factory=self._session_factory)
            fitness_state = await fs_repo.get_latest(self.athlete_id)

        return self.build_training_context(athlete=athlete, rides=rides, fitness_state=fitness_state)
