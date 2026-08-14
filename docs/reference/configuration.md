# Configurazione — Variabili d'Ambiente

Tutte le impostazioni sono definite in `bike_analyzer/backend/settings.py` (`Settings`, Pydantic Settings v2) e caricate da variabili d'ambiente o dal file `.env` (case-insensitive). L'accesso avviene tramite il singleton `get_settings()`.

Copia `.env.example` in `.env` e configura i valori necessari.

```bash
cp .env.example .env
```

> Le variabili d'ambiente hanno lo **stesso nome del campo in maiuscolo** (es. campo `groq_api_key` → env `GROQ_API_KEY`).

---

## Ambiente

| Env | Default | Descrizione |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` / `production` / `prod` / `staging` / `test` |

## Database

| Env | Default | Descrizione |
|---|---|---|
| `DB_PATH` | `rides.db` | Percorso SQLite (dev) |
| `DATABASE_URL` | `""` | Connessione async (PostgreSQL in prod). Se vuota in prod → warning e fallback su SQLite |

> Validazione: in `production/prod/staging` senza `DATABASE_URL` viene loggato un warning (fallback SQLite).

## API Server

| Env | Default | Descrizione |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Host di ascolto (necessario per Docker) |
 | `API_PORT` | `8001` | Porta |

## CORS & OAuth redirect

| Env | Default | Descrizione |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:8001,...:8080,127.0.0.1:...` | Origini consentite (CSV). Wildcard `*` vietata in produzione |
| `OAUTH_REDIRECT_SCHEMES` | `com.bikemaster.app` | Schemi URI custom consentiti come redirect OAuth (deep link mobile) |
| `OAUTH_ALLOWED_REDIRECT_HOSTS` | `""` | Host http/https extra consentiti come redirect_uri (l'header Origin non è mai fidato) |

## Sicurezza / JWT

| Env | Default | Descrizione |
|---|---|---|
| `SECRET_KEY` | `""` | **Obbligatoria in produzione** (≥32 caratteri, es. `openssl rand -hex 32`). Valori placeholder → il processo termina in prod |
| `SECRET_KEY_PREVIOUS` | `""` | Chiave precedente per la rotazione |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Scadenza access token |
| `JWT_ISSUER` | `bikemaster` | Claim `iss` |
| `JWT_AUDIENCE` | `bikemaster` | Claim `aud` |

## AI Coach

| Env | Default | Descrizione |
|---|---|---|
| `AI_COACH_MODE` | `external` | Modalità coach |
| `AI_COACH_CHAT_RETENTION_DAYS` | `90` | Retention storico chat |
| `GROQ_API_KEY` | `""` | **Richiesta per l'AI Coach** |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Modello LLM Groq |

## Knowledge Base

| Env | Default | Descrizione |
|---|---|---|
| `KB_PATH` | `<repo>/knowledge_base` | Cartella dei documenti KB |

Gli embeddings usano `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dim) se installato, altrimenti fallback TF-IDF/BM25.

## Google (Maps / OAuth / Fit / Health)

| Env | Default | Descrizione |
|---|---|---|
| `GOOGLE_MAPS_API_KEY` | `""` | Mappe statiche (opzionale) |
| `GOOGLE_MAPS_ZOOM` | `13` | Zoom mappe |
| `GOOGLE_MAPS_SIZE` | `800x600` | Dimensione mappe |
| `SERPAPI_API_KEY` | `""` | SerpApi — arricchimento POI a budget (vedi sotto) |
| `SERPAPI_ENGINE` | `google_maps` | Engine SerpApi |
| `SERPAPI_BASE_URL` | `https://serpapi.com/search` | |
| `SERPAPI_MONTHLY_BUDGET` | `250` | Max ricerche SerpApi/mese (salvaguardia free-tier) |
| `NOMINATIM_BASE_URL` | `https://nominatim.openstreetmap.org` | Geocoding OSM |
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth2 (login) |
| `GOOGLE_CLIENT_SECRET` | `""` | Google OAuth2 |
| `GOOGLE_FIT_CLIENT_ID` | `""` | Google Fit (fallback al client generico) |
| `GOOGLE_FIT_CLIENT_SECRET` | `""` | |
| `GOOGLE_FIT_SCOPE` | `fitness.activity.read + fitness.location.read` | Scope Fit |
| `GOOGLE_HEALTH_CLIENT_ID` | `""` | Google Health |
| `GOOGLE_HEALTH_CLIENT_SECRET` | `""` | |
| `GOOGLE_HEALTH_SCOPE` | `googlehealth.activity.read + location.read` | Scope Health |

### Arricchimento POI (SerpApi)

Il provider live di default per la ricerca luoghi è **OpenStreetMap** (`osm_maps.py`,
keyless). SerpApi è invece usato come fonte di **arricchimento a budget** del
database mappa: il modulo `maps/poi_enrichment.py` converte i risultati SerpApi
in righe `pois` persistite, entro un tetto mensile di ricerche.

- `enrich_pois_near(lat, lon, query=...)` esegue **al più una** ricerca SerpApi,
  deduplica contro i POI vicini esistenti e salva i nuovi (taggati
  `source:serpapi`).
- Il consumo è tracciato per mese solare nella tabella `serpapi_usage` (creata
  automaticamente) e limitato da `SERPAPI_MONTHLY_BUDGET`; a budget esaurito
  l'arricchimento si ferma.
- Le categorie SerpApi sono mappate sui tipi POI ammessi
  (`vista, fontana, ristoro, bivio, pericolo, culturale, tecnico`).

## Strava

| Env | Default |
|---|---|
| `STRAVA_CLIENT_ID` | `""` |
| `STRAVA_CLIENT_SECRET` | `""` |
| `STRAVA_REDIRECT_URI` | `http://localhost:8001/api/v1/import/strava/callback` |
| `STRAVA_SCOPE` | `activity:read_all` |

> Il path del redirect URI deve corrispondere esattamente, incluso `/import/`.

## Garmin

| Env | Default |
|---|---|
| `GARMIN_CONSUMER_KEY` | `""` |
| `GARMIN_CONSUMER_SECRET` | `""` |
| `GARMIN_REDIRECT_URI` | `http://localhost:8001/api/v1/import/garmin/callback` |
| `GARMIN_SCOPE` | `read` |

## Wahoo

| Env | Default |
|---|---|
| `WAHOO_CLIENT_ID` | `""` |
| `WAHOO_CLIENT_SECRET` | `""` |
| `WAHOO_REDIRECT_URI` | `http://localhost:8001/api/v1/integrations/wahoo/callback` |
| `WAHOO_SCOPE` | `workouts_read user_read` |

## Weather

| Env | Default | Descrizione |
|---|---|---|
| `WEATHER_API_KEY` | `""` | Chiave provider meteo |
| `WEATHER_CACHE_HOURS` | `6` | TTL cache meteo |
| `WEATHER_UNITS` | `metric` | Unità |

## Traffic / Road Safety

| Env | Default | Descrizione |
|---|---|---|
| `INCIDENT_DATA_PATH` | `""` | File dati incidenti locale |
| `INCIDENT_API_URL` | `""` | API incidenti |
| `INCIDENT_API_KEY` | `""` | |
| `INCIDENT_RADIUS_KM` | `5.0` | Raggio di ricerca |
| `INCIDENT_DAYS` | `90` | Finestra temporale |

## Redis / Cache

| Env | Default | Descrizione |
|---|---|---|
| `REDIS_URL` | `""` | URL Redis (fallback in-memory se vuoto) |
| `REDIS_CACHE_TTL_SECONDS` | `300` | TTL cache |

## Background Tasks

| Env | Default | Descrizione |
|---|---|---|
| `TASK_QUEUE_WORKERS` | `2` | Worker della coda async |

## Analytics — soglie e pesi

| Env | Default | Descrizione |
|---|---|---|
| `MAX_SPEED_KM_H` | `120.0` | Filtro velocità anomale |
| `PAUSE_SPEED_THRESHOLD` | `1.5` | Soglia velocità pausa (km/h) |
| `PAUSE_DURATION_THRESHOLD_S` | `180.0` | Durata minima pausa (s) |
| `ACCELERATION_THRESHOLD` | `2.0` | Soglia accelerazione |
| `CALORIE_EFFICIENCY_FACTOR` | `0.25` | Efficienza meccanica |
| `CALORIE_BENCHMARK_KCAL_KM` | `30.0` | Benchmark kcal/km |
| `FATIGUE_WEIGHT_DURATION` | `0.30` | Peso durata nel fatigue score |
| `FATIGUE_WEIGHT_HR` | `0.30` | Peso FC |
| `FATIGUE_WEIGHT_SPEED` | `0.20` | Peso velocità |
| `FATIGUE_WEIGHT_ELEVATION` | `0.10` | Peso dislivello |
| `FATIGUE_WEIGHT_WEIGHT` | `0.10` | Peso corporeo |

## Osservabilità

### Sentry

| Env | Default |
|---|---|
| `SENTRY_DSN` | `""` |
| `SENTRY_ENVIRONMENT` | `development` |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.2` |
| `SENTRY_PROFILES_SAMPLE_RATE` | `0.1` |

### OpenTelemetry / Tracing

| Env | Default |
|---|---|
| `OTEL_SERVICE_NAME` | `bikemaster` |
| `OTEL_EXPORTER_ZIPKIN_ENDPOINT` | `http://localhost:9411/api/v2/spans` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` |
| `OTEL_TRACES_SAMPLER` | `parentbased_traceidratio` |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` |
| `OTEL_ENVIRONMENT` | `development` |

## Mappe

| Env | Default | Descrizione |
|---|---|---|
| `DEFAULT_MAP_STYLE` | `standard` | Stile mappa di default |

## Migrazioni all'avvio

| Env | Default | Descrizione |
|---|---|---|
| `RUN_MIGRATIONS_ON_STARTUP` | attivo | Esegue `alembic upgrade head` all'avvio (solo se `DATABASE_URL` è impostata) — vedi `db/migrations.py` |

---

## Esempio `.env` minimale (sviluppo)

```env
ENVIRONMENT=development
DB_PATH=rides.db
API_HOST=0.0.0.0
API_PORT=8001
SECRET_KEY=dev-only-change-me-please-32-chars-min
GROQ_API_KEY=your_key_here
```

## Esempio `.env` produzione (estratto)

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/bikemaster
SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://app.tuodominio.it
REDIS_URL=redis://redis:6379/0
GROQ_API_KEY=...
SENTRY_DSN=...
```
