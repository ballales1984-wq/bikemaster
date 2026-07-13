# Database Schema — Completo

Riferimento completo dello schema dati di BikeMaster, derivato dal codice reale:

- **Sync (SQLite):** `bike_analyzer/backend/db/database.py` → `init_db()` è la fonte autoritativa dello schema SQLite (DDL + `ALTER` additivi idempotenti).
- **Async (PostgreSQL/SQLite):** `bike_analyzer/backend/db/models.py` (SQLAlchemy 2.0 `Mapped` ORM).
- **ORM leggero:** `bike_analyzer/backend/db/postgres_db.py` (`TrainingGoalModel`, `PlannedWorkoutModel`).
- **Migrazioni:** `alembic/versions/` (lineage completo più sotto).

> **Doppia sorgente di verità.** Il layer sync (SQLite) e la lineage Alembic (PostgreSQL) non sono perfettamente allineati. Le differenze note sono elencate nella sezione [Discrepanze tra i layer](#discrepanze-tra-i-layer).

---

## Tabelle

### `users`
Account applicativi / autenticazione.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `username` | TEXT | UNIQUE, NOT NULL |
| `email` | TEXT | UNIQUE, nullable |
| `password_hash` | TEXT | bcrypt |
| `is_admin` | INTEGER/BOOL | default 0/False |
| `is_active` | INTEGER/BOOL | default 1/True |
| `created_at` | TEXT/DateTime | |
| `updated_at` | TEXT/DateTime | |

### `athletes`
Profilo atleta per i calcoli personalizzati.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | TEXT | NOT NULL |
| `email` | TEXT | |
| `picture` | TEXT | URL avatar |
| `age` | INTEGER | default 30 |
| `weight_kg` | REAL | default 70 |
| `height_cm` | REAL | |
| `fat_percentage` | REAL | |
| `years_active` | INTEGER | default 1 |
| `weekly_sessions` | INTEGER | default 3 |
| `monthly_hours` | REAL | |
| `annual_hours` | REAL | |
| `experience_level` | TEXT | default `Beginner` |
| `goals` | TEXT | |
| `preferred_terrain` | TEXT | |
| `weekly_volume_km` | REAL | |
| `best_segments` | TEXT | |
| `medical_notes` | TEXT | |
| `equipment` | TEXT | |
| `ftp_watts` | REAL | Functional Threshold Power |
| `password_hash` | TEXT | (String(255) dopo migrazione `1a2b3c4d5e6f`) |
| `user_id` | INTEGER | FK→users.id, indice `ix_athletes_user` (solo Alembic) |
| `tenant_id` | INTEGER | default 0 (multi-tenant) |
| `created_at` | TEXT/DateTime | |

### `rides`
Sessione ciclistica completa.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | proprietario |
| `tenant_id` | INTEGER | default 0 |
| `date` | TEXT/String | NOT NULL (ISO) |
| `distance_km` | REAL | |
| `duration_minutes` | REAL | |
| `avg_speed_kmh` | REAL | |
| `weight_kg` | REAL | default 70 |
| `calories` | REAL | |
| `heart_rate_avg` | REAL | |
| `elevation_gain_m` | REAL | |
| `gps_points` | TEXT | array GPS serializzato JSON |
| `external_source` | TEXT/String | es. `strava`, `garmin` |
| `external_id` | TEXT/String | id attività esterna |
| `title` | TEXT/String | |
| `activity_type` | TEXT | default `ride` |
| `is_official` | INTEGER/BOOL | default 1/True |
| `source` | TEXT | default `manual` |
| `created_at` | TEXT/DateTime | |

**Vincoli/indici:** UNIQUE `uq_rides_external_identity(external_source, external_id)`; indici `idx_rides_date`, `idx_rides_distance`, `idx_rides_duration`, `idx_rides_speed`, `idx_rides_athlete`, `ix_rides_athlete_date`.

### `fitness_states`
Snapshot fisiologico dell'atleta (creato da ORM async + Alembic `add_fitness_states`, **non** dal sync `init_db()`).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | FK→athletes.id |
| `tenant_id` | INTEGER | default 0 |
| `date` | String | NOT NULL |
| `computed_at` | DateTime(tz) | |
| `fitness` | Float | |
| `fatigue` | Float | |
| `form` | Float | |
| `atl` | Float | Acute Training Load |
| `ctl` | Float | Chronic Training Load |
| `tsb` | Float | Training Stress Balance |
| `recovery_hours_needed` | Float | |
| `weekly_tss` | Float | |
| `monthly_tss` | Float | |
| `trend_7d` | String | default `stable` |
| `trend_30d` | String | default `stable` |
| `risk_indicators` | Text | JSON list |
| `recommendation` | Text | |

**Indici:** `ix_fitness_states_athlete_date`, `ix_fitness_states_ctl`.

### `chat_history`
Persistenza conversazioni AI Coach (sync + async `ChatHistoryModel`).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | FK→athletes.id, indicizzato, nullable |
| `tenant_id` | INTEGER | default 0 |
| `role` | TEXT | NOT NULL (`user`/`assistant`) |
| `content` | TEXT | NOT NULL |
| `created_at` | TEXT/DateTime | |

**Indice:** `ix_chat_history_athlete_id`. Retention configurabile (`AI_COACH_CHAT_RETENTION_DAYS`, default 90; `prune_chat_history`).

> Nella lineage PostgreSQL esiste anche una tabella `chat_messages` (creata da `add_pgvector_knowledge_chunks`, poi dotata di `tenant_id`). Vedi discrepanze.

### `calendar_events`
Eventi/pianificazione allenamento.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | FK→athletes.id |
| `tenant_id` | INTEGER | default 0 |
| `title` | TEXT | NOT NULL |
| `event_type` | TEXT | default `training` |
| `date` | TEXT | NOT NULL |
| `duration_minutes` | INTEGER | default 0 |
| `description` | TEXT | |
| `completed` | INTEGER | default 0 |
| `weather_temp` | REAL | cache meteo |
| `weather_humidity` | REAL | |
| `weather_description` | TEXT | |
| `created_at` | TEXT | |

### `weather_cache`
Cache previsioni meteo per coordinata/data.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `lat` | REAL | NOT NULL |
| `lon` | REAL | NOT NULL |
| `date` | TEXT | NOT NULL |
| `temperature` | REAL | |
| `humidity` | REAL | |
| `description` | TEXT | |
| `cached_at` | TEXT | |

**Vincolo:** UNIQUE `(lat, lon, date)`.

### `training_stress_days`
Serie giornaliera del carico di allenamento.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | NOT NULL, FK→athletes.id |
| `date` | TEXT | NOT NULL |
| `tss` | REAL | Training Stress Score |
| `atl` | REAL | |
| `ctl` | REAL | |
| `tsb` | REAL | |
| `created_at` | TEXT | |
| `updated_at` | TEXT | |

**Vincolo:** UNIQUE `(athlete_id, date)` (upsert).

### `metrics`
Metriche derivate per ride/atleta.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | FK→athletes.id |
| `ride_id` | INTEGER | FK→rides.id |
| `fatigue_score` | REAL | |
| `recovery_hours` | REAL | |
| `calories_per_km` | REAL | |
| `efficiency_score` | REAL | |
| `created_at` | TEXT | |
| `tenant_id` | INTEGER | default 0 |

**Indice:** `idx_metrics_ride(ride_id)`.

> La migrazione `08ee39bfe529` rimodella `metrics` in stile chiave/valore (`metric_type`, `value`, `unit`, `recorded_at`) nella lineage Alembic: lo schema effettivo di `metrics` dipende dal backend usato (SQLite sync vs PostgreSQL/Alembic).

### `training_goals`
Obiettivi di allenamento (es. granfondo).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | NOT NULL, FK→athletes.id |
| `tenant_id` | INTEGER | default 0 |
| `title` | TEXT | NOT NULL |
| `description` | TEXT | |
| `goal_type` | TEXT | default `granfondo` |
| `target_date` | TEXT | |
| `target_distance_km` | REAL | |
| `target_elevation_m` | REAL | |
| `status` | TEXT | default `active` |
| `created_at` | TEXT | |

### `planned_workouts`
Workout pianificati collegati a un obiettivo.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | NOT NULL, FK→athletes.id |
| `tenant_id` | INTEGER | default 0 |
| `goal_id` | INTEGER | FK→training_goals.id |
| `date` | TEXT | NOT NULL |
| `title` | TEXT | NOT NULL |
| `workout_type` | TEXT | default `endurance` |
| `duration_minutes` | INTEGER | default 60 |
| `target_intensity` | REAL | default 0.5 |
| `completed` | INTEGER | default 0 |
| `completed_at` | TEXT | |

### `road_incidents`
Incidenti stradali per l'analisi di sicurezza.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `source_id` | TEXT | NOT NULL |
| `lat` | REAL | NOT NULL |
| `lon` | REAL | NOT NULL |
| `incident_date` | TEXT | NOT NULL |
| `severity` | TEXT | default `medium` |
| `description` | TEXT | |
| `road_type` | TEXT | |
| `source` | TEXT | default `local` |
| `created_at` | TEXT | |

**Vincolo:** UNIQUE `(source_id, source)` (INSERT OR IGNORE).

### `route_safety_scores`
Punteggio di sicurezza calcolato per una ride.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `ride_id` | INTEGER | FK→rides.id |
| `athlete_id` | INTEGER | FK→athletes.id |
| `risk_score` | REAL | 0..1 |
| `label` | TEXT | etichetta rischio |
| `advice` | TEXT | |
| `road_type_counts` | TEXT | JSON |
| `has_bike_infrastructure` | INTEGER | |
| `incident_count` | INTEGER | |
| `route_length_km` | REAL | |
| `computed_at` | TEXT | |
| `tenant_id` | INTEGER | default 0 |

### `pois`
Point of Interest (vista, fontana, ristoro, bivio, pericolo, culturale, tecnico).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | TEXT | NOT NULL |
| `description` | TEXT | NOT NULL |
| `lat` | REAL | NOT NULL |
| `lon` | REAL | NOT NULL |
| `type` | TEXT | NOT NULL |
| `photos` | TEXT | JSON |
| `video_url` | TEXT | |
| `difficulty_note` | TEXT | |
| `tags` | TEXT | JSON |
| `itinerary_id` | INTEGER | |
| `created_by` | INTEGER | |
| `tenant_id` | INTEGER | default 0 |
| `created_at` | TEXT | |

**Indice:** `idx_pois_coords(lat, lon)`.

### `knowledge_chunks`
Chunk documentali per la RAG (vector DB).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `topic` | String | default "" |
| `chunk_id` | String | default "" |
| `text` | Text | contenuto chunk |
| `word_count` | Integer | |
| `char_count` | Integer | |
| `token_count` | Integer | |
| `section` | String | |
| `embedding` | `Vector(384)` / Text | pgvector se disponibile, altrimenti Text |

**Indice:** `ix_knowledge_chunks_topic`. `EMBEDDING_DIMENSION = 384` (`all-MiniLM-L6-v2`). Su PostgreSQL viene eseguito `CREATE EXTENSION vector`.

### `strava_tokens` / `garmin_tokens`
Token OAuth per provider esterni (creati da `a1b2c3d4e5f6`).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER | PK |
| `athlete_id` | INTEGER | FK→athletes.id ON DELETE CASCADE, UNIQUE per atleta |
| `access_token` | TEXT | |
| `refresh_token` | TEXT | auto-refresh |
| `expires_at` | — | scadenza token |
| `tenant_id` | INTEGER | default 0 |

---

## Multi-tenancy

Quasi tutte le tabelle funzionali hanno una colonna `tenant_id` (default 0) aggiunta in modo consolidato dalla migrazione `cf_tenant_id_consolidated` a **13 tabelle**: `athletes`, `rides`, `fitness_states`, `calendar_events`, `chat_messages`, `training_stress_days`, `metrics`, `training_goals`, `planned_workouts`, `knowledge_chunks`, `strava_tokens`, `garmin_tokens`, `route_safety_scores`. Le query di lettura/scrittura sono tenant-scoped.

---

## Migrazioni Alembic

`alembic/env.py` + `alembic.ini` guidano le migrazioni. `bike_analyzer/backend/db/migrations.py:run_migrations_on_startup()` esegue `alembic upgrade head` all'avvio (gated da `RUN_MIGRATIONS_ON_STARTUP`, default attivo, solo se `DATABASE_URL` è impostata).

| Revision | Down-revision | Contenuto |
|---|---|---|
| `08ee39bfe529` | — (base) | Initial models: ritipizza `athletes`/`calendar_events`/`rides`/`metrics`; rimodella `metrics` (metric_type/value/unit/recorded_at); indici base |
| `a1b2c3d4e5f6` | `08ee39bfe529` | Integrazione Strava/Garmin: crea `strava_tokens`, `garmin_tokens`; aggiunge `rides.external_source/external_id/title` |
| `9f8e7d6c5b4a` | `a1b2c3d4e5f6` | Dedup ride su `(external_source, external_id)`; crea UNIQUE `uq_rides_external_identity` |
| `add_fitness_states` | `08ee39bfe529` | Crea `fitness_states` (+ indici) |
| `cf_tenant_id_consolidated` | `add_fitness_states` | Aggiunge `tenant_id` + indice a 13 tabelle (consolida migrazioni tenant precedenti) |
| `1a2b3c4d5e6f` | `cf_tenant_id_consolidated` | Crea `users`; aggiunge `athletes.user_id` (+ `ix_athletes_user`); restringe `athletes.password_hash` a String(255) |
| `add_pgvector_knowledge_chunks` | `08ee39bfe529` | Crea `knowledge_chunks` (embedding) + `chat_messages`; `CREATE EXTENSION vector` su Postgres |
| `bbe692252c5e` | `add_pgvector_knowledge_chunks`, `cf_tenant_id_consolidated`, `9f8e7d6c5b4a` | Merge (single head) |
| `add_chat_history` | `bbe692252c5e`, `1a2b3c4d5e6f` | Crea `chat_history` async (+ `ix_chat_history_athlete_id`); **HEAD** |

**Lineage (head = `add_chat_history`):**

```
08ee39bfe529
├── a1b2c3d4e5f6 → 9f8e7d6c5b4a ─┐
├── add_fitness_states → cf_tenant_id_consolidated → 1a2b3c4d5e6f ─┐
└── add_pgvector_knowledge_chunks ─┐                               │
                                   └── bbe692252c5e ───────────────┴── add_chat_history (HEAD)
```

---

## Accesso ai dati

Non esiste un unico repository pattern: l'accesso è ibrido.

- **Sync (SQLite)** — `db/database.py`: funzioni module-level. `get_db_connection()` è un `@contextmanager` con `WAL`, `busy_timeout=5000`, `foreign_keys=ON`, `row_factory=Row`, retry-on-locked. Include CRUD ride/atleti/calendar/metriche, chat, training stress (upsert), safety, POI, utenti, backup.
- **Async (asyncpg/aiosqlite)** — `db/async_db.py`: `create_async_engine` con auto-rewrite dello schema URL, `async_sessionmaker`, `init_async_db()` (`create_all` sulle tabelle core), `get_rides_by_athlete_async()`.
- **ORM leggero** — `db/postgres_db.py`: `TrainingGoalModel`, `PlannedWorkoutModel`, `get_session()`.
- **Repository di dominio** — `bike_analyzer/backend/analytics/repositories/`: `athlete_repository`, `ride_repository`, `chat_history_repository`, `fitness_state_repository`, `poi_repository`, `training_stress_repository`, `user_repository`.
- **Vector store** — `db/vector_db.py`: `VectorStore` (SQLite BLOB) + `embed_text`/`similarity_search`, fallback TF-IDF/BM25 quando pgvector/sklearn non disponibili.

---

## Discrepanze tra i layer

1. **`fitness_states`** è creata dall'ORM async e da Alembic, ma **non** dal sync `init_db()`.
2. L'**ORM async** (`models.py`) non copre `metrics`, `training_stress_days`, `training_goals`, `planned_workouts`, `calendar_events`, `weather_cache`, `road_incidents`, `route_safety_scores`, non ha `athletes.user_id` e non definisce la FK su `rides.athlete_id`.
3. Nella lineage PostgreSQL esistono **due tabelle chat**: `chat_history` (async `ChatHistoryModel`) e `chat_messages` (da `add_pgvector_knowledge_chunks`).
4. Il layer **sync** è l'unico writer per la maggior parte delle tabelle funzionali; il path async è prevalentemente in lettura.
5. La forma di **`metrics`** differisce tra SQLite (colonne score) e Alembic/Postgres (chiave/valore).

> Per l'evoluzione dello schema fare riferimento alla lineage Alembic come sorgente più completa quando si usa PostgreSQL. Vedi anche [`../database-migration.md`](../database-migration.md).
