"""Export service - data aggregation for GDPR-style user data export."""

from __future__ import annotations

from datetime import UTC, datetime

from ...db.database import (
    get_ai_audit_logs_by_athlete,
    get_athlete,
    get_beck_assessments_by_athlete,
    get_consents_by_athlete,
    get_events_by_athlete,
    get_fitness_states_by_athlete,
    get_food_logs_by_athlete,
    get_legal_acceptances_by_athlete,
    get_metrics_by_athlete,
    get_rides_by_athlete,
    get_training_stress_days,
)
from ...analytics.repositories.athlete_repository import AthleteRepository
from ...analytics.repositories.ride_repository import RideRepository
from ...analytics.repositories.training_stress_repository import TrainingStressRepository


class ExportService:
    @staticmethod
    def export_all_my_data(user_id: str, tenant_id: int) -> dict:
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
