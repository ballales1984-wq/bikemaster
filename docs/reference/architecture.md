# Architettura del Sistema

Panoramica tecnica end-to-end di BikeMaster: layer applicativi, flusso di una richiesta, mappa dei moduli backend e frontend, integrazioni e osservabilità. Derivato dal codice reale in `bike_analyzer/` e `frontend/`.

Per la visione concettuale ad alto livello (Digital Twin, Engine) vedi [../ARCHITECTURE.md](../ARCHITECTURE.md) e [../BM2_ENGINE_ARCHITECTURE.md](../BM2_ENGINE_ARCHITECTURE.md).

---

## 1. Vista a strati (Clean Architecture)

```
┌──────────────────────────────────────────────────────────────┐
│  Presentation                                                  │
│  • FastAPI routes (api/routes.py, bm2_routes.py, admin_router) │
│  • Vue 3 SPA (frontend/) + PWA + Android (Capacitor)           │
├──────────────────────────────────────────────────────────────┤
│  Application / Use cases                                        │
│  • analytics/services/ (ride_analysis, fitness_state, context) │
│  • bm2/orchestrator.py, bm2/simulation.py                      │
├──────────────────────────────────────────────────────────────┤
│  Domain                                                         │
│  • core/models.py, core/fitness_state.py                      │
│  • bm2/models.py, bm2/units.py, bm2/algorithms/               │
├──────────────────────────────────────────────────────────────┤
│  Infrastructure                                                 │
│  • db/ (sync SQLite + async PG), repositories/                │
│  • ingestion/ (GPS + provider), maps/, traffic/, weather/     │
│  • security, rate_limiter, redis_client, monitoring, tracing  │
└──────────────────────────────────────────────────────────────┘
```

Regola di dipendenza: Presentation → Application → Domain ← Infrastructure. Il Domain non dipende da framework né da I/O.

---

## 2. Entry point ed esecuzione

`main.py` è l'entrypoint unificato con tre modalità:

| Comando | Modalità |
|---|---|
| `python main.py api` | API + dashboard (default) |
| `python main.py web` | Frontend standalone |
| `python main.py cli` | Demo analytics da riga di comando |

L'app FastAPI è costruita dalla factory in `bike_analyzer/backend/api/app_factory.py`, che:
- registra il rate limiter (`app.state.limiter`) e `SlowAPIMiddleware`;
- aggiunge `MetricsMiddleware` (Prometheus) e `CORSMiddleware` (origini da `CORS_ORIGINS`, wildcard vietata in produzione);
- include i router:
  - `router` → prefix `/api/v1`
  - `admin_router` → prefix `/api/v1/admin` (tag `admin`)
  - `bm2_router` → prefix `/api/v1/bm2` (tag `bm2`)
- esegue le migrazioni all'avvio (`db/migrations.py`, se `DATABASE_URL` è impostata).

---

## 3. Flusso di una richiesta (esempio: analisi ride)

```
Client (SPA/mobile)
   │  Authorization: Bearer <JWT>
   ▼
CORSMiddleware → SlowAPIMiddleware (rate limit) → MetricsMiddleware
   ▼
Route  POST /api/v1/rides/{id}/analyze   (routes.py)
   │  Depends(get_current_user)  → security.py (verifica JWT, tenant)
   ▼
Service  ride_analysis_service.py        (analytics/services/)
   │  usa context_builder + calculators
   ▼
Domain   core/models.py + analytics/*    (funzioni pure: power, fatigue, calorie)
   ▼
Repository/DB  db/database.py (sync) o async_db.py  (tenant-scoped)
   ▼
Response  schema Pydantic (api/schemas.py) → JSON
```

Osservabilità trasversale: Sentry (errori), Prometheus (metriche), OpenTelemetry/Zipkin (tracing).

---

## 4. Mappa dei moduli backend (`bike_analyzer/`)

### `core/` — Domain
- `models.py` — `GPSPoint`, `Segment`, `Pause`, `RouteStatistics`, `Ride`, `AthleteProfile`, `CalendarEvent`
- `fitness_state.py` — `TrainingStressDay`, `FitnessStateVector`
- `physics/` — kernel fisico condiviso (forze ciclismo, potenza istantanea)
- `analytics/` — funzioni core (es. `calories.ensure_calories`, `training_stress`)

### `backend/api/` — Presentation
- `app_factory.py` — factory app + middleware + routing
- `routes.py` — router pubblico (`/api/v1`) + `admin_router` (`/api/v1/admin`)
- `bm2_routes.py` — router BM2 (`/api/v1/bm2`)
- `schemas.py` — DTO Pydantic
- `async_db_facade.py`, `utils.py` — helper

### `backend/analytics/` — Application + Domain analitico
- `services/` — `ride_analysis_service`, `fitness_state_service`, `context_builder`
- `repositories/` — accesso dati di dominio (athlete, ride, chat_history, fitness_state, poi, training_stress, user)
- moduli: `analytics`, `advanced`, `power_model`, `calories`, `fatigue`, `training_load`, `training_stress`, `performance`, `benchmark`, `analytics_trends`, `multi_classifier`, `anomaly_detection`, `vip_predictor`, `inactivity_estimator`, `ride_route_estimator`, `granfondo_planner`, `training_plan_generator`, `badges`, `dashboard`, `knowledge_base`, `ai_coach`
- Vedi [engines-and-analytics.md](./engines-and-analytics.md).

### `backend/bm2/` → in realtà `bike_analyzer/bm2/` — Simulation Engine
- `units.py`, `transformer.py`, `models.py`, `algorithms/`, `orchestrator.py`, `simulation.py`, `knowledge.py`, `agents.py`, `adapters.py`
- Vedi [engines-and-analytics.md](./engines-and-analytics.md) e [domain-models.md](./domain-models.md).

### `backend/db/` — Infrastructure (persistenza)
- `database.py` (sync SQLite, sorgente DDL), `async_db.py` (async PG/SQLite), `postgres_db.py` (ORM leggero), `models.py` (ORM async), `migrations.py`, `vector_db.py`, `api_compat.py`
- Vedi [database-schema.md](./database-schema.md).

### `backend/ingestion/` — Import GPS & provider
- `gps_parser.py` — parsing GPX/FIT
- `strava_client.py`, `garmin_client.py`, `wahoo_client.py`
- `google_fit.py`, `google_health.py`, `google_oauth_store.py`

### `backend/auth/` — Autenticazione
- `google_auth.py` — Google OAuth2 (login)
- JWT e verifica: `backend/security.py`

### `backend/maps/` — Rendering mappe
- `map_renderer.py`, `google_maps.py`, `osm_maps.py`, `serpapi_maps.py`, `aethermap_adapter.py`

### `backend/traffic/` — Sicurezza stradale
- `safety_analyzer.py` — risk score (0-1), pesi tipo strada, bonus infrastruttura ciclabile, penalità incidenti/km
- `overpass_client.py` — query OpenStreetMap (Overpass)
- `incident_fetcher.py` — dati incidenti d'area

### `backend/weather/`
- `weather_service.py` — meteo + cache (`weather_cache`)

### `backend/events/`
- Event bus di dominio (RideCreated, BadgeEarned, ecc.)

### Moduli trasversali (`backend/`)
- `security.py` (JWT), `rate_limiter.py` (slowapi), `redis_client.py` (cache + fallback in-memory), `task_queue.py` (task async), `audit.py`/`audit_log.py` (audit), `monitoring.py`/`observability.py`/`tracing.py` (Sentry, Prometheus, OpenTelemetry), `logging_config.py`, `settings.py`

---

## 5. Frontend (`frontend/`)

SPA Vue 3 + Vite 5 + TypeScript + Pinia + Vue Router 4. Dettaglio in [frontend.md](./frontend.md).

- **23 route** (`router/index.ts`): `/`, `/rides`, `/import`, `/athlete`, `/coach`, `/knowledge`, `/bm2`, `/calendar`, `/granfondo`, `/map`, `/pois`, `/aethermap`, `/comparison`, `/heatmap`, `/badges`, `/weather`, `/admin`, `/track`, e pagine legali (`/privacy`, `/terms`, `/cookies`, `/about`, `/contact`).
- **Stores Pinia:** `auth.ts`, `trackingStore.ts`, `ui.ts`.
- **Client API:** `utils/api.ts` (apiGet/apiPost/apiPut/apiDelete/apiUpload).
- **Mobile:** Android via Capacitor (`plugins/bikeTracking.ts` → `BikeTrackingPlugin.kt`), PWA via `vite-plugin-pwa`.

---

## 6. Integrazioni esterne

| Servizio | Modulo | Flusso |
|---|---|---|
| **Strava** | `ingestion/strava_client.py` | OAuth2 + PKCE, sync batch, token in `strava_tokens` con auto-refresh |
| **Garmin Connect** | `ingestion/garmin_client.py` | OAuth2, sync multi-sport, token in `garmin_tokens` |
| **Wahoo Fitness** | `ingestion/wahoo_client.py` | OAuth2, import attività |
| **Google Fit / Health** | `ingestion/google_fit.py`, `google_health.py` | OAuth2, import attività ciclismo |
| **Google Maps / OSM** | `maps/google_maps.py`, `osm_maps.py` | Mappe statiche, geocoding Nominatim |
| **Overpass (OSM)** | `traffic/overpass_client.py` | Tipi strada e infrastrutture ciclabili |
| **Groq (LLM)** | `analytics/ai_coach.py` | AI Coach + RAG |
| **Redis** | `redis_client.py` | Cache (fallback in-memory) |

Endpoint corrispondenti: vedi [api-reference.md](./api-reference.md) sezioni 2, 4, 10, 11, 13.

---

## 7. Sicurezza

- **Autenticazione:** JWT HS256 (`security.py`), scadenza `ACCESS_TOKEN_EXPIRE_MINUTES`, claim `iss`/`aud`, rotazione via `SECRET_KEY_PREVIOUS`.
- **Rate limiting:** per-IP, proxy-aware (`rate_limiter.py`), limiti dedicati su login/register.
- **CORS:** origini esplicite; wildcard vietata in produzione.
- **OAuth redirect:** allow-list di host/schemi (`OAUTH_ALLOWED_REDIRECT_HOSTS`, `OAUTH_REDIRECT_SCHEMES`); l'header Origin non è mai fidato (anti open-redirect).
- **Multi-tenant:** colonna `tenant_id` e query tenant-scoped.
- **Audit:** `audit.py` / `audit_log.py`.
- **Nota admin:** gli endpoint sotto `/api/v1/admin` non hanno `get_current_user` sui singoli handler — proteggerli a livello di rete/reverse proxy o aggiungere un controllo ruolo (vedi [api-reference.md §15](./api-reference.md#15-admin-apiv1admin)).

---

## 8. Osservabilità

| Aspetto | Strumento | Config |
|---|---|---|
| Errori | Sentry | `SENTRY_DSN`, `SENTRY_*` |
| Metriche | Prometheus (`MetricsMiddleware`) + Grafana/Alertmanager | `prometheus/` |
| Tracing | OpenTelemetry → Zipkin/OTLP | `OTEL_*` |
| Logging | `logging_config.py` | strutturato |

---

## 9. Persistenza & migrazioni

- **Dev:** SQLite (`DB_PATH`), schema da `db/database.py:init_db()`.
- **Prod:** PostgreSQL async (`DATABASE_URL`, `asyncpg`), + PGVector per la RAG.
- **Migrazioni:** Alembic (`alembic/versions/`), eseguite all'avvio se `DATABASE_URL` è impostata.
- Dettaglio completo e discrepanze note: [database-schema.md](./database-schema.md).

---

## Riferimenti

- API: [api-reference.md](./api-reference.md)
- Schema DB: [database-schema.md](./database-schema.md)
- Modelli: [domain-models.md](./domain-models.md)
- Config: [configuration.md](./configuration.md)
- Engine & analytics: [engines-and-analytics.md](./engines-and-analytics.md)
- Frontend: [frontend.md](./frontend.md)
