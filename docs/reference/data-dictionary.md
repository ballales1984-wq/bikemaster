# Dizionario Dati — Modello Dati & Regole Decisionali

Riferimento unificato del modello dati di BikeMaster: entità di dominio, tabelle di persistenza, vincoli, indici e regole decisionali/business logic.

## Fonti

| Layer | Percorso |
| --- | --- |
| Dominio core (dataclass pure) | `bike_analyzer/core/models.py`, `bike_analyzer/core/fitness_state.py` |
| Persistenza sync (SQLite) | `bike_analyzer/backend/db/database.py` |
| ORM async (SQLAlchemy 2.0) | `bike_analyzer/backend/db/models.py` |
| ORM PostgreSQL leggero | `bike_analyzer/backend/db/postgres_db.py` |
| DTO API (Pydantic) | `bike_analyzer/backend/api/schemas.py` |
| Modelli BM2 | `bike_analyzer/bm2/models.py`, `bm2/units.py`, `bm2/transformer.py` |
| TypeScript (frontend) | `frontend/src/types/index.d.ts`, `frontend/src/types/bm2.ts` |
| Regole decisionali | `bike_analyzer/core/calculators/`, `bike_analyzer/backend/analytics/`, `bike_analyzer/bm2/algorithms/` |

> **Nota di integrità:** Il layer sync (SQLite, `db/database.py`) è il *primary store* locale e di proprietà di `init_db()`. L'ORM `db/models.py` e la lineage Alembic (PostgreSQL, `RUN_MIGRATIONS_ON_STARTUP`) ne rispecchiano lo schema ma NON sono perfettamente allineati su ogni colonna (es. `metrics`, `strava_tokens`/`garmin_tokens` non esistono nello schema sync corrente). Le differenze sono segnalate nelle singole sezioni. Vedere `database-schema.md` per il dettaglio della lineage.

---

## 1. Entità di Dominio Core

Tutte le entità in `bike_analyzer/core/models.py` sono `@dataclass` pure, indipendenti da DB/API. Costante globale: `EARTH_RADIUS_M = 6_371_000`.

### GPSPoint (`frozen`)
Singolo campione della traccia GPS.

| Campo | Tipo | Significato |
| --- | --- | --- |
| `lat` | `float` | Latitudine (gradi, WGS84) |
| `lon` | `float` | Longitudine (gradi, WGS84) |
| `timestamp` | `datetime` | Istante del campione (normalizzato a UTC naive in `__post_init__`) |
| `altitude` | `float \| None` | Quota (m) |
| `speed` | `float \| None` | Velocità (km/h) |
| `power` | `float \| None` | Potenza (W) |
| `heart_rate` | `float \| None` | Frequenza cardiaca (bpm) |
| `cadence` | `float \| None` | Cadenza (rpm) |

- Metodo: `distance_to(other) → float` (distanza haversine in metri).
- Helper modulo: `haversine_distance_m(lat1, lon1, lat2, lon2) → float`.

### Segment
Sotto-sezione di una ride tra due punti di controllo.

| Campo | Tipo | Default |
| --- | --- | --- |
| `start` | `GPSPoint` | — |
| `end` | `GPSPoint` | — |
| `distance_m` | `float` | `0.0` |
| `duration_s` | `float` | `0.0` |
| `avg_speed_km_h` | `float` | `0.0` |
| `elevation_gain_m` | `float` | `0.0` |
| `elevation_loss_m` | `float` | `0.0` |

### Pause
Intervallo di sosta rilevato.

| Campo | Tipo | Default |
| --- | --- | --- |
| `start` | `datetime` | — |
| `end` | `datetime` | — |
| `duration_s` | `float` | `0.0` |

### RouteStatistics
Statistiche aggregate del percorso.

| Campo | Tipo | Default |
| --- | --- | --- |
| `total_distance_m` | `float` | `0.0` |
| `total_duration_s` | `float` | `0.0` |
| `total_pause_duration_s` | `float` | `0.0` |
| `avg_speed_km_h` | `float` | `0.0` |
| `max_speed_km_h` | `float` | `0.0` |
| `total_elevation_gain_m` | `float` | `0.0` |
| `total_elevation_loss_m` | `float` | `0.0` |
| `segment_count` | `int` | `0` |
| `pause_count` | `int` | `0` |

### Ride
Entità ride completa. Metodi: `to_dict()`, proprietà `duration_hours` (`duration_minutes / 60`).

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `id` | `int \| None` | `None` | PK |
| `athlete_id` | `int \| None` | `None` | Atleta proprietario |
| `tenant_id` | `int` | `0` | Isolamento tenant (multi-tenant) |
| `date` | `str` | `""` | Data (ISO: `YYYY-MM-DD`) |
| `distance_km` | `float` | `0.0` | Distanza (km) |
| `duration_minutes` | `float` | `0.0` | Durata (min) |
| `avg_speed_kmh` | `float` | `0.0` | Velocità media (km/h) |
| `weight_kg` | `float` | `70.0` | Peso usato (kg) |
| `calories` | `float` | `0.0` | Calorie stimate |
| `heart_rate_avg` | `float \| None` | `None` | FC media (bpm) |
| `elevation_gain_m` | `float \| None` | `None` | Dislivello positivo (m) |
| `external_source` | `str \| None` | `None` | Origine esterna (strava, garmin, ...) |
| `external_id` | `str \| None` | `None` | ID attività esterna (v. UNIQUE) |
| `title` | `str \| None` | `None` | Titolo |
| `gps_points` | `list[GPSPoint] \| None` | `None` | Traccia GPS |
| `created_at` | `str \| None` | `None` | Timestamp creazione |
| `activity_type` | `str` | `"ride"` | `ride\|walk\|hike\|run\|indoor\|other` |
| `is_official` | `bool` | `True` | Ufficiale vs stimata |
| `source` | `str` | `"manual"` | `manual\|strava\|garmin\|wahoo\|gpx\|fit\|google_fit` |

### AthleteProfile
Profilo atleta per i calcoli personalizzati. Metodo: `to_dict()`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `id` | `int \| None` | `None` | PK |
| `name` | `str` | `""` | Nome completo |
| `age` | `int` | `30` | Età (anni) |
| `weight_kg` | `float` | `70.0` | Peso corporeo (kg) |
| `height_cm` | `float \| None` | `None` | Altezza (cm) |
| `fat_percentage` | `float \| None` | `None` | Massa grassa (%) |
| `years_active` | `int` | `1` | Anni di attività ciclistica |
| `weekly_sessions` | `int` | `3` | Sessioni/settimana |
| `monthly_hours` | `float` | `0.0` | Ore/mese |
| `annual_hours` | `float` | `0.0` | Ore/anno |
| `experience_level` | `str` | `"Beginner"` | `Beginner\|Amateur\|Intermediate\|Advanced\|Elite` |
| `goals` | `str \| None` | `None` | Obiettivi testuali |
| `preferred_terrain` | `str \| None` | `None` | Terreno preferito |
| `weekly_volume_km` | `float` | `0.0` | Volume settimanale (km) |
| `best_segments` | `str \| None` | `None` | Segmenti migliori |
| `medical_notes` | `str \| None` | `None` | Note mediche |
| `equipment` | `str \| None` | `None` | Dotazione |
| `ftp_watts` | `float \| None` | `None` | FTP (W) |
| `created_at` | `str \| None` | `None` | Data creazione |

### CalendarEvent
Evento/pianificazione allenamento. Metodo: `to_dict()`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `id` | `int \| None` | `None` | PK |
| `athlete_id` | `int \| None` | `None` | FK→athletes |
| `title` | `str` | `""` | Titolo evento |
| `event_type` | `str` | `"training"` | `training\|race\|rest\|event` |
| `date` | `str` | `""` | Data (ISO) |
| `duration_minutes` | `int` | `0` | Durata (min) |
| `description` | `str \| None` | `None` | Descrizione |
| `completed` | `bool` | `False` | Completato |
| `created_at` | `str \| None` | `None` | Timestamp creazione |

### TrainingStressDay (`core/fitness_state.py`)
Serie giornaliera del carico di allenamento.

| Campo | Tipo | Default |
| --- | --- | --- |
| `date` | `date` | — |
| `tss` | `float` | `0.0` |
| `atl` | `float` | `0.0` |
| `ctl` | `float` | `0.0` |
| `tsb` | `float` | `0.0` |

### FitnessStateVector (`core/fitness_state.py`)
Snapshot fisiologico. Metodo: `to_dict()` (arrotonda a 1 decimale e aggiunge le proprietà calcolate). Proprietà calcolate: `is_overtraining_risk`, `is_fresh`, `is_ready_for_hard_effort`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `athlete_id` | `int` | — | FK→athletes |
| `computed_at` | `datetime` | — | Timestamp calcolo |
| `atl` | `float` | `0.0` | Acute Training Load (7g) |
| `ctl` | `float` | `0.0` | Chronic Training Load (42g) |
| `tsb` | `float` | `0.0` | Training Stress Balance (ctl−atl) |
| `fitness` | `float` | `0.0` | Indice fitness complessivo |
| `fatigue` | `float` | `0.0` | Indice affaticamento |
| `form` | `float` | `0.0` | Indice forma |
| `recovery_hours_needed` | `float` | `0.0` | Ore di recupero stimate |
| `weekly_tss` | `float` | `0.0` | TSS settimanale |
| `monthly_tss` | `float` | `0.0` | TSS mensile |
| `trend_7d` | `str` | `"stable"` | Trend 7gg: `rising\|falling\|stable` |
| `trend_30d` | `str` | `"stable"` | Trend 30gg |
| `risk_indicators` | `list[str]` | `[]` | Indicatori di rischio |
| `recommendation` | `str` | `""` | Raccomandazione testuale |

Proprietà calcolate (verificate in `core/fitness_state.py:36-46`):

| Proprietà | Condizione |
| --- | --- |
| `is_fresh` | `tsb > 15` |
| `is_ready_for_hard_effort` | `tsb > 5 and atl < ctl * 1.1` |
| `is_overtraining_risk` | `atl > ctl * 1.3 and tsb < -20` |

---

## 2. Tabelle di Persistenza

Lo schema SQLite è creato da `init_db()` in `bike_analyzer/backend/db/database.py`. La colonna `tenant_id` (default `0`) è presente su quasi tutte le tabelle per l'isolamento multi-tenant. Gli indici sono creati/garantiti da `_ensure_external_identity_index` e da `CREATE INDEX IF NOT EXISTS`.

### `users` — account applicativi / autenticazione

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK, AUTOINCREMENT |
| `username` | `TEXT` | UNIQUE, NOT NULL |
| `email` | `TEXT` | UNIQUE, nullable |
| `password_hash` | `TEXT` | bcrypt (nullable) |
| `is_admin` | `INTEGER` | DEFAULT 0 |
| `is_active` | `INTEGER` | DEFAULT 1 |
| `created_at` | `TEXT` | |
| `updated_at` | `TEXT` | |

### `athletes` — profilo atleta

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `name` | `TEXT` | NOT NULL |
| `email` | `TEXT` | (aggiunta migrazione runtime) |
| `picture` | `TEXT` | URL avatar (runtime) |
| `age` | `INTEGER` | DEFAULT 30 |
| `weight_kg` | `REAL` | DEFAULT 70 |
| `height_cm` | `REAL` | |
| `fat_percentage` | `REAL` | |
| `years_active` | `INTEGER` | DEFAULT 1 |
| `weekly_sessions` | `INTEGER` | DEFAULT 3 |
| `monthly_hours` | `REAL` | |
| `annual_hours` | `REAL` | |
| `experience_level` | `TEXT` | DEFAULT `Beginner` |
| `goals` | `TEXT` | (runtime) |
| `preferred_terrain` | `TEXT` | |
| `weekly_volume_km` | `REAL` | DEFAULT 0 |
| `best_segments` | `TEXT` | |
| `medical_notes` | `TEXT` | |
| `equipment` | `TEXT` | |
| `ftp_watts` | `REAL` | FTP (W) — runtime |
| `password_hash` | `TEXT` | (runtime) |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `created_at` | `TEXT` | |

> Le colonne `email`, `picture`, `goals`, `ftp_watts`, `password_hash`, `tenant_id` sono aggiunte in modo idempotente con `ALTER TABLE` in `init_db()` se assenti. Nell'ORM `db/models.py` non esiste l'indice `ix_athletes_user` (menzionato in alcuni documenti legacy): è assente.

### `rides` — sessione ciclistica completa

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | proprietario |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `date` | `TEXT` | NOT NULL (ISO `YYYY-MM-DD`) |
| `distance_km` | `REAL` | |
| `duration_minutes` | `REAL` | |
| `avg_speed_kmh` | `REAL` | |
| `weight_kg` | `REAL` | DEFAULT 70 |
| `calories` | `REAL` | DEFAULT 0 |
| `heart_rate_avg` | `REAL` | |
| `elevation_gain_m` | `REAL` | |
| `gps_points` | `TEXT` | array GPS serializzato JSON |
| `external_source` | `TEXT` | es. strava, garmin (runtime) |
| `external_id` | `TEXT` | id attività esterna (runtime) |
| `title` | `TEXT` | (runtime) |
| `activity_type` | `TEXT` | DEFAULT `ride` (runtime) |
| `is_official` | `INTEGER` | DEFAULT 1 (runtime) |
| `source` | `TEXT` | DEFAULT `manual` (runtime) |
| `created_at` | `TEXT` | |

**Vincoli/indici:** `UNIQUE(external_source, external_id)` creato come `uq_rides_external_identity` (PRIMA droppato `ix_rides_external_source` se non ci sono duplici). `save_ride` salta l'insert se esiste già `(external_source, external_id)`.

### `fitness_states` — snapshot fisiologico

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | FK→athletes(id) |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `date` | `TEXT` | NOT NULL |
| `computed_at` | `TEXT` | |
| `fitness` | `REAL` | DEFAULT 0 |
| `fatigue` | `REAL` | DEFAULT 0 |
| `form` | `REAL` | DEFAULT 0 |
| `atl` | `REAL` | DEFAULT 0 |
| `ctl` | `REAL` | DEFAULT 0 |
| `tsb` | `REAL` | DEFAULT 0 |
| `recovery_hours_needed` | `REAL` | DEFAULT 0 |
| `weekly_tss` | `REAL` | DEFAULT 0 |
| `monthly_tss` | `REAL` | DEFAULT 0 |
| `trend_7d` | `TEXT` | DEFAULT `stable` |
| `trend_30d` | `TEXT` | DEFAULT `stable` |
| `risk_indicators` | `TEXT` | JSON list |
| `recommendation` | `TEXT` | |

Indice: `idx_fitness_states_athlete(athlete_id)`. Nell'ORM `db/models.py` non esiste `ix_fitness_states_ctl` (menzionato in doc legacy): assente.

### `chat_history` — conversazioni AI Coach

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | FK→athletes(id), `INDEX` |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `role` | `TEXT` | NOT NULL (`user`/`assistant`) |
| `content` | `TEXT` | NOT NULL |
| `created_at` | `TEXT` | |

Retention configurabile (`AI_COACH_CHAT_RETENTION_DAYS`, default 90); pruning via `prune_chat_history`.

### `calendar_events` — eventi/pianificazione

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | FK→athletes(id) |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `title` | `TEXT` | NOT NULL |
| `event_type` | `TEXT` | DEFAULT `training` |
| `date` | `TEXT` | NOT NULL |
| `duration_minutes` | `INTEGER` | DEFAULT 0 |
| `description` | `TEXT` | |
| `completed` | `INTEGER` | DEFAULT 0 |
| `weather_temp` | `REAL` | cache meteo (runtime) |
| `weather_humidity` | `REAL` | (runtime) |
| `weather_description` | `TEXT` | (runtime) |
| `created_at` | `TEXT` | |

### `weather_cache` — cache previsioni meteo

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `lat` | `REAL` | NOT NULL |
| `lon` | `REAL` | NOT NULL |
| `date` | `TEXT` | NOT NULL |
| `temperature` | `REAL` | |
| `humidity` | `REAL` | |
| `description` | `TEXT` | |
| `cached_at` | `TEXT` | |

**Vincolo:** `UNIQUE(lat, lon, date)`.

### `training_stress_days` — serie giornaliera del carico

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | NOT NULL, FK→athletes(id) |
| `date` | `TEXT` | NOT NULL |
| `tss` | `REAL` | Training Stress Score |
| `atl` | `REAL` | |
| `ctl` | `REAL` | |
| `tsb` | `REAL` | |
| `created_at` | `TEXT` | |
| `updated_at` | `TEXT` | |

**Vincolo:** `UNIQUE(athlete_id, date)` (upsert). `tenant_id` colonna gestita da runtime (`ALTER TABLE` se assente).

### `metrics` — metriche derivate per ride/atleta

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | FK→athletes(id) (runtime) |
| `ride_id` | `INTEGER` | FK→rides(id) |
| `fatigue_score` | `REAL` | (runtime) |
| `recovery_hours` | `REAL` | (runtime) |
| `calories_per_km` | `REAL` | (runtime) |
| `efficiency_score` | `REAL` | (runtime) |
| `created_at` | `TEXT` | (runtime) |
| `tenant_id` | `INTEGER` | DEFAULT 0 (runtime) |

Indice: `idx_metrics_ride(ride_id)`.

> **Differenza di lineage:** la migration Alembic remodella `metrics` in stile chiave/valore (`metric_type`, `value`, `unit`, `recorded_at`). Lo schema effettivo dipende dal backend attivo (SQLite sync vs PostgreSQL/Alembic). In locale (sync) la forma a colonne fisse è quella gestita da `init_db()`.

### `training_goals` — obiettivi (es. granfondo)

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | NOT NULL, FK→athletes(id) |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `title` | `TEXT` | NOT NULL |
| `description` | `TEXT` | |
| `goal_type` | `TEXT` | DEFAULT `granfondo` |
| `target_date` | `TEXT` | |
| `target_distance_km` | `REAL` | |
| `target_elevation_m` | `REAL` | |
| `status` | `TEXT` | DEFAULT `active` |
| `created_at` | `TEXT` | |

### `planned_workouts` — workout pianificati (collegati a obiettivo)

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | NOT NULL, FK→athletes(id) |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `goal_id` | `INTEGER` | FK→training_goals(id) |
| `date` | `TEXT` | NOT NULL |
| `title` | `TEXT` | NOT NULL |
| `workout_type` | `TEXT` | DEFAULT `endurance` |
| `duration_minutes` | `INTEGER` | DEFAULT 60 |
| `target_intensity` | `REAL` | DEFAULT 0.5 |
| `completed` | `INTEGER` | DEFAULT 0 |
| `completed_at` | `TEXT` | |

### `road_incidents` — incidenti stradali (analisi sicurezza)

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `source_id` | `TEXT` | NOT NULL |
| `lat` | `REAL` | NOT NULL |
| `lon` | `REAL` | NOT NULL |
| `incident_date` | `TEXT` | NOT NULL |
| `severity` | `TEXT` | DEFAULT `medium` |
| `description` | `TEXT` | |
| `road_type` | `TEXT` | |
| `source` | `TEXT` | DEFAULT `local` |
| `created_at` | `TEXT` | |

**Vincolo:** `UNIQUE(source_id, source)` (INSERT OR IGNORE).

### `route_safety_scores` — punteggio sicurezza per ride

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `ride_id` | `INTEGER` | FK→rides(id) |
| `athlete_id` | `INTEGER` | FK→athletes(id) |
| `risk_score` | `REAL` | 0..1 |
| `label` | `TEXT` | etichetta rischio |
| `advice` | `TEXT` | |
| `road_type_counts` | `TEXT` | JSON |
| `has_bike_infrastructure` | `INTEGER` | |
| `incident_count` | `INTEGER` | |
| `route_length_km` | `REAL` | |
| `computed_at` | `TEXT` | |
| `tenant_id` | `INTEGER` | DEFAULT 0 |

### `pois` — Point of Interest

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `name` | `TEXT` | NOT NULL |
| `description` | `TEXT` | NOT NULL |
| `lat` | `REAL` | NOT NULL |
| `lon` | `REAL` | NOT NULL |
| `type` | `TEXT` | NOT NULL (vista, fontana, ristoro, bivio, pericolo, culturale, tecnico) |
| `photos` | `TEXT` | JSON |
| `video_url` | `TEXT` | |
| `difficulty_note` | `TEXT` | |
| `tags` | `TEXT` | JSON |
| `itinerary_id` | `INTEGER` | |
| `created_by` | `INTEGER` | |
| `tenant_id` | `INTEGER` | DEFAULT 0 |
| `created_at` | `TEXT` | |

Indice: `idx_pois_coords(lat, lon)`.

### `knowledge_chunks` — chunk RAG (vector DB)

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `topic` | `String` | DEFAULT `""` |
| `chunk_id` | `String` | DEFAULT `""` |
| `text` | `Text` | contenuto chunk |
| `word_count` | `Integer` | |
| `char_count` | `Integer` | |
| `token_count` | `Integer` | |
| `section` | `String` | |
| `embedding` | `Vector(384)` / `Text` | pgvector se disponibile, altrimenti `Text` |

`EMBEDDING_DIMENSION = 384` (all-MiniLM-L6-v2). Su PostgreSQL: `CREATE EXTENSION vector;`. Indice `ix_knowledge_chunks_topic` (ORM).

### `strava_tokens` / `garmin_tokens` — token OAuth provider esterni

> Queste tabelle **non** compaiono nello schema `init_db()` corrente (SQLite sync). Esistono come concetto nel layer ingestion/OAuth. Struttura attesa:

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER` | PK |
| `athlete_id` | `INTEGER` | FK→athletes(id) ON DELETE CASCADE, UNIQUE per atleta |
| `access_token` | `TEXT` | |
| `refresh_token` | `TEXT` | auto-refresh |
| `expires_at` | `*` | scadenza token |
| `tenant_id` | `INTEGER` | DEFAULT 0 |

### Tabelle di sync (aggiuntive, `db/database.py`)

| Tabella | Scopo |
| --- | --- |
| `sync_entity_state` | stato di sync per entità (`UNIQUE(entity_type, entity_id)`, indice `idx_sync_entity_state_type`) |
| `sync_settings` | impostazioni di sync chiave/valore (`key` PK) |
| `sync_conflicts` | conflitti di sync (`resolution` DEFAULT `unresolved`, indice `idx_sync_conflicts_resolution`) |

---

## 3. Modelli BikeMaster 2.0 (BM2)

Motore knowledge/model-driven. Ogni grandezza è normalizzata verso le **unità canoniche interne** prima di essere passata agli algoritmi.

### Quantity (`bm2/units.py`, `frozen`)
Misura fondamentale: **valore + unità + precisione + fonte**. Costruttore helper: `q(value, unit, precision=0.0, source="unknown", timestamp=None)`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `value` | `float` | — | Valore numerico |
| `unit` | `str` | — | Simbolo unità (es. `kg`, `m/s`, `%`) |
| `precision` | `float` | `0.0` | Incertezza assoluta (stessa unità) |
| `source` | `str` | `"unknown"` | `garmin\|strava\|manual\|gps\|dem\|estimate\|power_meter\|hr_sensor\|...` |
| `timestamp` | `datetime \| None` | `None` | Istante di misura |

`UnitRegistry` (`default_registry`): conversioni lineari per massa/lunghezza/velocità/tempo/energia/potenza/frequenza/pressione/densità/coppia, più dimensioni non lineari (`slope`, `angle`, `temperature`).

**Unità canoniche interne:** massa→`kg`, lunghezza→`m`, velocità→`m/s`, tempo→`s`, energia→`J`, potenza→`W`, pendenza→`%`, angolo→`deg`, frequenza→`bpm`, temperatura→`°C`.

Precisione di default stimata per `(source, unit)` in `DEFAULT_QUALITY` (es. `gps/m`=±5, `gps/dem/m`=±10, `power_meter/W`=±2, `estimate/W`=±15).

### GeoPoint (`bm2/transformer.py`, `frozen`)
Punto geografico con proiezione metrica locale (equirettangolare).

| Campo | Tipo | Default |
| --- | --- | --- |
| `lat` | `float` | — |
| `lon` | `float` | — |
| `altitude` | `float` | `0.0` |
| `timestamp` | `datetime \| None` | `None` |
| `x` | `float` | `0.0` (X metrico locale) |
| `y` | `float` | `0.0` (Y metrico locale) |
| `speed` | `float \| None` | `None` |
| `power` | `float \| None` | `None` |
| `heart_rate` | `float \| None` | `None` |
| `cadence` | `float \| None` | `None` |

### Athlete (`bm2/models.py`)
Metodi: `from_raw`, `to_dict`, `from_dict`, `power_to_weight()`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `weight_kg` | `Quantity` | — | Peso (obbligatorio) |
| `age` | `int` | `30` | Età |
| `height_m` | `Quantity \| None` | `None` | Altezza |
| `ftp_w` | `Quantity \| None` | `None` | FTP (W) |
| `max_hr_bpm` | `Quantity \| None` | `None` | FC max (bpm) |
| `resting_hr_bpm` | `Quantity \| None` | `None` | FC a riposo |
| `experience_level` | `str` | `"Beginner"` | `Beginner\|Intermediate\|Advanced\|Elite` |
| `weekly_hours` | `Quantity \| None` | `None` | Ore/settimana |
| `name` | `str` | `""` | Nome |
| `ctl_stress_score` | `Quantity \| None` | `None` | CTL |
| `atl_stress_score` | `Quantity \| None` | `None` | ATL |
| `tsb_stress_score` | `Quantity \| None` | `None` | TSB |

### Bike (`bm2/models.py`)
Metodo: `from_raw`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `weight_kg` | `Quantity` | — | Peso bici (obbligatorio) |
| `crr` | `float` | `0.005` | Coeff. resistenza rotolamento |
| `cda` | `float` | `0.40` | Area frontale × Cd |
| `drivetrain_efficiency` | `float` | `0.97` | Efficienza trasmissione |
| `name` | `str` | `""` | Nome |
| `category` | `str` | `"road"` | `road\|gravel\|mtb\|other` |
| `gear_ratio` | `float \| None` | `None` | Rapporto |

### Activity (`bm2/models.py`)
Metodi: `from_raw`, `to_dict`, `from_dict`, `metrics(t)`.

| Campo | Tipo | Default |
| --- | --- | --- |
| `points` | `list[GeoPoint]` | `[]` |
| `title` | `str` | `""` |
| `sport` | `str` | `"cycling"` |
| `laps` | `list[dict]` | `[]` |
| `segments` | `list[dict]` | `[]` |
| `summary` | `dict` | `{}` |

`metrics(t)` restituisce: `distance_m`, `duration_s`, `gain_m`, `loss_m`, `avg_slope_percent`, `avg_speed_ms`.

### WorldObject (`bm2/models.py`)
Metodo: `from_raw`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `surface` | `str` | `"asphalt"` | `asphalt\|gravel\|dirt\|trail` |
| `roughness_index` | `Quantity` | `q(0.0, "")` | Indice di rugosità (adimensionale) |
| `avg_slope_percent` | `Quantity \| None` | `None` | Pendenza media (%) |
| `wind_speed_ms` | `Quantity \| None` | `None` | Velocità vento (m/s) |
| `temperature_c` | `Quantity \| None` | `None` | Temperatura (°C) |

### AnalysisContext (`bm2/models.py`)
Contesto di analisi che raggruppa gli oggetti. Proprietà: `total_mass_kg = athlete.weight_kg.value + bike.weight_kg.value`.

| Campo | Tipo |
| --- | --- |
| `athlete` | `Athlete` |
| `activity` | `Activity` |
| `bike` | `Bike` |
| `world` | `WorldObject` |
| `transformer` | `TransformerEngine` |

### ModelResult (`bm2/algorithms/base.py`)
Contratto universale di output di ogni algoritmo BM2. Metodi: `to_dict`, `from_dict`, `uncertainty_bounds()` `(value-precision, value+precision)`, `compare_with(other)`.

| Campo | Tipo | Significato |
| --- | --- | --- |
| `value` | `float` | Risultato nell'unità |
| `unit` | `str` | Unità risultato |
| `formula` | `str` | Formula/metodo applicato |
| `data_used` | `list[str]` | Input consumati |
| `precision` | `float` | Incertezza assoluta |
| `confidence` | `float` | Affidabilità 0..1 |
| `source` | `str` | Algoritmo produttore |
| `details` | `dict` | Output secondari |

La classe base `Algorithm` (ABC) definisce `run(ctx, extra) -> ModelResult`, una mappa `SOURCE_CONFIDENCE` (vedi sotto) e i controlli `_has_input`. Costanti fisiche: `G = 9.81`, `RHO = 1.225`.

`SOURCE_CONFIDENCE` (base affidabilità per fonte):

| Fonte | confidence |
| --- | --- |
| `power_meter` | 0.95 |
| `scale` | 0.90 |
| `hr_sensor` | 0.85 |
| `gps` / `gps/dem` | 0.85 / 0.75 |
| `baro` | 0.80 |
| `hr_band` | 0.80 |
| `manual` | 0.80 |
| `dem` | 0.70 |
| `estimate` | 0.50 |

### Insight (`bm2/knowledge.py`)
Output interpretato del Knowledge Layer. Metodo: `to_dict`.

| Campo | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `concept` | `str` | — | Concetto |
| `detail` | `str` | — | Spiegazione |
| `severity` | `str` | `"info"` | `info\|note\|warning\|critical` |

---

## 4. Modelli TypeScript (Frontend)

### `Ride` (`frontend/src/types/index.d.ts`)

```ts
interface Ride {
  id: number;
  athlete_id: number;
  tenant_id: number;
  date: string;              // ISO YYYY-MM-DD
  distance_km: number;
  duration_minutes: number;
  avg_speed_kmh: number;
  weight_kg: number;
  calories: number;
  heart_rate_avg: number | null;
  elevation_gain_m: number | null;
  gps_points: GpsPoint[] | null;
  external_source: string | null;
  external_id: string | null;
  title: string | null;
  activity_type: string;
  is_official: boolean;
  source: string;
  created_at: string | null;
}
```

### `Athlete` (`frontend/src/types/index.d.ts`)

```ts
interface Athlete {
  id: number;
  name: string;
  age: number;
  weight_kg: number;
  height_cm: number | null;
  fat_percentage: number | null;
  years_active: number;
  weekly_sessions: number;
  monthly_hours: number;
  annual_hours: number;
  experience_level: string;
  goals: string | null;
  preferred_terrain: string | null;
  weekly_volume_km: number | null;
  best_segments: string | null;
  medical_notes: string | null;
  equipment: string | null;
  ftp_watts: number | null;
  tenant_id: number;
}
```

### `GpsPoint` (`frontend/src/types/index.d.ts`)

```ts
interface GpsPoint {
  lat: number;
  lon: number;
  timestamp: string;
  altitude?: number;
  speed?: number;
  power?: number;
  heart_rate?: number;
  cadence?: number;
}
```

### Tipi BM2 (`frontend/src/types/bm2.ts`)
`Bm2Quantity`, `Bm2ModelResult`, `Bm2Insight`, `Bm2Answer`, `Bm2AskPayload`, `Bm2SimulateRidePayload`, `Bm2SimulateRideResult`, `Bm2ValidatePayload`, `Bm2Validation`, `Bm2ValidateResult`, `Bm2Comparison`, `Bm2SimulationDelta`. Riflettono 1:1 i modelli Python `ModelResult`/`Insight`/`AnalysisContext`.

---

## 5. Regole Decisionali

Tutte le formule sono trascrizioni fedeli dal codice sorgente (file indicati). Dove il codice usava soglie arrotondate, esse sono riportate esattamente.

### 5.1 Fatigue Score & Recupero

**File:** `bike_analyzer/core/calculators/fatigue.py`, `bike_analyzer/bm2/algorithms/fatigue.py`

Formula core (`calculate_fatigue_score`, `rider_age` default 35):

```
DURATION_FACTOR   = min(duration_h / 2.0, 3.0)
INTENSITY_FACTOR  = da HR% (220 - age) se HR nota, altrimenti 1.0
SPEED_FACTOR      = min(avg_speed_kmh / 25.0, 2.0)
ELEV_FACTOR       = 1.0 + min((elev_gain_km / dist_km) / 20.0, 1.0)   # elev_gain_km = gain_m/1000
WEIGHT_FACTOR     = weight_kg / 70.0
score = min((DURATION*0.3 + INTENSITY*0.3 + SPEED*0.2 + ELEV*0.1 + WEIGHT*0.1) * 3.0, 10.0)
```

Soglie fatigue → ore di recupero (`estimate_recovery_hours`):

| Range Fatigue | Ore Recupero | Raccomandazione (`get_recovery_recommendation`) |
| --- | --- | --- |
| ≤ 3.0 | 8 h | Minimal fatigue |
| ≤ 5.0 | 16 h | Light fatigue |
| ≤ 7.0 | 24 h | Moderate fatigue — rest day recommended |
| > 7.0 | 48 h | High/Extreme fatigue — rest required / multiple rest days |

BM2 `FatigueModel` (`_recovery_hours`) usa le stesse soglie (≤3→8, ≤5→16, ≤7→24, else→48). Confidence BM2:

- Base: `0.75` se `duration_s > 0`, altrimenti `0.30`
- Se `max_hr_bpm` noto: `+0.05` (capped `0.85`)

**Recovery Score** (core `performance.py`): `recovery_score = round(10 - fatigue, 1)`.

### 5.2 Performance Score

**File:** `bike_analyzer/core/calculators/performance.py`

```
speed_factor      = min(avg_speed_kmh / 30.0, 1.0)
duration_factor   = min(duration_h / 2.0, 1.0)
elevation_factor  = min(elevation_gain_m / 500.0, 1.0)   # se elev_gain_m None -> 0
score = round((speed*0.4 + duration*0.4 + elevation*0.2) * 10.0, 1)
```

Funzioni correlate (`performance.py`):

- `endurance_score(rides)`: `long_ride_ratio*0.4 + consistency*0.3 + distance_factor*0.3` (×10), con `long_ride` = durata ≥ 2h.
- `efficiency_score(ride)`: `clamp(10 - (calories_per_km - 30)/5, 0, 10)`.
- `recovery_score(ride)`: `10 - fatigue`.
- `monthly_scores(rides)`: media di performance/endurance/recovery/efficiency + `avg_fatigue`.

**BM2 `PerformanceModel`** (normalizzato sull'esperienza, `REFERENCE_SPEED_KMH`: Beginner 18, Intermediate 24, Advanced 30, Elite 36):

```
index = clamp(avg_speed_kmh / ref_speed(experience) * 100, 0, 120)
confidence = 0.7 se speed>0 altrimenti 0.3; +0.05 se Advanced/Elite (cap 0.85)
```

### 5.3 Calorie

**File:** `bike_analyzer/core/calculators/calories.py`

MET-based (`calories_met`):

| Velocità (km/h) | MET |
| --- | --- |
| < 16 | 4.0 |
| 16–19 | 6.0 |
| 19–22 | 8.0 |
| ≥ 22 | `10.0 + (speed - 22) * 0.5` |

`calories = MET * weight_kg * duration_hours`

Physics-based (`calories_physics`):

```
g, crr, rho, cdA, eff, J_PER_CAL = 9.81, 0.005, 1.225, 0.4, 0.25, 4184
v_ms = avg_speed_kmh * 1000 / 3600
w_n = weight_kg * g
rolling = crr * w_n
air = 0.5 * rho * cdA * v_ms^2
grade = elevation_gain_m / (distance_km * 1000)        # 0 se indisponibile
gravity = w_n * grade
power = (rolling + air + gravity) * v_ms
energy = power * duration_minutes * 60
calories = energy / (eff * J_PER_CAL)                  # eff = 0.25 (75% perdite)
```

`estimate(ride, method="met" | "physics")`; `per_km(ride) = calories / distance_km`.

**BM2 `EnergyModel`** (lavoro meccanico, `kcal = P_mech * t / (0.24 * 4184)`, dove `0.24` è l'efficienza metabolica; `confidence` 0.85 se dislivello presente, 0.7 altrimenti, ×0.85 se peso `estimate`).

**Efficiency Score** (core): `benchmark = 30.0 kcal/km`; `efficiency = clamp(10 - (calories_per_km - 30)/5, 0, 10)`.

### 5.4 CTL / ATL / TSB

**File:** `bike_analyzer/backend/analytics/training_load.py`, `bike_analyzer/bm2/algorithms/training_load.py`

EWMA time constants (Banister):

- **CTL** (Chronic, 42g): `ctl = prev_ctl * 41/42 + tss * 1/42` (α = 1/42)
- **ATL** (Acute, 7g): `atl = prev_atl * 6/7 + tss * 1/7` (α = 1/7)
- **TSB** = `ctl - atl`

RSS (semplificato, `calculate_rss`): `tss = min(duration_h * 100, 200)`.

TSS potenza (BM2 `TrainingLoadModel`, `ftp > 0`):

```
IF = min(avg_power / ftp, 1.5)
NP = avg_power * (1 + 0.05 * (IF - 1))
TSS = (duration_s * NP * IF) / (ftp * 3600) * 100
```

Stato allenamento per TSB (`get_current_training_status` — **valori verificati**):

| TSB Range | Stato | Raccomandazione |
| --- | --- | --- |
| > 10 | `fresh` | Intense training recommended |
| 0 – 10 | `optimal` | Ideal state for quality training |
| −10 – 0 | `fatigued` | Light training or recovery recommended |
| −20 – (−10) | `overreached` | Urgent recovery needed; reduce volume/intensity |
| ≤ −20 | `burnout_risk` | Overtraining risk; total rest 2–3 days |

Rilevamento overtraining (`core/fitness_state.py`):

```
overtraining_risk = (atl > ctl * 1.3) AND (tsb < -20)
```

Proprietà calcolate `FitnessStateVector`:

| Proprietà | Condizione |
| --- | --- |
| `is_fresh` | `tsb > 15` |
| `is_ready_for_hard_effort` | `tsb > 5 AND atl < ctl * 1.1` |
| `is_overtraining_risk` | `atl > ctl * 1.3 AND tsb < -20` |

### 5.5 Load Manager — Soglie Sicurezza & Bilanciamento

**File:** `bike_analyzer/backend/analytics/load_manager/config.py`, `safety_balance.py`

`SafetyThresholds` (configurabili, `config.py`):

| Soglia | Default | Significato |
| --- | --- | --- |
| `acwr_high_risk` | `1.5` | ACWR sopra = alto rischio infortunio |
| `acwr_block` | `2.0` | ACWR sopra = **blocco** carico aggiuntivo |
| `acwr_detraining` | `0.8` | ACWR sotto = rischio detraining |
| `tsb_fatigue` | `-30.0` | TSB sotto = affaticamento eccessivo |
| `tsb_freshness_loss` | `20.0` | TSB sopra = rischio perdita fitness |
| `ctl_atl_sum_limit` | `250.0` | CTL+ATL sopra = ridurre volume |

Costanti temporali: `tau_ctl = 42`, `tau_atl = 7`, `acwr_short_days = 7`, `acwr_long_days = 28`.

**`evaluate_safety(load)`** (`safety_balance.py`) emette `SafetyAlert` con `RiskLevel` (`ok|info|warning|high|block`):

- `acwr > acwr_block` → `BLOCK` ("Blocco carico aggiuntivo")
- `acwr > acwr_high_risk` → `HIGH` ("Rischio infortunio alto")
- `acwr < acwr_detraining` → `INFO` ("Rischio detraining")
- `tsb < tsb_fatigue` → `HIGH` ("Fatica eccessiva")
- `tsb > tsb_freshness_loss` → `INFO` ("Rischio perdita fitness")
- `ctl + atl > ctl_atl_sum_limit` → `WARNING` ("Ridurre volume")

**Target TSS settimanali** (`config.py`, `LoadBalanceTarget` — **valori verificati**):

| Livello | Min TSS/sett | Max TSS/sett |
| --- | --- | --- |
| `beginner` | 200 | 400 |
| `intermediate` | 400 | 700 |
| `advanced` | 700 | 1000 |
| `elite` | 1000 | 1600 |

`balance(...)`: `desired = planned_week_total` (o media min/max target); `remaining_tss = max(desired - current_week_tss, 0)`; `recommended_per_ride = remaining_tss / remaining_rides`; `in_balance = min ≤ current ≤ max`.

`redistribute(...)`: **suggerisce, non vieta** (`#4`). `per_ride = (remaining_tss / remaining_rides) * recovery_factor`; capped a `residual_capacity` se fornita.

### 5.6 Recovery Model (BM2)

**File:** `bike_analyzer/bm2/algorithms/recovery.py`

```
readiness = clamp(100 - fatigue*6 - sleep_deficit*4 + hrv_bonus, 0, 100)
sleep_deficit = max(0, 8 - sleep_hours)
hrv_bonus = clamp((hrv - baseline_hrv)/baseline_hrv * 20, -10, 10)   # solo se baseline_hrv > 0
```

`required_inputs`: `fatica`, `sonno_ore`, `hrv`. Confidence: `0.7` se sleep>0 o hrv>0, altrimenti `0.4`. Readiness < 40 → insight `warning` (Knowledge Engine).

### 5.7 Nutrition Model (BM2)

**File:** `bike_analyzer/bm2/algorithms/nutrition.py`

```
carbs_per_h = 30 + intensity * 30          # 30..60 g/h (intensity da FatigueModel)
carbs_g  = carbs_per_h * duration_h
water_L  = 0.6 * duration_h
protein_g = 0.3 * weight_kg                # post-attività
```

`required_inputs`: `durata`, `intensità`, `massa_corpo`. Confidence: `0.7` se `duration_h > 0` altrimenti `0.3`.

### 5.8 Route Difficulty Model (BM2)

**File:** `bike_analyzer/bm2/algorithms/route_difficulty.py`

```
norm_dist  = min(distance_km / 100, 1)
norm_gain  = min(gain_m / 2000, 1)
norm_slope = min(|avg_slope%| / 12, 1)
rough      = ROUGHNESS_FACTOR[surface]      # asphalt 1.0, gravel 1.25, dirt 1.5, trail 1.8
cap        = {Beginner:1.3, Intermediate:1.0, Advanced:0.8, Elite:0.65}
raw        = 0.3*norm_dist + 0.3*norm_gain + 0.25*norm_slope + 0.15*(rough-1)
difficulty = clamp(100 * raw / cap, 0, 100)
```

Categoria (`_category`): `<20` Facile, `<45` Moderato, `<70` Impegnativo, `≥70` Estremo. Knowledge Engine: `Impegnativo`/`Estremo` → `warning`.

### 5.9 Energy Model (BM2)

**File:** `bike_analyzer/bm2/algorithms/energy.py`

```
v = distance_m / duration_s                # m/s
slope = avg_slope_percent / 100
P_mech = (crr*m*g + m*g*sin(atan(slope)) + 0.5*rho*cdA*v_air^2) * v   # v_air = v + vento
E_mech = P_mech * duration_s
kcal = E_mech / (0.24 * 4184)              # 0.24 = efficienza metabolica
```

`required_inputs`: `massa_totale`, `velocità`, `pendenza`, `durata`, `crr`, `cda`. Confidence: `0.85` se dislivello presente, `0.7` altrimenti; ×`0.85` se peso `estimate`.

### 5.10 TSS / Training Load Model (BM2)

**File:** `bike_analyzer/bm2/algorithms/training_load.py`

Alfa EWMA: `alpha_ctl = 2/(42+1)`, `alpha_atl = 2/(7+1)` (formula `2/(N+1)`). `TSS` per storico: `(t*NP*IF)/(ftp*3600)*100`. Se nessuno storico: singola ride con `avg_power = ftp*0.7`. Confidence: `0.8` se ≥7 attività, `0.6` se ≥1, `0.3` se nessuna.

### 5.11 Knowledge Engine — Mappatura Insight

**File:** `bike_analyzer/bm2/knowledge.py`

| Modello sorgente | Concetto | Severity |
| --- | --- | --- |
| `RouteDifficultyModel` | `Percorso: {category}` | `warning` se Impegnativo/Estremo, else `info` |
| `FatigueModel` | `Fatica {value}/10` | `warning` se ≥6, else `info` |
| `PerformanceModel` | `Prestazione {value}/100` | `info` |
| `RecoveryModel` | `Prontenza {value}/100` | `warning` se <40, else `info` |
| `NutritionModel` | `Nutrizione` (carbs/water/protein) | `info` |

### 5.12 Calcolo Potenza Fisica condiviso

**File:** `bike_analyzer/core/physics/power.py` (`cycling_forces`), usato da `bm2/algorithms/base.py::_cycling_forces`

Funzione unica delegata da tutti gli algoritmi BM2 per forze di resistenza e potenza meccanica richiesta:

```
F_roll = crr * m * g
F_grav = m * g * sin(atan(slope_fraction))
F_air  = 0.5 * rho * cdA * v_air^2
P = (F_roll + F_grav + F_air) * v   # moltiplicato per efficienza trasmissione eta
```

Costanti: `g = 9.81 m/s²`, `rho = 1.225 kg/m³` (da `Algorithm.G`/`Algorithm.RHO`).

---

## 6. Convenzioni Trasversali

- **Tenant isolation:** colonna `tenant_id` (default `0`) su quasi tutte le tabelle; `0` = tenant locale/singolo-utente.
- **Timestamp:** SQLite serializza `created_at`/`computed_at`/`date` come `TEXT` (ISO). L'ORM async usa `DateTime(timezone=True)`.
- **GPS:** `gps_points` è serializzato in JSON `TEXT` nello schema sync; nel DTO/API è `list[GPSPoint]`.
- **External identity:** `(external_source, external_id)` UNIQUE su `rides`; `save_ride` è idempotente su import esterni.
- **Unità:** BM2 normalizza sempre in unità canoniche interne prima del calcolo (`Quantity` + `UnitRegistry`); i layer core (1.x) lavorano in km/h, km, minuti, kcal.
- **Confidence:** ogni `ModelResult` BM2 riporta `confidence` 0..1 derivata da `SOURCE_CONFIDENCE` e completezza dati; gli score core sono deterministici senza confidence.

## 7. Differenze note tra layer (sync vs ORM/Alembic)

| Elemento | SQLite sync (`init_db`) | ORM/Alembic (`db/models.py`) |
| --- | --- | --- |
| `metrics` | forma a colonne (`fatigue_score`, `efficiency_score`, ...) | Lineage chiave/valore (`metric_type`, `value`, `unit`) |
| `strava_tokens`/`garmin_tokens` | non presenti | non presenti (solo concetto ingestion) |
| `ix_athletes_user`, `ix_fitness_states_ctl` | assenti | documentati in alcuni doc legacy ma **non** definiti in `db/models.py` |
| `tenant_id` | aggiunto a runtime su `training_stress_days`/`metrics`/`chat_history`/`calendar_events` | presente a definizione |

> Per la lineage Alembic completa (revisioni, `uq_rides_external_identity`, `ix_*`) vedere `database-schema.md`.
