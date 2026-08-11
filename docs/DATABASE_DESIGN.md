# BikeMaster — Database Design (Implementato)

Riferimento autorevole: `bike_analyzer/backend/db/models.py` (ORM) e le migration in `alembic/versions/`.
Head Alembic corrente: `13a1d54d325f` (verificato con `alembic check` -> "No new upgrade operations detected").

Lo schema è **dual-mode**: SQLite (store locale primario, WAL) e PostgreSQL opzionale (cloud sync / hub multi-tenant).
Il layer sync (`database.py`) è la source of truth per SQLite; `models.py` definisce i mapping ORM usati dal session async.

> **Refactoring in corso (2026-08-11):** `database.py` (~4065 linee) è in estrazione per dominio in repository pattern.
> Vedi `review_db_architecture.md` per il piano di smontaggio completo.

---

## 1. Analisi dei dati

Il dominio si divide in 5 famiglie:

- **Identity & Auth** (`users`, `external_identities`, `external_tokens`, `totp_secrets`, `sessions`, `audit_logs`): gestione utenti, OAuth esterni (Google/Strava/Garmin/Wahoo), 2FA TOTP, sessioni JWT/refresh, audit.
- **Athlete & Profile** (`athletes`): profilo atleta, parametri fisiologici (ftp, peso, experience), collegato opzionalmente a `users` (1:1).
- **Activity & Telemetry** (`rides`, `segments`, `pauses`, `metrics`): uscite, segmenti/pause, metriche derivate per ride. GPS grezzo in `rides.gps_points` (JSON) per evitare l'esplosione di righe di una tabella point.
- **Training Load & Planning** (`training_stress_days`, `fitness_states`, `training_goals`, `planned_workouts`, `calendar_events`): CTL/ATL/TSB, stati di fitness/fatica, piani e calendario.
- **Safety, Content & Sync** (`road_incidents`, `route_safety_scores`, `pois`, `weather_cache`, `knowledge_chunks`, `sync_entity_state`, `sync_settings`, `sync_conflicts`): sicurezza stradale, POI, cache meteo, knowledge base vettoriale (pgvector), e la macchina a stati di sync device<->cloud.

Multi-tenancy: `tenant_id` (default 0 = locale) su quasi tutte le tabelle abilitanti. Le tabelle `weather_cache` e `knowledge_chunks` sono globali (no tenant). Deduplicazione esterna tramite `(external_source, external_id)` su `rides` e `(provider, external_id)` su `external_identities`.

---

## 2. Schema ER (sintetico)

```
users 1—1 athletes (user_id)
users 1—N external_identities, external_tokens, totp_secrets
users 1—N sessions (athlete_id, via athletes)

athletes 1—N rides
athletes 1—N training_stress_days, fitness_states, metrics
athletes 1—N training_goals, planned_workouts, calendar_events, chat_history
athletes 1—N route_safety_scores, pois
athletes 1—N external_identities, external_tokens
athletes 1—N strava_tokens, garmin_tokens (1—1)

rides 1—N segments, pauses
rides 1—1 metrics
rides 1—N route_safety_scores

training_goals 1—N planned_workouts (goal_id)
external_identities/strava_tokens/garmin_tokens/external_tokens -> provider OAuth
```

---

## 3. Tabelle

Ordinamento per famiglia. Tipi: `PK`=primary key, `FK`=foreign key, `UQ`=unique, `IX`=index, `NN`=not null.

### Identity & Auth

#### `users`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| username | VARCHAR | NN, UQ |
| email | VARCHAR | UQ |
| password_hash | TEXT |  |
| role | VARCHAR(6) | NN |
| is_admin | BOOLEAN | NN |
| is_client | BOOLEAN | NN |
| is_active | BOOLEAN | NN |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| _UQ_ | | UQ(username) |
| _UQ_ | | UQ(email) |

Indici: `ix_users_username`(username), `ix_users_is_active`(is_active), `ix_users_email`(email)

#### `external_identities`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | FK->users.id |
| athlete_id | INTEGER | FK->athletes.id |
| provider | VARCHAR | NN |
| external_id | VARCHAR | NN |
| external_email | VARCHAR |  |
| display_name | VARCHAR |  |
| picture_url | VARCHAR |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| _UQ_ | | UQ(provider, external_id) |

Indici: `ix_external_identity_athlete`(athlete_id), `ix_external_identity_provider`(provider), `ix_external_identity_external_id`(external_id)

#### `external_tokens`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | FK->users.id |
| athlete_id | INTEGER | FK->athletes.id |
| provider | VARCHAR | NN |
| access_token | TEXT |  |
| refresh_token | TEXT |  |
| expires_at | DATETIME |  |
| scope | VARCHAR |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| _UQ_ | | UQ(athlete_id, provider) |

Indici: `ix_external_token_athlete`(athlete_id), `ix_external_token_provider`(provider), `ix_external_token_expires`(expires_at)

#### `totp_secrets`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | NN, FK->users.id |
| secret | VARCHAR | NN |
| enabled | BOOLEAN | NN |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| _UQ_ | | UQ(user_id) |

#### `sessions`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | NN, FK->athletes.id |
| refresh_token | VARCHAR | NN, UQ |
| jti | VARCHAR | NN, UQ |
| expires_at | DATETIME | NN |
| created_at | DATETIME |  |
| revoked_at | DATETIME |  |
| _UQ_ | | UQ(jti) |
| _UQ_ | | UQ(refresh_token) |

Indici: `ix_sessions_athlete_id`(athlete_id)

#### `audit_logs`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| actor_id | INTEGER |  |
| action | VARCHAR | NN |
| resource | VARCHAR | NN |
| resource_id | INTEGER |  |
| details | TEXT | NN |
| ip_address | VARCHAR |  |
| created_at | DATETIME |  |


### Athlete & Profile

#### `athletes`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | FK->users.id, UQ |
| name | VARCHAR | NN |
| email | VARCHAR |  |
| picture | VARCHAR |  |
| age | INTEGER | NN |
| weight_kg | FLOAT | NN |
| height_cm | FLOAT |  |
| fat_percentage | FLOAT |  |
| years_active | INTEGER | NN |
| weekly_sessions | INTEGER | NN |
| monthly_hours | FLOAT | NN |
| annual_hours | FLOAT | NN |
| experience_level | VARCHAR | NN |
| goals | TEXT |  |
| preferred_terrain | TEXT |  |
| weekly_volume_km | FLOAT | NN |
| best_segments | TEXT |  |
| medical_notes | TEXT |  |
| equipment | TEXT |  |
| ftp_watts | FLOAT |  |
| password_hash | TEXT |  |
| tenant_id | INTEGER | NN |
| created_at | DATETIME |  |
| _UQ_ | | UQ(user_id) |

Indici: `ix_athletes_user_id`(user_id), `ix_athletes_tenant`(tenant_id), `ix_athletes_experience_level`(experience_level), `ix_athletes_email`(email), `ix_athletes_name`(name)


### Activity & Telemetry

#### `rides`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | FK->athletes.id |
| tenant_id | INTEGER | NN |
| date | VARCHAR | NN |
| distance_km | FLOAT | NN |
| duration_minutes | FLOAT | NN |
| avg_speed_kmh | FLOAT | NN |
| weight_kg | FLOAT | NN |
| calories | FLOAT | NN |
| heart_rate_avg | FLOAT |  |
| elevation_gain_m | FLOAT |  |
| gps_points | TEXT |  |
| external_source | VARCHAR |  |
| external_id | VARCHAR |  |
| title | VARCHAR |  |
| activity_type | VARCHAR(12) | NN |
| is_official | BOOLEAN | NN |
| source | VARCHAR | NN |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| _UQ_ | | UQ(external_source, external_id) |

Indici: `ix_rides_athlete_id`(athlete_id), `ix_rides_tenant`(tenant_id), `ix_rides_date`(date)

#### `segments`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| ride_id | INTEGER | NN, FK->rides.id |
| name | VARCHAR | NN |
| start_index | INTEGER | NN |
| end_index | INTEGER | NN |
| distance_m | FLOAT |  |
| avg_speed_kmh | FLOAT |  |
| elevation_gain_m | FLOAT |  |

Indici: `ix_segments_ride_id`(ride_id)

#### `pauses`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| ride_id | INTEGER | NN, FK->rides.id |
| start_index | INTEGER | NN |
| end_index | INTEGER | NN |
| duration_seconds | FLOAT |  |

Indici: `ix_pauses_ride_id`(ride_id)

#### `metrics`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | FK->athletes.id |
| ride_id | INTEGER | FK->rides.id, UQ |
| fatigue_score | FLOAT |  |
| recovery_hours | FLOAT |  |
| calories_per_km | FLOAT |  |
| efficiency_score | FLOAT |  |
| created_at | DATETIME |  |
| tenant_id | INTEGER | NN |
| _UQ_ | | UQ(ride_id) |

Indici: `ix_metrics_ride_id`(ride_id), `ix_metrics_athlete_id`(athlete_id), `ix_metrics_tenant`(tenant_id)


### Training Load & Planning

#### `training_stress_days`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | NN, FK->athletes.id |
| date | VARCHAR | NN |
| tss | FLOAT |  |
| atl | FLOAT |  |
| ctl | FLOAT |  |
| tsb | FLOAT |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| tenant_id | INTEGER | NN |
| _UQ_ | | UQ(athlete_id, date) |

Indici: `ix_training_stress_days_tenant`(tenant_id), `ix_training_stress_days_athlete`(athlete_id), `ix_training_stress_days_date`(date)

#### `fitness_states`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | FK->athletes.id |
| tenant_id | INTEGER | NN |
| date | VARCHAR | NN |
| computed_at | DATETIME |  |
| fitness | FLOAT | NN |
| fatigue | FLOAT | NN |
| form | FLOAT | NN |
| atl | FLOAT | NN |
| ctl | FLOAT | NN |
| tsb | FLOAT | NN |
| recovery_hours_needed | FLOAT | NN |
| weekly_tss | FLOAT | NN |
| monthly_tss | FLOAT | NN |
| trend_7d | VARCHAR | NN |
| trend_30d | VARCHAR | NN |
| risk_indicators | TEXT |  |
| recommendation | TEXT |  |

#### `training_goals`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | NN, FK->athletes.id |
| tenant_id | INTEGER | NN |
| title | VARCHAR | NN |
| description | TEXT |  |
| goal_type | VARCHAR(15) | NN |
| target_date | VARCHAR |  |
| target_distance_km | FLOAT |  |
| target_elevation_m | FLOAT |  |
| status | VARCHAR | NN |
| created_at | DATETIME |  |

Indici: `ix_training_goals_tenant`(tenant_id), `ix_training_goals_status`(status), `ix_training_goals_athlete`(athlete_id)

#### `planned_workouts`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | NN, FK->athletes.id |
| tenant_id | INTEGER | NN |
| goal_id | INTEGER | FK->training_goals.id |
| date | VARCHAR | NN |
| title | VARCHAR | NN |
| workout_type | VARCHAR(9) | NN |
| duration_minutes | INTEGER | NN |
| target_intensity | FLOAT | NN |
| completed | BOOLEAN | NN |
| completed_at | VARCHAR |  |

Indici: `ix_planned_workouts_athlete`(athlete_id), `ix_planned_workouts_goal`(goal_id), `ix_planned_workouts_completed`(completed), `ix_planned_workouts_date`(date), `ix_planned_workouts_tenant`(tenant_id)

#### `calendar_events`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | FK->athletes.id |
| tenant_id | INTEGER | NN |
| title | VARCHAR | NN |
| event_type | VARCHAR(8) | NN |
| date | VARCHAR | NN |
| duration_minutes | INTEGER | NN |
| description | TEXT |  |
| completed | BOOLEAN | NN |
| weather_temp | FLOAT |  |
| weather_humidity | FLOAT |  |
| weather_description | VARCHAR |  |
| created_at | DATETIME |  |

Indici: `ix_calendar_events_athlete_id`(athlete_id), `ix_calendar_events_tenant`(tenant_id), `ix_calendar_events_athlete_id`(athlete_id), `ix_calendar_events_date`(date), `ix_calendar_events_athlete_date`(athlete_id, date)

#### `chat_history`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | FK->athletes.id |
| tenant_id | INTEGER | NN |
| role | VARCHAR | NN |
| content | TEXT | NN |
| created_at | DATETIME |  |

Indici: `ix_chat_history_athlete_id`(athlete_id)


### Safety, Content & Sync

#### `road_incidents`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| source_id | VARCHAR | NN |
| lat | FLOAT | NN |
| lon | FLOAT | NN |
| incident_date | VARCHAR | NN |
| severity | VARCHAR(8) | NN |
| description | TEXT |  |
| road_type | VARCHAR |  |
| source | VARCHAR | NN |
| created_at | DATETIME |  |
| _UQ_ | | UQ(source_id, source) |

Indici: `ix_road_incidents_source`(source), `ix_road_incidents_coords`(lat, lon), `ix_road_incidents_severity`(severity)

#### `route_safety_scores`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| ride_id | INTEGER | FK->rides.id |
| athlete_id | INTEGER | FK->athletes.id |
| risk_score | FLOAT |  |
| label | VARCHAR(9) |  |
| advice | TEXT |  |
| road_type_counts | TEXT |  |
| has_bike_infrastructure | BOOLEAN |  |
| incident_count | INTEGER |  |
| route_length_km | FLOAT |  |
| computed_at | DATETIME |  |
| tenant_id | INTEGER | NN |

Indici: `ix_route_safety_scores_ride`(ride_id), `ix_route_safety_scores_athlete`(athlete_id), `ix_route_safety_scores_tenant`(tenant_id)

#### `pois`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR | NN |
| description | TEXT | NN |
| lat | FLOAT | NN |
| lon | FLOAT | NN |
| type | VARCHAR(9) | NN |
| photos | TEXT |  |
| video_url | VARCHAR |  |
| difficulty_note | TEXT |  |
| tags | TEXT |  |
| itinerary_id | INTEGER |  |
| created_by | INTEGER | FK->athletes.id |
| tenant_id | INTEGER | NN |
| created_at | DATETIME |  |

Indici: `idx_pois_coords`(lat, lon), `ix_pois_type`(type), `ix_pois_tenant`(tenant_id)

#### `weather_cache`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| lat | FLOAT | NN |
| lon | FLOAT | NN |
| date | VARCHAR | NN |
| temperature | FLOAT |  |
| humidity | FLOAT |  |
| description | VARCHAR |  |
| cached_at | DATETIME |  |
| _UQ_ | | UQ(lat, lon, date) |

#### `knowledge_chunks`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| topic | VARCHAR | NN |
| chunk_id | VARCHAR | NN |
| text | TEXT | NN |
| word_count | INTEGER | NN |
| char_count | INTEGER | NN |
| token_count | INTEGER | NN |
| section | VARCHAR |  |
| embedding | VECTOR(384) | NN |
| tenant_id | INTEGER | NN |
| created_at | DATETIME |  |

#### `sync_entity_state`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| entity_type | VARCHAR | NN |
| entity_id | INTEGER | NN |
| source | VARCHAR | NN |
| reliability_score | FLOAT | NN |
| last_modified | DATETIME | NN |
| sync_status | VARCHAR | NN |
| sync_error | TEXT |  |
| cloud_id | VARCHAR |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| _UQ_ | | UQ(entity_type, entity_id) |

#### `sync_settings`

| Colonna | Tipo | Vincoli |
|---|---|---|
| key | VARCHAR | PK |
| value | VARCHAR | NN |
| updated_at | DATETIME |  |

#### `sync_conflicts`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| entity_type | VARCHAR | NN |
| entity_id | INTEGER | NN |
| local_data | TEXT | NN |
| remote_data | TEXT | NN |
| local_reliability | FLOAT | NN |
| remote_reliability | FLOAT | NN |
| local_modified | DATETIME | NN |
| remote_modified | DATETIME | NN |
| resolution | VARCHAR | NN |
| resolved_data | TEXT |  |
| resolution_reason | TEXT |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |

#### `strava_tokens`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | NN, FK->athletes.id, UQ |
| access_token | VARCHAR(1024) | NN |
| refresh_token | VARCHAR(1024) | NN |
| expires_at | INTEGER |  |
| scope | VARCHAR(200) |  |
| athlete_name | VARCHAR(200) |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| tenant_id | INTEGER | NN |
| _UQ_ | | UQ(athlete_id) |

#### `garmin_tokens`

| Colonna | Tipo | Vincoli |
|---|---|---|
| id | INTEGER | PK |
| athlete_id | INTEGER | NN, FK->athletes.id, UQ |
| access_token | VARCHAR(1024) | NN |
| refresh_token | VARCHAR(1024) | NN |
| expires_at | INTEGER |  |
| scope | VARCHAR(200) |  |
| athlete_name | VARCHAR(200) |  |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |
| tenant_id | INTEGER | NN |
| _UQ_ | | UQ(athlete_id) |


---

## 4. Relazioni

Tutte le relazioni ORM (`relationship()`) in `models.py`:

- `UserModel` -> athletes, oauth_identities, external_tokens, totp_secrets
- `AthleteModel` -> rides, chat_history, calendar_events, training_stress_days, fitness_states, training_goals, planned_workouts, metrics, route_safety_scores, pois, external_identities, external_tokens
- `RideModel` -> metrics, route_safety_scores (figli); athlete (genitore)
- `TrainingGoalModel` -> planned_workouts (figli)
- `ExternalIdentityModel` / `ExternalTokenModel` -> user, athlete
- `TOTPSecretModel` -> user
- `RouteSafetyScore` / `Segments` / `Pauses` -> ride
- `POIModel` -> created_by_athlete (athlete)
- `SyncEntityState` / `SyncConflict` / `KnowledgeChunkModel` / `WeatherCache` / `AuditLog` / `SessionModel` / `StravaToken` / `GarminToken` / `SyncSetting` non hanno relazioni ORM bidirezionali (tabelle di supporto/servizio).

---

## 5. SQLAlchemy Models

Definiti in `bike_analyzer/backend/db/models.py`. Pattern usato: `DeclarativeBase` + typed `Mapped[...]` / `mapped_column`, con `relationship(back_populates=...)` e cascade `all, delete-orphan` sui figli. Enum nativi (`UserRole`, `ActivityType`, `EventType`, `WorkoutType`, `GoalType`, `SyncStatus`, `ConflictResolution`, `IncidentSeverity`, `POIType`, `RiskLabel`) mappati via `Enum(...)`. `knowledge_chunks.embedding` usa `pgvector.sqlalchemy.Vector` se disponibile, altrimenti `Text` (fallback SQLite).

```python
class AthleteModel(Base):
    __tablename__ = "athletes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # ... profilo ftp_watts, weight_kg, experience_level, ecc.
    rides: Mapped[list['RideModel']] = relationship(back_populates='athlete', cascade='all, delete-orphan')
```

---

## 6. Indici

Riassunto degli indici per supportare le query calde (lookup per atleta, per data, per tenant, deduplicazione esterna):

| Tabella | Indici |
|---|---|
| users | ix_users_username(username), ix_users_is_active(is_active), ix_users_email(email) |
| athletes | ix_athletes_user_id(user_id), ix_athletes_tenant(tenant_id), ix_athletes_experience_level(experience_level), ix_athletes_email(email), ix_athletes_name(name) |
| rides | ix_rides_athlete_id(athlete_id), ix_rides_tenant(tenant_id), ix_rides_date(date) |
| training_stress_days | ix_training_stress_days_tenant(tenant_id), ix_training_stress_days_athlete(athlete_id), ix_training_stress_days_date(date) |
| metrics | ix_metrics_ride_id(ride_id), ix_metrics_athlete_id(athlete_id), ix_metrics_tenant(tenant_id) |
| chat_history | ix_chat_history_athlete_id(athlete_id) |
| calendar_events | ix_calendar_events_athlete_id(athlete_id), ix_calendar_events_tenant(tenant_id), ix_calendar_events_athlete_id(athlete_id), ix_calendar_events_date(date), ix_calendar_events_athlete_date(athlete_id, date) |
| training_goals | ix_training_goals_tenant(tenant_id), ix_training_goals_status(status), ix_training_goals_athlete(athlete_id) |
| planned_workouts | ix_planned_workouts_athlete(athlete_id), ix_planned_workouts_goal(goal_id), ix_planned_workouts_completed(completed), ix_planned_workouts_date(date), ix_planned_workouts_tenant(tenant_id) |
| road_incidents | ix_road_incidents_source(source), ix_road_incidents_coords(lat, lon), ix_road_incidents_severity(severity) |
| route_safety_scores | ix_route_safety_scores_ride(ride_id), ix_route_safety_scores_athlete(athlete_id), ix_route_safety_scores_tenant(tenant_id) |
| pois | idx_pois_coords(lat, lon), ix_pois_type(type), ix_pois_tenant(tenant_id) |
| sessions | ix_sessions_athlete_id(athlete_id) |
| segments | ix_segments_ride_id(ride_id) |
| pauses | ix_pauses_ride_id(ride_id) |
| external_identities | ix_external_identity_athlete(athlete_id), ix_external_identity_provider(provider), ix_external_identity_external_id(external_id) |
| external_tokens | ix_external_token_athlete(athlete_id), ix_external_token_provider(provider), ix_external_token_expires(expires_at) |

---

## 7. Vincoli

- **Primary key**: tutte le tabelle hanno `id` autoincrement (eccetto `sync_settings` con PK su `key`).
- **Unique**:
  - `users`: UQ(username) `None`
  - `users`: UQ(email) `None`
  - `athletes`: UQ(user_id) `None`
  - `rides`: UQ(external_source, external_id) `uq_rides_external_identity`
  - `training_stress_days`: UQ(athlete_id, date) `uq_training_stress_days`
  - `metrics`: UQ(ride_id) `None`
  - `weather_cache`: UQ(lat, lon, date) `uq_weather_cache`
  - `road_incidents`: UQ(source_id, source) `uq_road_incidents`
  - `strava_tokens`: UQ(athlete_id) `None`
  - `garmin_tokens`: UQ(athlete_id) `None`
  - `sync_entity_state`: UQ(entity_type, entity_id) `uq_sync_entity_state`
  - `sessions`: UQ(jti) `None`
  - `sessions`: UQ(refresh_token) `None`
  - `external_identities`: UQ(provider, external_id) `uq_external_identity`
  - `external_tokens`: UQ(athlete_id, provider) `uq_external_token_athlete_provider`
  - `totp_secrets`: UQ(user_id) `uq_totp_user`
- **Foreign key / ondelete**:
  - `athletes.user_id -> users.id` (CASCADE)
  - `rides.athlete_id -> athletes.id` (CASCADE)
  - `metrics.ride_id -> rides.id` (CASCADE, UQ)
  - `fitness_states/training_stress_days/training_goals/planned_workouts/chat_history/calendar_events/external_identities/external_tokens/strava_tokens/garmin_tokens/sessions -> athletes.id` (CASCADE/SET NULL)
  - `training_goals -> athletes`, `planned_workouts.goal_id -> training_goals.id` (SET NULL)
- **Enum**: 10 enum nativi applicati a `users.role`, `rides.activity_type`, `calendar_events.event_type`, `training_goals.goal_type`, `planned_workouts.workout_type`, `road_incidents.severity`, `route_safety_scores.label`, `pois.type`.
- **Multi-tenancy**: `tenant_id` NOT NULL default 0 su tutte le tabelle tenant-aware.

---

## 8. Motivazioni progettuali

- **GPS in JSON (`rides.gps_points`)** invece di una tabella `movement_points`: il volume (decine di punti/min) renderebbe la tabella relazionale ingestibile per l'uso locale; il JSON preserva i dati grezzi e l'analytics li processa in memoria. Se il volume cloud lo richiede, `movement_points` resta il candidato a serie temporali (vedi `docs/bm2/database-schema.md`).
- **Enum nativi**: valori controllati a db-level, indexing efficiente, nessun cast in app.
- **Deduplicazione esterna** `(external_source, external_id)` su `rides` e `(provider, external_id)` su `external_identities`: import idempotenti da Strava/Garmin/Wahoo/Google senza duplicati.
- **Separazione token per provider** (`strava_tokens`, `garmin_tokens`, `external_tokens`): i token vendor-specific hanno scope/refresh differenti; `external_tokens` è il vault generico OAuth, `totp_secrets` isola il 2FA server-side (mai nel JWT).
- **`sync_entity_state` / `sync_conflicts` / `sync_settings`**: macchina a stati per la sincronizzazione device<->cloud con risoluzione conflitti basata su reliability score, coerente con l'architettura local-first.
- **`knowledge_chunks` con `pgvector`**: similarity search per la knowledge base AI; fallback `Text` su SQLite mantiene il layer locale funzionante senza estensioni.
- **`tenant_id` ovunque**: abilita il passaggio trasparente da store locale (tenant 0) a hub multi-tenant PostgreSQL senza reshaping dello schema.

---

## Migration

Catena Alembic (head unico `13a1d54d325f`):

```
08ee39bfe529 (initial)
  -> add_fitness_states
  -> cf_tenant_id_consolidated -> 1a2b3c4d5e6f -> 9f8e7d6c5b4a
  -> a1b2c3d4e5f6
  -> add_pgvector_knowledge_chunks
bbe692252c5e (merge) <- {add_pgvector_knowledge_chunks, cf_tenant_id_consolidated, 9f8e7d6c5b4a}
  -> add_chat_history -> add_is_client_col -> ba4ede18c9fc (sync_models_expansion)
  -> 13a1d54d325f (add_enums_and_missing_models)  [HEAD]
```

Comandi:
```bash
alembic upgrade head      # applica tutte le migration
alembic check             # verifica coerenza models vs schema
alembic revision --autogenerate -m 'msg'   # nuova migration da diff
```