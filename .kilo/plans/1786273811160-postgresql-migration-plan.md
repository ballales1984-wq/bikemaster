# Plan: PostgreSQL Migration for SQLite-Only Domains

## Context
On Render, SQLite data is ephemeral (lost on container resume). Domains already migrated to PostgreSQL are protected. This plan migrates the remaining SQLite-only domains to PostgreSQL, one domain module at a time.

## Priority Order (by data criticality)
1. **POI** (`pois`, `stages` FK) — simple schema, referenced by existing postgres_itineraries
2. **Users** (`users`) — auth-critical, small schema
3. **Calendar** (`calendar_events`) — moderate schema
4. **Chat** (`chat_history`) — simple schema
5. **Weather cache** (`weather_cache`) — simple, ephemeral but useful
6. **HR 24h** (`hr_24h_samples`, `hr_monitoring_settings`) — moderate schema
7. **Metabolic** (`metabolic_profiles`, `food_logs`, `metabolic_daily_summaries`, etc.) — complex, many tables
8. **Nutrition** (`nutrition_food_items`) — simple
9. **Beck assessments** (`beck_assessments`) — simple
10. **BLE devices** (`ble_devices`) — simple
11. **Fitness states** (`fitness_states`) — moderate
12. **Road incidents** (`road_incidents`) — simple
13. **Route safety scores** (`route_safety_scores`) — moderate
14. **Consent/Legal/AI Audit** (`user_consent`, `legal_acceptances`, `ai_audit_log`) — simple
15. **Sensor/Activity** (`sensor_data`, `daily_activity_classification`) — moderate

## Implementation Pattern (per domain)

### Step 1: Create `postgres_<domain>.py`
```python
def _url() -> str: ...
def has_postgres() -> bool: ...
def _connect(): ...
def _ensure_tables(conn): ...
# Public functions mirroring database.py signatures
def save_<entity>(...): ...
def get_<entity>(...): ...
# etc.
```

### Step 2: Add dispatch guards in `database.py`
```python
def save_<entity>(...):
    from .postgres_<domain> import has_postgres
    from .postgres_<domain> import save_<entity> as _pg_save
    if has_postgres():
        return _pg_save(...)
    # existing SQLite code
```

### Step 3: Run tests
```bash
pytest bike_analyzer/backend/db/
```

## First Domain: POI
- Tables: `pois`
- Functions: `save_poi`, `get_poi`, `list_pois`, `get_nearby_pois`, `delete_poi`
- Schema: simple (id, name, description, lat, lon, type, photos, video_url, difficulty_note, tags, itinerary_id, created_by, tenant_id, created_at)

## Risks
- Schema drift between SQLite and PostgreSQL definitions
- Missing dispatch guards for some functions
- Test failures due to connection issues

## Rollback
- Each domain module is independent
- Remove dispatch guard to fall back to SQLite
- No changes to existing postgres modules
