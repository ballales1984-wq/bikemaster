"""Legal repository - data access abstraction for legal/consent data."""

from __future__ import annotations

from ...db.database import (
    get_consents_by_athlete,
    get_legal_acceptances_by_athlete,
    save_consent,
    save_legal_acceptance,
)


class LegalRepository:
    @staticmethod
    def save_consent(athlete_id: int, consent_type: str, granted: bool, source: str, tenant_id: int = 0):
        return save_consent(
            athlete_id=athlete_id,
            consent_type=consent_type,
            granted=granted,
            source=source,
            tenant_id=tenant_id,
        )

    @staticmethod
    def get_consents_by_athlete(athlete_id: int):
        return get_consents_by_athlete(athlete_id)

    @staticmethod
    def save_legal_acceptance(athlete_id: int, acceptance_type: str, version: str, source: str, tenant_id: int = 0):
        return save_legal_acceptance(
            athlete_id=athlete_id,
            acceptance_type=acceptance_type,
            version=version,
            source=source,
            tenant_id=tenant_id,
        )

    @staticmethod
    def get_legal_acceptances_by_athlete(athlete_id: int):
        return get_legal_acceptances_by_athlete(athlete_id)
