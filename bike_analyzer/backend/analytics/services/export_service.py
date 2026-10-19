"""Export service - data aggregation for GDPR-style user data export.

Collects all personal data for a user/athlete across all domains
(rides, metrics, calendar, fitness, nutrition, legal, audit) into a
single JSON-compatible dict for download.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...analytics.repositories.athlete_repository import AthleteRepository
from ...analytics.repositories.ride_repository import RideRepository
from ...analytics.repositories.training_stress_repository import TrainingStressRepository
from ...db.database import (
    get_ai_audit_logs_by_athlete,
    get_beck_assessments_by_athlete,
    get_consents_by_athlete,
    get_events_by_athlete,
    get_fitness_states_by_athlete,
    get_food_logs_by_athlete,
    get_legal_acceptances_by_athlete,
    get_metrics_by_athlete,
)


class ExportService:
    """Service for exporting all user data (GDPR data portability)."""

    @staticmethod
    def export_all_my_data(user_id: str, tenant_id: int) -> dict:
        """Aggregate all athlete data into a single export dict.

        Queries every data domain (rides, metrics, calendar, fitness,
        nutrition, legal, audit) and returns a JSON-serializable dict
        with an ``exported_at`` timestamp.

        Args:
            user_id: User/athlete identifier string.
            tenant_id: Tenant id for multi-tenant isolation.

        Returns:
            Dict with keys: ``user``, ``athlete``, ``rides``, ``metrics``,
            ``calendar_events``, ``fitness_states``, ``training_stress_days``,
            ``food_logs``, ``beck_assessments``, ``legal_acceptances``,
            ``consents``, ``ai_audit_logs``, ``exported_at``.
        """
        athlete_id = int(user_id)
        now = datetime.now(UTC).isoformat()
        return {
            "user": {"id": user_id},
            "athlete": AthleteRepository().get_by_id(athlete_id, tenant_id),
            "rides": RideRepository().list_all(athlete_id=athlete_id, tenant_id=tenant_id),
            "metrics": get_metrics_by_athlete(athlete_id, tenant_id),
            "calendar_events": get_events_by_athlete(athlete_id, tenant_id),
            "fitness_states": get_fitness_states_by_athlete(athlete_id, tenant_id),
            "training_stress_days": TrainingStressRepository.get_training_stress_days(athlete_id, tenant_id=tenant_id),
            "food_logs": get_food_logs_by_athlete(athlete_id, tenant_id),
            "beck_assessments": get_beck_assessments_by_athlete(athlete_id, tenant_id),
            "legal_acceptances": get_legal_acceptances_by_athlete(athlete_id),
            "consents": get_consents_by_athlete(athlete_id),
            "ai_audit_logs": get_ai_audit_logs_by_athlete(athlete_id, limit=500),
            "exported_at": now,
        }
