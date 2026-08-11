# Report di Revisone Architetturale — `db/` e dipendenze

## 1. Struttura di `database.py`

| Metrica | Valore |
|---------|--------|
| File | `D:\BikeMaster\bike_analyzer\backend\db\database.py` |
| Righe totali | **4.224** |
| Funzioni pubbliche | **~100** |
| Tabelle gestite | **~30** (CREATE TABLE + ALTER TABLE) |

`database.py` è un **"god object"** in forma procedurale. Contiene:

- **Schema definitions**: `init_db()` (righe 111-1079) crea tutte le tabelle SQLite con `CREATE TABLE IF NOT EXISTS` + migrazioni inline `ALTER TABLE`.
- **Context manager**: `get_db_connection()` (righe 68-108) con WAL, busy_timeout, retry su lock.
- **CRUD per ogni dominio**: athletes, rides, metrics, training_stress_days, chat_history, calendar_events, weather_cache, pois, itineraries, stages, fitness_states, metabolic_profiles, food_logs, metabolic_daily_summaries, metabolic_reference_values, metabolic_adaptive_weights, performance_metrics, ftp_history, nutrition_food_items, beck_assessments, ble_devices, hr_24h_samples, hr_monitoring_settings, sensor_data, daily_activity_classification, strava_tokens, garmin_tokens, wahoo_tokens, users, user_consent, legal_acceptances, ai_audit_log, knowledge_chunks, audit_logs, sessions, segments, pauses, external_identities, external_tokens, totp_secrets, revoked_tokens.
- **Business logic mista**: `classify_day()` (righe 1641-1776) combina HR, rides e metabolico per derivare label attività; `seed_nutrition_food_items()` (righe 3492-3574) hardcoda 50 item alimentari.
- **Backup/rotazione**: `backup_database()`, `rotate_backups()`, `scheduled_backup()`.
- **Dispatch PostgreSQL**: 7 funzioni decorate con `@pg_dispatch(...)` (righe 1177, 2760, 2892, 2915, 3792, 3207, 3233, 3261, 3290, 3315, 3374, 3415, 3432).
- **Import diretti**: `from ..models.models import Ride` e `from .repositories.athlete_repository import ...` / `from .repositories.ride_repository import ...` (righe 35-59).

**Problemi**:单文件 4.224 righe, mistura di schema migration, CRUD, business logic e seeding. Nessuna separazione tra domini. Le migrazioni ALTER TABLE sono sparse e ripetute.

---

## 2. Dispatch SQLite/PostgreSQL

### Come funziona `dispatch.py`
`dispatch.py` (165 righe) definisce:
- `is_postgres()`: single source of truth basata su `DATABASE_URL`.
- `POSTGRES_BACKENDS`: dizionario che mappa domini migrati → modulo Python + lista funzioni.
- `pg_dispatch(pg_module_name)`: decorator che, a runtime, se `is_postgres()` è true, importa lazy il modulo PostgreSQL e chiama la funzione omonima; altrimenti esegue il corpo SQLite.

### Moduli PostgreSQL esistenti
| Modulo | Righe | Tabelle gestite |
|--------|-------|-----------------|
| `postgres_athlete.py` | 633 | athletes, athlete_metric_log, athlete_history |
| `postgres_rides.py` | 507 | rides, metrics, training_stress_days |
| `postgres_itineraries.py` | 404 | itineraries, stages |
| `postgres_db.py` | 124 | training_goals, planned_workouts (via SQLAlchemy sync) |

### Domini migrati vs non migrati
**Migrati (via `@pg_dispatch`)**:
- Athlete (profile, history, metric log)
- Rides / metrics / training stress (TSS, ATL, CTL, TSB)
- Itineraries + stages

**Migrati ma fuori da `@pg_dispatch`** (usano direttamente SQLAlchemy in `postgres_db.py`):
- Training goals / planned workouts

**NON migrati (SQLite-only, dati persi al resume su Render)**:
- POI (`save_poi`, `get_poi`, `list_pois`, `get_nearby_pois`, `delete_poi`)
- HR 24h (`log_hr_sample`, `log_hr_samples`, `get_hr_24h_samples`, `get_hr_daily_summary`, `get_hr_settings`, `upsert_hr_settings`, `delete_hr_settings`, `delete_hr_samples`)
- Metabolico/food logs (`save_metabolic_profile`, `get_metabolic_profile`, `save_food_log`, `get_food_logs_by_athlete_date`, `update_food_log`, `get_food_log`, `delete_food_log`, `save_metabolic_daily_summary`, `get_metabolic_daily_summaries`, `get_metabolic_daily_summary`, `upsert_metabolic_reference_value`, `get_metabolic_reference_value`, `get_all_metabolic_reference_values`, `save_metabolic_adaptive_weights`, `get_metabolic_adaptive_weights`)
- Chat (`save_chat_message`, `get_chat_history`, `clear_chat_history`, `prune_chat_history`)
- Calendario (`save_calendar_event`, `get_calendar_event`, `get_events_by_athlete`, `get_events_by_date_range`, `get_events_by_month`, `update_calendar_event`, `delete_calendar_event`)
- Weather cache (`save_weather_cache`, `get_weather_cache`)
- Road incidents (`save_road_incident`)
- Route safety scores (`save_route_safety_score`, `get_route_safety_score`)
- Fitness states (`get_fitness_states_by_athlete`)
- Nutrition (`save_nutrition_food_item`, `search_nutrition_food_items`, `get_nutrition_food_item`, `list_nutrition_categories`, `update_nutrition_food_item`, `delete_nutrition_food_item`, `seed_nutrition_food_items`)
- Beck assessments (`save_beck_assessment`, `get_beck_assessment`, `get_beck_assessments_by_athlete`, `get_latest_beck_assessment`)
- BLE devices (`register_ble_device`, `get_ble_devices`, `get_ble_device`, `update_ble_device`, `unregister_ble_device`, `mark_ble_device_connected`, `mark_ble_device_synced`)
- Users (`save_user`, `get_user_by_username`, `get_user_by_id`, `get_all_users`, `update_user`, `delete_user`)
- Consent/legal/ai_audit (`save_consent`, `get_consent`, `get_consents_by_athlete`, `save_legal_acceptance`, `get_legal_acceptances_by_athlete`, `has_accepted_version`, `save_ai_audit_log`, `get_ai_audit_logs_by_athlete`)
- Sensor/activity (`log_sensor_data`, `classify_day`, `get_activity_summary`, `get_activity_classification`)
- Sync/backup (`backup_database`, `scheduled_backup`, `rotate_backups`)

### Problemi di coerenza
- `training_goals` non ha un twin SQLite in `database.py`; esiste solo via `postgres_db.py` + SQLAlchemy. Questo è documentato in `dispatch.py` riga 120-122, ma crea un buco nella migrazione.
- Le colonne `updated_at` mancano in alcune tabelle PostgreSQL `postgres_rides.py` (es. `rides` ha `updated_at` nel DDL ma non tutte le INSERT lo popolano).
- `postgres_itineraries.py` usa `TIMESTAMP WITH TIME ZONE` nel DDL ma `datetime.now(UTC).isoformat()` (stringa) nei dati — coerenza con SQLite (TEXT) ma non con SQLAlchemy models (DateTime).

---

## 3. Repository esistenti

### `db/repositories/` (2 file)
| File | Funzioni esposte | Note |
|------|-----------------|------|
| `athlete_repository.py` | `get_athlete_by_name`, `get_athlete_by_email`, `save_athlete`, `get_athlete`, `save_athlete_snapshot`, `get_athlete_history`, `update_athlete`, `get_athletes_by_user`, `get_athlete_count_by_user`, `delete_athlete`, `log_athlete_metric`, `get_athlete_metric_log` | Usa `@pg_dispatch` su metà delle funzioni. Importa da `..database` (lazy dentro funzioni). |
| `ride_repository.py` | `save_ride`, `get_ride`, `get_rides_by_athlete`, `get_all_rides`, `delete_ride`, `update_ride`, `_find_existing_external_ride`, `_row_to_ride` | Usa `@pg_dispatch` su tutte le funzioni pubbliche. Importa da `...models.models.Ride` per validazione calorie. |

### `analytics/repositories/` (17 file)
| File | Note |
|------|------|
| `athlete_repository.py` | Wrapper AthleteRepository con sync/async dual-mode. Importa da `..db.database` (lazy). |
| `ride_repository.py` | Wrapper RideRepository con sync/async dual-mode. Importa da `...db.models.RideModel` e `..db.database` (lazy). |
| `training_stress_repository.py` | Usa SQLAlchemy Table + sync fallback a `..db.database`. |
| `user_repository.py` | Doppia implementazione: async SQLAlchemy + sync SQLite diretto (senza passare per `database.py`). |
| `user_oauth_repository.py` | - |
| `itinerary_repository.py` | - |
| `performance_repository.py` | - |
| `hr_repository.py` | - |
| `ai_audit_repository.py` | - |
| `ble_repository.py` | - |
| `legal_repository.py` | - |
| `calendar_repository.py` | - |
| `chat_repository.py` | - |
| `chat_history_repository.py` | - |
| `poi_repository.py` | - |
| `fitness_state_repository.py` | - |
| `metabolism_repository.py` | - |

### Quanti sono realmente usati dai router?
**Router che usano analytics repositories** (via import diretto):
- `analytics_routes.py`: `athlete_repository`, `ride_repository`
- `auth_routes.py`: `athlete_repository`, `user_oauth_repository`
- `badges_routes.py`: `athlete_repository`, `ride_repository`
- `ble_routes.py`: `ble_repository`
- `calendar_routes.py`: `calendar_repository`
- `charts_routes.py`: `ride_repository`
- `coach_routes.py`: `athlete_repository`, `ride_repository`, `chat_repository`
- `hr_routes.py`: `hr_repository`
- `itineraries_routes.py`: `itinerary_repository`
- `legal_routes.py`: `legal_repository`, `athlete_repository`
- `maps_routes.py`: `poi_repository`, `ride_repository`
- `training_routes.py`: `ride_repository`

**Router che NON usano analytics repositories**:
- `import_routes.py`: nessun db diretto
- `knowledge_routes.py`: importa `postgres_db` direttamente
- `notifications_routes.py`: nessun db diretto
- `traffic_routes.py`: nessun db diretto
- `weather_routes.py`: nessun db diretto

### Duplicati o inutili
- `db/repositories/athlete_repository.py` e `analytics/repositories/athlete_repository.py`: **duplicati parziali**. Il primo è usato da `database.py`; il secondo è usato dai router. Stesse funzioni, implementazioni diverse (async vs sync).
- `db/repositories/ride_repository.py` e `analytics/repositories/ride_repository.py`: **duplicati parziali**. Stesso pattern.
- `analytics/repositories/user_repository.py`: ridefinisce CRUD users da zero invece di riusare `database.py` o `postgres_db.py`.
- `analytics/repositories/training_stress_repository.py`: ridefinisce le query con SQLAlchemy Table + fallback sync, duplicando logica già in `postgres_rides.py` e `database.py`.

---

## 4. Chiamate dirette a `db.database`

### Router che chiamano direttamente `database.py`
**Nessun router** chiama direttamente `database.py` con import statico. Tutti passano per `analytics/repositories/` o per lazy import in `api/routes.py`.

### `api/routes.py` — lazy import diretti (3 punti)
| Riga | Funzione chiamata | Uso |
|------|------------------|-----|
| 517 | `get_user_oauth_credentials` | `_get_user_oauth_creds()` per OAuth |
| 558 | `get_rides_by_athlete` | `_get_athlete_rides()` per access control |
| 713 | `scheduled_backup` | endpoint `/cron` per manutenzione |

### Altri moduli che chiamano direttamente `database.py`
| Modulo | Funzioni chiamate |
|--------|------------------|
| `weather/weather_repository.py` | `get_weather_cache`, `save_weather_cache` |
| `ingestion/garmin_client.py` | `get_db_connection` |
| `ingestion/health_connect.py` | `get_db_connection`, `log_athlete_metric` |
| `ingestion/google_oauth_store.py` | `get_db_connection` |
| `ingestion/wahoo_client.py` | `get_db_connection` |
| `rate_limiter.py` | `get_db_connection` |
| `sync/service.py` | `get_db_connection` |
| `sync/db_helpers.py` | `get_db_connection` |
| `sync/config.py` | `get_db_connection` |
| `analytics/training_load.py` | `get_rides_by_athlete`, `upsert_training_stress_day` |
| `analytics/repositories/athlete_repository.py` | `save_athlete`, `get_athlete`, `get_all_athletes`, `delete_athlete` |
| `analytics/repositories/training_stress_repository.py` | `upsert_training_stress_day`, `get_training_stress_days`, `get_latest_training_stress` |

---

## 5. Modelli duplicati

### `db/models.py` (1.170 righe)
SQLAlchemy ORM models per async/sync cloud layer. 30+ classi:
- `UserModel`, `AthleteModel`, `RideModel`, `MetricModel`, `TrainingStressDayModel`, `FitnessStateModel`, `TrainingGoalModel`, `PlannedWorkoutModel`, `RoadIncident`, `RouteSafetyScore`, `POIModel`, `ItineraryModel`, `StageModel`, `StravaToken`, `GarminToken`, `SyncEntityState`, `SyncSetting`, `SyncConflict`, `KnowledgeChunkModel`, `AuditLog`, `SessionModel`, `SegmentModel`, `PauseModel`, `ExternalIdentityModel`, `ExternalTokenModel`, `TOTPSecretModel`, `MetabolicProfileModel`, `FoodLogModel`, `MetabolicDailySummaryModel`, `BeckAssessmentModel`, `MetabolicReferenceValueModel`, `MetabolicAdaptiveWeightsModel`, `AetherMapObjectModel`, `AetherMapStateHistoryModel`.

### `models/models.py` (61 righe)
Wrapper dataclass che **re-esporta** da `bike_analyzer.core.models`:
- `Ride(_CoreRide)` con `to_dict()` custom
- `AthleteProfile`, `GPSPoint`, `Segment`, `Pause`, `RouteStatistics`, `CalendarEvent`, `haversine_distance_m`, `EARTH_RADIUS_M`

### `api/schemas.py` (1.083 righe)
Pydantic schemas per request/response validation. 50+ classi.

### Duplicazioni e problemi
| Tipo | Dettaglio |
|------|-----------|
| **Schema duplication** | `db/models.py` ridefinisce tutti i campi in SQLAlchemy; `database.py` ridefinisce tutti i campi in SQLite DDL; `models/models.py` ridefinisce `Ride` come dataclass. Tre definizioni dello stesso concetto. |
| **Colonne mancanti in SQLite DDL** | Alcune tabelle in `database.py` mancano di colonne presenti in `db/models.py` (es. `rides.updated_at` aggiunta via ALTER, ma non in tutte le tabelle). |
| **Tipi incompatibili** | `db/models.py` usa `DateTime(timezone=True)` (aware); `database.py` usa `TEXT` con `datetime.now(UTC).isoformat()` (stringa). |
| **Modelli mancanti** | Non esiste un ORM model SQLAlchemy per: `hr_24h_samples`, `hr_monitoring_settings`, `sensor_data`, `daily_activity_classification`, `pois` (mancava in `db/models.py` fino a poco fa?), `nutrition_food_items`, `ble_devices`, `user_consent`, `legal_acceptances`, `ai_audit_log`, `revoked_tokens`, `totp_secrets`, `external_identities`, `external_tokens`, `oauth_locks`, `user_oauth_credentials`, `sync_entity_state`, `sync_settings`, `sync_conflicts`. |
| **Pydantic duplicati** | `api/schemas.py` ridefinisce campi già in `models/models.py` e `db/models.py` senza condivisione. Es. `RideCreate` vs `Ride` vs `RideModel`. |

---

## 6. Piano di smontaggio di `database.py`

### Funzioni da estrarre per prime (basso rischio)
1. **`init_db()`** → `db/migrations.py` (già esistente, ma va completato)
2. **`get_db_connection()`** → `db/connection.py` (context manager isolato)
3. **Backup functions** (`backup_database`, `rotate_backups`, `scheduled_backup`, `get_backup_dir`) → `db/backup.py`
4. **Nutrition seeding** (`seed_nutrition_food_items`) → `db/seed.py`
5. **OAuth lock** (`acquire_oauth_sqlite_lock`, `release_oauth_sqlite_lock`, `_ensure_oauth_lock_table`) → `db/oauth_locks.py`

### Funzioni da estrarre per secondo (medio rischio)
6. **HR 24h** (`log_hr_sample`, `log_hr_samples`, `get_hr_24h_samples`, `get_hr_daily_summary`, `get_hr_settings`, `upsert_hr_settings`, `delete_hr_settings`, `delete_hr_samples`) → `db/repositories/hr_repository.py`
7. **Sensor/activity** (`log_sensor_data`, `classify_day`, `get_activity_summary`, `get_activity_classification`, `_get_max_hr_setting`, `_get_resting_hr_setting`) → `db/repositories/activity_repository.py`
8. **Metabolico** (`save_metabolic_profile`, `get_metabolic_profile`, `save_food_log`, `get_food_logs_by_athlete_date`, `update_food_log`, `get_food_log`, `delete_food_log`, `save_metabolic_daily_summary`, `get_metabolic_daily_summaries`, `get_metabolic_daily_summary`, `upsert_metabolic_reference_value`, `get_metabolic_reference_value`, `get_all_metabolic_reference_values`, `save_metabolic_adaptive_weights`, `get_metabolic_adaptive_weights`) → `db/repositories/metabolism_repository.py`
9. **Chat** (`save_chat_message`, `get_chat_history`, `clear_chat_history`, `prune_chat_history`) → `db/repositories/chat_repository.py`
10. **Calendario** (`save_calendar_event`, `get_calendar_event`, `get_events_by_athlete`, `get_events_by_date_range`, `get_events_by_month`, `update_calendar_event`, `delete_calendar_event`, `_row_to_calendar_event`) → `db/repositories/calendar_repository.py`

### Funzioni da estrarre per terze (alto rischio)
11. **POI** (`save_poi`, `get_poi`, `get_nearby_pois`, `list_pois`, `delete_poi`, `_row_to_poi`) → `db/repositories/poi_repository.py`
12. **Itinerari/Stages** (`save_itinerary`, `get_itinerary`, `list_itineraries`, `save_stage`, `list_stages`, `get_stage`, `update_itinerary`, `delete_itinerary`, `update_stage`, `delete_stage`, `reorder_stages`, `_row_to_itinerary`, `_row_to_stage`) → `db/repositories/itinerary_repository.py`
13. **Users/Auth** (`save_user`, `get_user_by_username`, `get_user_by_id`, `get_all_users`, `update_user`, `delete_user`) → `db/repositories/user_repository.py`
14. **Consent/Legal/Audit** (`save_consent`, `get_consent`, `get_consents_by_athlete`, `save_legal_acceptance`, `get_legal_acceptances_by_athlete`, `has_accepted_version`, `save_ai_audit_log`, `get_ai_audit_logs_by_athlete`) → `db/repositories/legal_repository.py`
15. **BLE** (`register_ble_device`, `get_ble_devices`, `get_ble_device`, `update_ble_device`, `unregister_ble_device`, `mark_ble_device_connected`, `mark_ble_device_synced`) → `db/repositories/ble_repository.py`
16. **Fitness states** (`get_fitness_states_by_athlete`) → `db/repositories/fitness_repository.py`
17. **Road safety** (`save_road_incident`, `save_route_safety_score`, `get_route_safety_score`) → `db/repositories/safety_repository.py`
18. **Training stress** (`upsert_training_stress_day`, `get_training_stress_days`, `get_latest_training_stress`) — già in `postgres_rides.py`, ma twin SQLite rimane in `database.py`
19. **Metrics** (`save_metric`, `get_metrics_by_athlete`) — già in `postgres_rides.py`, twin SQLite in `database.py`

### Dipendenze più pericolose
- **`database.py` → `repositories/athlete_repository.py` → `database.py`**: circolare a compile-time se rimossa la lazy import. Soluzione: invertire la dipendenza (repositories non importano `database.py`, ma `database.py` importa repositories).
- **`database.py` → `repositories/ride_repository.py` → `...models.models.Ride` → `bike_analyzer.core.models`**: catena di import lunga. Se `core/models.py` cambia, rompe tutto.
- **`postgres_rides.py` → `postgres_athlete.py`**: dipendenza tra moduli PostgreSQL. Se `postgres_athlete.py` viene refactorato, `postgres_rides.py` e `postgres_itineraries.py` si rompono.

### Rischio di rompere qualcosa
- **Alto**: `classify_day()` dipende da `get_hr_settings()` e da tabelle metabolico. È business logic spalmata su 3 tabelle.
- **Alto**: `save_athlete()` in `repositories/athlete_repository.py` chiama `save_athlete_snapshot()` con `conn` opzionale — accoppiamento transazionale.
- **Medio**: `_row_to_ride` e `_row_to_athlete` sono usati da `postgres_rides.py` e `postgres_athlete.py` per normalizzare le risposte. Se cambiano i nomi colonne, i moduli PostgreSQL si rompono silenziosamente.
- **Basso**: Funzioni di utility come `backup_database`, `seed_nutrition_food_items`, `create_indices` sono auto-contained.

---

## 7. Problemi di temporalità / data lineage

### Gestione date attuale
- **SQLite**: tutti i timestamp sono salvati come `TEXT` in formato ISO-8601 UTC (es. `2026-08-11T17:00:08.489Z`).
- **SQLAlchemy models**: usano `DateTime(timezone=True)` (aware).
- **Codice**: usa `datetime.now(UTC).isoformat()` (stringa UTC) o `datetime.now(UTC)` (aware datetime).

### Campi di temporalità
| Campo | Tabelle | Note |
|-------|---------|------|
| `created_at` | quasi tutte | Sempre popolato con `datetime.now(UTC).isoformat()` |
| `updated_at` | alcune | Non sempre popolato negli UPDATE |
| `recorded_at` | `athlete_metric_log`, `hr_24h_samples`, `food_logs` | Event-time, non server-time |
| `computed_at` | `fitness_states`, `route_safety_scores`, `daily_activity_classification` | Quando è stato calcolato il valore |
| `last_modified` | `sync_entity_state` | Sync-specific |
| `local_modified` / `remote_modified` | `sync_conflicts` | Sync-specific |
| `expires_at` | `strava_tokens`, `garmin_tokens`, `wahoo_tokens`, `sessions` | INTEGER (epoch) per token, DateTime per sessions |
| `cached_at` | `weather_cache` | Cache freshness |
| `incident_date` | `road_incidents` | DATA evento, non created_at |
| `date` | `rides`, `training_stress_days`, `food_logs`, `fitness_states`, `metabolic_daily_summaries`, `daily_activity_classification` | **DATE** (no time), ma alcune sono `TEXT` con formato data |

### Problemi
- **Timezone naive vs aware**: SQLite salva stringhe ISO con suffisso `Z` (UTC aware come stringa). SQLAlchemy usa `DateTime(timezone=True)`. Non c’è conversione esplicita tra i due mondi — se un modulo PostgreSQL legge un `created_at` da SQLAlchemy (aware) e lo confronta con una stringa ISO da SQLite, il confronto funziona per coincidenza ma non per design.
- **Campi mancanti**: alcune tabelle SQLite non hanno `updated_at` (es. `rides` lo ha solo dopo ALTER TABLE; `metrics` non lo ha nel DDL iniziale). I modelli SQLAlchemy lo hanno.
- **`date` vs `datetime`**: campi `date` (es. `rides.date`) sono stringhe `YYYY-MM-DD` senza timezone. Campi `recorded_at` sono ISO datetime. Non c’è un helper centralizzato per conversioni.
- **`expires_at`**: nei token è INTEGER epoch; in `sessions` è DateTime aware. Inconsistente.

---

## 8. Dipendenze circolari reali

### Nessuna circolare a runtime (grazie a lazy imports)
Tutte le importazioni da `database.py` nei repository sono **lazy** (dentro le funzioni), quindi Python non rileva errori a import-time. Tuttavia esistono **circolari a compile-time / design-time**:

| Ciclo | Moduli coinvolti | Gravità |
|-------|------------------|----------|
| `database.py` → `repositories/athlete_repository.py` → `..database` | `db/database.py` ↔ `db/repositories/athlete_repository.py` | Medio (lazy import evita il crash) |
| `database.py` → `repositories/ride_repository.py` → `...models.models` → `bike_analyzer.core.models` | `db/database.py` ↔ `db/repositories/ride_repository.py` | Basso (solo dataclass) |
| `postgres_rides.py` → `postgres_athlete.py` → `_connect` | `db/postgres_rides.py` ↔ `db/postgres_athlete.py` | Basso (solo connection factory) |
| `postgres_itineraries.py` → `postgres_athlete.py` → `_connect` | `db/postgres_itineraries.py` ↔ `db/postgres_athlete.py` | Basso |
| `analytics/repositories/athlete_repository.py` → `..db.database` → `repositories/athlete_repository.py` | `analytics/repositories/athlete_repository.py` ↔ `db/database.py` | Medio (stesso modulo, lazy) |
| `analytics/repositories/ride_repository.py` → `..db.database` → `repositories/ride_repository.py` | `analytics/repositories/ride_repository.py` ↔ `db/database.py` | Medio |
| `analytics/repositories/user_repository.py` → `...db.models` (per `_table`) + sync diretto senza `database.py` | `analytics/repositories/user_repository.py` ↔ `db/models.py` | Basso |

### Conclusioni sulle circolari
Non ci sono dipendenze circolari **vere** che causano crash a runtime. Tutte sono mitigate da:
- Lazy imports dentro funzioni
- Import condizionali (`if SQLALCHEMY_AVAILABLE`)
- Import di modelli (no side effects)

Però il grafico delle dipendenze è **completamente piatto**: ogni repository, router e modulo business importa direttamente da `database.py` senza passare per un layer di astrazione. Questo rende impossibile sostituire `database.py` senza rompere decine di import.

---

## Riepilogo raccomandazioni

1. **Estrarre `database.py` in moduli per dominio** seguendo il piano allo point 6, iniziando dalle funzioni meno dipendenti.
2. **Unificare i modelli**: creare un singolo source of truth per lo schema (preferibilmente `db/models.py` SQLAlchemy) e generare il DDL SQLite da quello, invece di mantenere due versioni manuali.
3. **Rimuovere duplicazioni**: `analytics/repositories/*` e `db/repositories/*` dovrebbero convergere in un unico set di repository. I repository analytics sono già più vicini a un design pulito (dual-mode sync/async).
4. **Centralizzare la temporalità**: creare un helper `db/temporal.py` con `now_iso()`, `now_aware()`, `parse_iso()` per evitare misture di stringhe ISO e datetime aware.
5. **Completare la migrazione PostgreSQL**: i domini SQLite-only elencati nel punto 2 dovrebbero essere migrati o almeno avere un `@pg_dispatch` stub per documentare l’assenza.
