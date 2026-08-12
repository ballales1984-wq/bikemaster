"""PostgreSQL stubs for non-migrated domains.

These functions mirror the SQLite implementations in ``database.py`` but
raise ``RuntimeError`` when invoked on the managed PostgreSQL backend
(Render).  They exist solely to satisfy the ``@pg_dispatch`` decorator's
lazy import mechanism: when ``DATABASE_URL`` is configured the decorator
attempts to import the matching symbol from this module; without it the
import fails with ``ModuleNotFoundError`` and crashes startup.

Each domain listed below has not yet been migrated to PostgreSQL and
remains SQLite-only.  On Render (where the container has no persistent
volume) data for these domains is ephemeral, but the application must
still start cleanly.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _not_migrated(fn_name: str) -> None:
    raise RuntimeError(
        f"[postgres_stubs] '{fn_name}' is not yet migrated to PostgreSQL. "
        "This domain still uses the local SQLite store."
    )


def get_user_oauth_credentials(user_id: int, provider: str) -> dict | None:
    _not_migrated("get_user_oauth_credentials")


def get_all_user_oauth_credentials(user_id: int) -> list[dict]:
    _not_migrated("get_all_user_oauth_credentials")


def save_user_oauth_credentials(user_id: int, provider: str, data: dict) -> None:
    _not_migrated("save_user_oauth_credentials")


def delete_user_oauth_credentials(user_id: int, provider: str) -> bool:
    _not_migrated("delete_user_oauth_credentials")


def log_hr_sample(
    athlete_id: int,
    timestamp: str,
    hr_bpm: int,
    source: str = "manual",
    *,
    tenant_id: int = 0,
) -> int:
    _not_migrated("log_hr_sample")


def log_hr_samples(
    athlete_id: int,
    samples: list[dict],
    *,
    tenant_id: int = 0,
) -> int:
    _not_migrated("log_hr_samples")


def get_hr_24h_samples(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    _not_migrated("get_hr_24h_samples")


def get_hr_daily_summary(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int | None = None,
) -> dict | None:
    _not_migrated("get_hr_daily_summary")


def get_hr_settings(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    _not_migrated("get_hr_settings")


def upsert_hr_settings(
    athlete_id: int, settings: dict, *, tenant_id: int = 0
) -> dict:
    _not_migrated("upsert_hr_settings")


def delete_hr_settings(
    athlete_id: int, tenant_id: int | None = None
) -> bool:
    _not_migrated("delete_hr_settings")


def delete_hr_samples(
    athlete_id: int,
    *,
    tenant_id: int | None = None,
    older_than: str | None = None,
) -> int:
    _not_migrated("delete_hr_samples")


def log_sensor_data(
    athlete_id: int,
    sensor_type: str,
    value: float,
    unit: str,
    timestamp: str,
    *,
    tenant_id: int = 0,
) -> int:
    _not_migrated("log_sensor_data")


def classify_day(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int = 0,
) -> dict | None:
    _not_migrated("classify_day")


def get_activity_summary(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int = 0,
) -> dict | None:
    _not_migrated("get_activity_summary")


def get_activity_classification(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict | None:
    _not_migrated("get_activity_classification")


def save_metabolic_profile(
    profile: dict, athlete_id: int, tenant_id: int = 0
) -> int:
    _not_migrated("save_metabolic_profile")


def get_metabolic_profile(
    athlete_id: int, tenant_id: int | None = None
) -> dict | None:
    _not_migrated("get_metabolic_profile")


def save_food_log(log: dict, tenant_id: int = 0) -> int:
    _not_migrated("save_food_log")


def get_food_logs_by_athlete_date(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    _not_migrated("get_food_logs_by_athlete_date")


def update_food_log(log_id: int, log_data: dict) -> bool:
    _not_migrated("update_food_log")


def get_food_log(log_id: int) -> dict | None:
    _not_migrated("get_food_log")


def delete_food_log(log_id: int) -> bool:
    _not_migrated("delete_food_log")


def save_metabolic_daily_summary(summary: dict, tenant_id: int = 0) -> int:
    _not_migrated("save_metabolic_daily_summary")


def get_metabolic_daily_summaries(
    athlete_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: int | None = None,
    limit: int = 365,
) -> list[dict]:
    _not_migrated("get_metabolic_daily_summaries")


def get_metabolic_daily_summary(
    athlete_id: int,
    date: str,
    tenant_id: int | None = None,
) -> dict | None:
    _not_migrated("get_metabolic_daily_summary")


def upsert_metabolic_reference_value(value: dict, tenant_id: int = 0) -> int:
    _not_migrated("upsert_metabolic_reference_value")


def get_metabolic_reference_value(
    sex: str,
    age: int,
    weight_kg: float,
    activity_level: str = "moderate",
    tenant_id: int = 0,
) -> dict | None:
    _not_migrated("get_metabolic_reference_value")


def get_all_metabolic_reference_values(
    tenant_id: int | None = None,
) -> list[dict]:
    _not_migrated("get_all_metabolic_reference_values")


def save_metabolic_adaptive_weights(
    weights: dict, athlete_id: int, tenant_id: int = 0
) -> int:
    _not_migrated("save_metabolic_adaptive_weights")


def get_metabolic_adaptive_weights(
    athlete_id: int, tenant_id: int | None = None
) -> dict | None:
    _not_migrated("get_metabolic_adaptive_weights")


def save_chat_message(
    athlete_id: int | None, role: str, content: str, tenant_id: int = 0
) -> int:
    _not_migrated("save_chat_message")


def get_chat_history(
    athlete_id: int,
    limit: int = 10,
    tenant_id: int | None = None,
) -> list[dict]:
    _not_migrated("get_chat_history")


def clear_chat_history(
    athlete_id: int, tenant_id: int | None = None
) -> bool:
    _not_migrated("clear_chat_history")


def prune_chat_history(
    athlete_id: int,
    tenant_id: int | None = None,
    retention_days: int = 90,
) -> int:
    _not_migrated("prune_chat_history")


def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
    _not_migrated("get_weather_cache")


def save_weather_cache(
    lat: float, lon: float, date: str, weather: dict
) -> int:
    _not_migrated("save_weather_cache")


def save_road_incident(incident: dict) -> int:
    _not_migrated("save_road_incident")


def save_route_safety_score(
    score_data: dict, tenant_id: int = 0
) -> int:
    _not_migrated("save_route_safety_score")


def get_route_safety_score(
    ride_id: int, tenant_id: int | None = None
) -> dict | None:
    _not_migrated("get_route_safety_score")


def get_athlete_by_query(**query) -> dict | None:
    _not_migrated("get_athlete_by_query")


def save_poi(poi: dict) -> int:
    _not_migrated("save_poi")


def get_poi(poi_id: int, tenant_id: int | None = None) -> dict | None:
    _not_migrated("get_poi")


def get_nearby_pois(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    tenant_id: int | None = None,
) -> list[dict]:
    _not_migrated("get_nearby_pois")


def list_pois(
    itinerary_id: int | None = None,
    tenant_id: int | None = None,
) -> list[dict]:
    _not_migrated("list_pois")


def delete_poi(poi_id: int) -> bool:
    _not_migrated("delete_poi")


def seed_nutrition_food_items() -> None:
    _not_migrated("seed_nutrition_food_items")


def search_nutrition_food_items(
    query: str,
    category: str | None = None,
    limit: int = 50,
) -> list[dict]:
    _not_migrated("search_nutrition_food_items")


def get_nutrition_food_item(item_id: int) -> dict | None:
    _not_migrated("get_nutrition_food_item")


def list_nutrition_categories() -> list[str]:
    _not_migrated("list_nutrition_categories")


def save_nutrition_food_item(item: dict, tenant_id: int = 0) -> int:
    _not_migrated("save_nutrition_food_item")


def update_nutrition_food_item(item_id: int, item_data: dict) -> bool:
    _not_migrated("update_nutrition_food_item")


def delete_nutrition_food_item(item_id: int) -> bool:
    _not_migrated("delete_nutrition_food_item")


def save_beck_assessment(assessment: dict, tenant_id: int = 0) -> int:
    _not_migrated("save_beck_assessment")


def get_beck_assessment(assessment_id: int) -> dict | None:
    _not_migrated("get_beck_assessment")


def get_beck_assessments_by_athlete(
    athlete_id: int, tenant_id: int = 0, limit: int = 100
) -> list[dict]:
    _not_migrated("get_beck_assessments_by_athlete")


def get_fitness_states_by_athlete(
    athlete_id: int, tenant_id: int | None = None
) -> list[dict]:
    _not_migrated("get_fitness_states_by_athlete")


def get_food_logs_by_athlete(
    athlete_id: int,
    tenant_id: int | None = None,
    limit: int = 2000,
) -> list[dict]:
    _not_migrated("get_food_logs_by_athlete")


def get_latest_beck_assessment(
    athlete_id: int, tenant_id: int = 0
) -> dict | None:
    _not_migrated("get_latest_beck_assessment")


def register_ble_device(
    athlete_id: int,
    device_id: str,
    name: str,
    *,
    tenant_id: int = 0,
    device_type: str = "weight_scale",
    service_uuid: str | None = None,
    characteristic_uuid: str | None = None,
    mac_address: str | None = None,
    settings: str | None = None,
) -> int:
    _not_migrated("register_ble_device")


def get_ble_devices(
    athlete_id: int, tenant_id: int | None = None
) -> list[dict]:
    _not_migrated("get_ble_devices")


def get_ble_device(device_id: int, athlete_id: int) -> dict | None:
    _not_migrated("get_ble_device")


def update_ble_device(
    device_id: int, athlete_id: int, **updates
) -> dict | None:
    _not_migrated("update_ble_device")


def unregister_ble_device(device_id: int, athlete_id: int) -> bool:
    _not_migrated("unregister_ble_device")


def mark_ble_device_connected(device_id: int, athlete_id: int) -> None:
    _not_migrated("mark_ble_device_connected")


def mark_ble_device_synced(device_id: int, athlete_id: int) -> None:
    _not_migrated("mark_ble_device_synced")


def save_consent(
    athlete_id: int,
    consent_type: str,
    granted: bool = True,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    _not_migrated("save_consent")


def get_consent(athlete_id: int, consent_type: str) -> dict | None:
    _not_migrated("get_consent")


def get_consents_by_athlete(athlete_id: int) -> list[dict]:
    _not_migrated("get_consents_by_athlete")


def save_legal_acceptance(
    athlete_id: int,
    acceptance_type: str,
    version: str,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    _not_migrated("save_legal_acceptance")


def get_legal_acceptances_by_athlete(athlete_id: int) -> list[dict]:
    _not_migrated("get_legal_acceptances_by_athlete")


def has_accepted_version(
    athlete_id: int,
    acceptance_type: str,
    min_version: str,
) -> bool:
    _not_migrated("has_accepted_version")


def save_ai_audit_log(
    athlete_id: int,
    provider: str,
    model: str,
    prompt_hash: str,
    response_length: int = 0,
    tool_calls: int = 0,
    latency_ms: int = 0,
    tenant_id: int = 0,
) -> None:
    _not_migrated("save_ai_audit_log")


def get_ai_audit_logs_by_athlete(
    athlete_id: int, limit: int = 100
) -> list[dict]:
    _not_migrated("get_ai_audit_logs_by_athlete")
