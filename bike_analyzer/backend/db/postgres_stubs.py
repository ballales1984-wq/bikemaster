"""PostgreSQL stubs for non-migrated domains.

These functions mirror the SQLite implementations in ``database.py`` but
raise ``RuntimeError`` when invoked on the managed PostgreSQL backend
(Render).  They exist solely to satisfy the ``@pg_dispatch`` decorator's
lazy import mechanism: when ``DATABASE_URL`` is configured the decorator
attempts to import the matching symbol from this module; without it the
import fails with ``ModuleNotFoundError`` and crashes startup.

Domains migrated in this file are no longer stubbed here; they live in
their own ``postgres_*.py`` modules.  Only truly unmigrated domains remain
below.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _not_migrated(fn_name: str) -> None:
    raise RuntimeError(
        f"[postgres_stubs] '{fn_name}' is not yet migrated to PostgreSQL. "
        "This domain still uses the local SQLite store."
    )


# user oauth (migrated to postgres_user_oauth.py)
def get_user_oauth_credentials(user_id: int, provider: str) -> dict | None:
    _not_migrated("get_user_oauth_credentials")


def get_all_user_oauth_credentials(user_id: int) -> list[dict]:
    _not_migrated("get_all_user_oauth_credentials")


def save_user_oauth_credentials(user_id: int, provider: str, data: dict) -> None:
    _not_migrated("save_user_oauth_credentials")


def delete_user_oauth_credentials(user_id: int, provider: str) -> bool:
    _not_migrated("delete_user_oauth_credentials")


# hr
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


# sensor / activity
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


# chat
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


# nutrition
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


# ble
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


# legal / consent / audit
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
