"""Itinerary repository - data access abstraction for itineraries and stages."""

from __future__ import annotations

from ...db.database import (
    delete_itinerary,
    delete_stage,
    get_itinerary,
    get_stage,
    list_itineraries,
    list_stages,
    reorder_stages,
    save_itinerary,
    save_stage,
    update_itinerary,
    update_stage,
)


class ItineraryRepository:
    @staticmethod
    def save_itinerary(data: dict):
        return save_itinerary(data)

    @staticmethod
    def list_itineraries(athlete_id: int | None = None):
        return list_itineraries(athlete_id)

    @staticmethod
    def get_itinerary(itinerary_id: int):
        return get_itinerary(itinerary_id)

    @staticmethod
    def update_itinerary(itinerary_id: int, data: dict, tenant_id: int = 0):
        return update_itinerary(itinerary_id, data, tenant_id)

    @staticmethod
    def delete_itinerary(itinerary_id: int, tenant_id: int = 0):
        return delete_itinerary(itinerary_id, tenant_id)

    @staticmethod
    def save_stage(data: dict):
        return save_stage(data)

    @staticmethod
    def list_stages(itinerary_id: int):
        return list_stages(itinerary_id)

    @staticmethod
    def get_stage(stage_id: int):
        return get_stage(stage_id)

    @staticmethod
    def update_stage(stage_id: int, data: dict, tenant_id: int = 0):
        return update_stage(stage_id, data, tenant_id)

    @staticmethod
    def delete_stage(stage_id: int, tenant_id: int = 0):
        return delete_stage(stage_id, tenant_id)

    @staticmethod
    def reorder_stages(itinerary_id: int, stage_order: list[int], tenant_id: int = 0):
        return reorder_stages(itinerary_id, stage_order, tenant_id)
