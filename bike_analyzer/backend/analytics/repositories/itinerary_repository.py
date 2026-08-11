"""Itinerary repository - data access abstraction for itineraries and stages."""

from __future__ import annotations


class ItineraryRepository:
    @staticmethod
    def save_itinerary(data: dict):
        from ...db.database import save_itinerary

        return save_itinerary(data)

    @staticmethod
    def list_itineraries(athlete_id: int | None = None):
        from ...db.database import list_itineraries

        return list_itineraries(athlete_id)

    @staticmethod
    def get_itinerary(itinerary_id: int):
        from ...db.database import get_itinerary

        return get_itinerary(itinerary_id)

    @staticmethod
    def update_itinerary(itinerary_id: int, data: dict, tenant_id: int = 0):
        from ...db.database import update_itinerary

        return update_itinerary(itinerary_id, data, tenant_id)

    @staticmethod
    def delete_itinerary(itinerary_id: int, tenant_id: int = 0):
        from ...db.database import delete_itinerary

        return delete_itinerary(itinerary_id, tenant_id)

    @staticmethod
    def save_stage(data: dict):
        from ...db.database import save_stage

        return save_stage(data)

    @staticmethod
    def list_stages(itinerary_id: int):
        from ...db.database import list_stages

        return list_stages(itinerary_id)

    @staticmethod
    def get_stage(stage_id: int):
        from ...db.database import get_stage

        return get_stage(stage_id)

    @staticmethod
    def update_stage(stage_id: int, data: dict, tenant_id: int = 0):
        from ...db.database import update_stage

        return update_stage(stage_id, data, tenant_id)

    @staticmethod
    def delete_stage(stage_id: int, tenant_id: int = 0):
        from ...db.database import delete_stage

        return delete_stage(stage_id, tenant_id)

    @staticmethod
    def reorder_stages(itinerary_id: int, stage_order: list[int], tenant_id: int = 0):
        from ...db.database import reorder_stages

        return reorder_stages(itinerary_id, stage_order, tenant_id)
