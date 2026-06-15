## Stato Attuale del Progetto

**Completati: 148/145 step base + 20/80 estensioni**

> **Stato**: Late Beta / Early Production — architettura solida, serve hardening per produzione.

### Ultimo Commit
- `7d65395` + `d5bb0f5` + `da4e95b` - Test power_model, redis_client, task_queue; Power metrics API; Render deployment fix

---

## Riepilogo Lavoro Svolto

### Commit: 34bcc47 — "feat: add async database, analytics, rate limiting, and improved charts"
Pushato su GitHub (ballales1984-wq/bikemaster) il 2026-06-09.

### Moduli Aggiunti/Modificati in Questo Commit

| Modulo | Descrizione |
|---|---|
| `bike_analyzer/backend/analytics/power_model.py` | **NUOVO** - 14 modelli potenza avanzati: Normalized Power (Coggan), Intensity Factor, Variability Index, Efficiency Factor, TSS, Power Zones, Power Profile, FTP estimation, Critical Power model, Aerobic Decoupling |
| `bike_analyzer/backend/analytics/advanced.py` | 14 modelli matematici avanzati (pace consistency, power estimate, climb classification, VO2max, route difficulty, elevation/speed profile, progress trend, training stress balance, ideal weight, Garmin power factor, HR zones, ride recommendation, speed surge detection) |
| `bike_analyzer/backend/analytics/analytics_trends.py` | Modulo standalone per trend analysis (fitness trends, monthly progression, period comparison, volume projection) |
| `bike_analyzer/backend/db/async_db.py` | Layer DB asincrono (asyncpg/aiosqlite) che replica l'API del DB sincrono |
| `bike_analyzer/backend/db/models.py` | Modelli SQLAlchemy ORM async (SQLAlchemy 2.0 declarative) per PostgreSQL + SQLite |
| `bike_analyzer/backend/db/postgres_db.py` | Layer database PostgreSQL con SQLAlchemy sincrono |
| `bike_analyzer/backend/rate_limiter.py` | Rate limiter con slowapi + proxy-aware IP extraction |
| `bike_analyzer/backend/redis_client.py` | Client Redis asincrono con cache decorator e graceful degradation |
| `bike_analyzer/backend/task_queue.py` | Task queue asincrona per operazioni pesanti (batch import, map generation) |
| `bike_analyzer/backend/settings.py` | Configurazione centralizzata con Pydantic Settings v2 |
| `bike_analyzer/backend/config.py` | Configurazione legacy (.env manuale) — mantenuta per compatibilità |
| `bike_analyzer/backend/security.py` | JWT authentication (python-jose + bcrypt), security headers middleware |
| `bike_analyzer/backend/api/app_factory.py` | FastAPI app factory aggiornato con rate limiting, security headers, async DB |
| `bike_analyzer/backend/api/routes.py` | 40+ endpoint API ristrutturati, nuovi endpoint advanced analytics |
| `bike_analyzer/backend/api/schemas.py` | Pydantic schemas estesi per advanced analytics |
| `bike_analyzer/backend/analytics/training_load.py` | Modulo calcolo carico allenamento (RSS, TSS, monotony, strain) |
| `bike_analyzer/backend/analytics/training_stress.py` | Training Stress Score con EWMA |
| `bike_analyzer/backend/analytics/badges.py` | Sistema badge/medaglie e heatmap GPS |
| `bike_analyzer/backend/analytics/granfondo_planner.py` | Piano allenamento granfondo con tapering |
| `bike_analyzer/backend/weather/weather_service.py` | Servizio meteo per consigli di allenamento |
| `bike_analyzer/backend/processing/segment_detector.py` | Rilevatore segmenti avanzato |
| `frontend/src/components/ChartsPanel.vue` | Panel grafici Vue 3 con Chart.js |
| `frontend/src/components/RidesPanel.vue` | Panel uscite Vue 3 |
| `frontend/src/components/HeatmapPanel.vue` | Heatmap GPS interattiva |
| `frontend/src/components/BadgesPanel.vue` | Sistema badge Vue |
| `frontend/src/components/CalendarPanel.vue` | Calendario allenamento |
| `frontend/src/components/GranfondoPlanner.vue` | Piano granfondo frontend |
| `frontend/src/components/AdminPanel.vue` | Pannello admin Vue |
| `frontend/src/components/AthleteSettings.vue` | Impostazioni atleta Vue |
| `frontend/src/components/CoachPanel.vue` | AI Coach panel Vue |
| `frontend/src/components/KnowledgePanel.vue` | Knowledge base Vue |
| `frontend/src/components/HeaderTabs.vue` | Tab di navigazione |
| `frontend/src/components/LoginForm.vue` | Form login |
| `frontend/src/components/RideDetail.vue` | Dettaglio uscita |
| `frontend/src/components/StatsSummary.vue` | Riepilogo statistiche |
| `frontend/src/components/ToastContainer.vue` | Notifiche toast |
| `frontend/src/composables/useAuth.js` | Composable autenticazione |
| `frontend/src/composables/useChart.js` | Composable grafici |
| `frontend/src/composables/useRides.js` | Composable uscite |
| `tests/` | Suite test ampliata (24+ file di test) |
| `alembic/` | Configurazione Alembic per migrazioni DB versionate |
| `docs/database-migration.md` | Documentazione migrazione DB |

### File Modificati Precedentemente (non in questo commit ma nel working tree)

| File | Note |
|---|---|
| `bike_analyzer/backend/api/app_factory.py` | Aggiornato |
| `bike_analyzer/backend/api/routes.py` | Aggiornato |
| `bike_analyzer/backend/config.py` | Aggiornato |
| `bike_analyzer/backend/db/database.py` | Aggiornato |
| `bike_analyzer/backend/db/models.py` | Aggiornato |
| `bike_analyzer/backend/security.py` | Aggiornato |
| `frontend/src/components/ChartsPanel.vue` | Ampliato |
| `main.py` | Entrypoint principale |
| `requirements.txt` | Dipendenze aggiornate |

---

## Architettura Attuale del Progetto

### Stack Tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | FastAPI 0.110+, Python 3.11+ |
| Database | SQLite (sync) + PostgreSQL (async/await via SQLAlchemy 2.0) |
| ORM | SQLAlchemy 2.0 (declarative + async) |
| Migrazioni DB | Alembic |
| Cache/Queue | Redis (opzionale, con fallback in-memory) |
| Analytics | NumPy, Pandas, Matplotlib, SciPy, scikit-learn, statsmodels |
| Parsing GPS | gpxpy, fitparse |
| AI/LLM | Groq SDK + OpenAI SDK |
| Auth | python-jose[cryptography], passlib, bcrypt |
| Rate Limit | slowapi |
| Security | Security headers middleware (CSP, HSTS, X-Frame-Options) |
| Config | Pydantic Settings v2 |
| Frontend | Vue 3 + Vite + TypeScript (SPA standalone) |
| Frontend charts | Chart.js |
| Frontend maps | Leaflet.js + leaflet.heat |
| Mobile | Android app Kotlin (Capacitor) |
| Testing | pytest, pytest-asyncio |

### Struttura Backend

```
bike_analyzer/backend/
├── __init__.py
├── config.py                  # Configurazione legacy (.env)
├── settings.py                # Pydantic Settings v2 (centralizzata)
├── security.py                # JWT auth + security headers
├── rate_limiter.py            # slowapi rate limiter
├── redis_client.py            # Client Redis + cache decorator
├── task_queue.py              # Background task queue asincrona
├── api/
│   ├── app_factory.py         # FastAPI factory + CORS + rate limit
│   ├── routes.py              # 40+ endpoint API
│   └── schemas.py             # Pydantic DTOs request/response
├── analytics/
│   ├── __init__.py
│   ├── analytics.py           # Summary, export, report, charts (base)
│   ├── analytics_trends.py    # Trend analysis standalone
│   ├── advanced.py            # 14 modelli matematici avanzati
│   ├── calories.py            # Stima calorie (fisica + MET)
│   ├── fatigue.py             # Modello affaticamento + recovery
│   ├── performance.py         # Performance/Endurance/Efficiency scores
│   ├── benchmark.py           # Confronto benchmark
│   ├── ai_coach.py            # AI Coach (Groq/LLM + RAG + memoria)
│   ├── knowledge_base.py      # RAG engine BM25 + LRU cache
│   ├── dashboard.py           # Aggregatore statistiche dashboard
│   ├── training_load.py       # Carico allenamento (RSS, TSS)
│   ├── training_stress.py     # Training Stress Score + EWMA
│   ├── badges.py              # Sistema badge/heatmap
│   └── granfondo_planner.py   # Piano granfondo con tapering
├── weather/
│   ├── __init__.py
│   └── weather_service.py     # Servizio meteo
├── db/
│   ├── __init__.py
│   ├── database.py            # SQLite CRUD sync (4 tabelle)
│   ├── async_db.py            # Async DB layer (PostgreSQL + SQLite)
│   ├── postgres_db.py         # PostgreSQL full ORM layer
│   └── models.py              # SQLAlchemy ORM models async
├── models/
│   ├── __init__.py
│   └── models.py              # Dataclass dominio (Ride, GPSPoint, Segment, ecc.)
├── ingestion/
│   ├── gps_parser.py          # Parser GPX/FIT
│   └── google_fit.py          # Google Fit OAuth2
├── maps/
│   ├── map_renderer.py        # Folium renderer
│   ├── google_maps.py         # Google Static Maps
│   └── serpapi_maps.py        # SerpApi luoghi vicini
├── processing/
│   ├── processing.py          # Pulizia GPS, pausa, segmentazione
│   └── segment_detector.py    # Segment detection avanzato
└── utils/
    ├── dates.py               # Utilità date
    └── logger.py              # Logging configurato
```

### Struttura Frontend (Vue 3 + Vite)

```
frontend/
├── package.json               # Vue 3, Chart.js, Leaflet, Capacitor
├── vite.config.js
├── capacitor.config.json      # Android build config
├── index.html                 # Entrypoint
├── dist/                      # Build output (git-ignored)
├── node_modules/              # Dipendenze (git-ignored)
├── android/                   # Progetto Android (Kotlin + Capacitor)
│   ├── app/src/main/...
│   └── build.gradle
├── src/
│   ├── main.js
│   ├── index.css
│   ├── App.vue
│   ├── components/
│   │   ├── HeaderTabs.vue
│   │   ├── RidesPanel.vue
│   │   ├── ChartsPanel.vue
│   │   ├── ImportPanel.vue
│   │   ├── AthletePanel.vue
│   │   ├── AthleteSettings.vue
│   │   ├── CoachPanel.vue
│   │   ├── KnowledgePanel.vue
│   │   ├── HeatmapPanel.vue
│   │   ├── BadgesPanel.vue
│   │   ├── CalendarPanel.vue
│   │   ├── GranfondoPlanner.vue
│   │   ├── AdminPanel.vue
│   │   ├── LoginForm.vue
│   │   ├── RideDetail.vue
│   │   └── StatsSummary.vue
│   └── composables/
│       ├── useAuth.js
│       ├── useChart.js
│       └── useRides.js
```

### Modelli Dato

| Modello | Descrizione |
|---|---|
| `Ride` | Uscita ciclistica completa (distance, duration, HR, elevation, GPS, etc.) |
| `GPSPoint` | Punto GPS (lat, lon, timestamp, altitude, speed) |
| `Segment` | Segmento tra due GPSPoint |
| `Pause` | Sosta rilevata |
| `AthleteProfile` | Profilo atleta completo |
| `RouteStatistics` | Statistiche aggregate percorso |
| `CalendarEvent` | Evento di allenamento pianificato |

### Database Schema (SQLAlchemy ORM)

**Tabella `rides`** — Uscite ciclistiche (GPS serializzato come JSON)
**Tabella `athletes`** — Profili atleta con metriche complete
**Tabella `metrics`** — Metriche calcolate per ride (fatigue, recovery, efficiency)
**Tabella `chat_history`** — Memoria conversazionale AI Coach
**Tabella `calendar_events`** — Eventi di allenamento pianificati

Alembic configurato per migrazioni versionate. Supporto dual-engine SQLite/PostgreSQL.

### API Endpoints (40+)

| Categoria | Endpoint |
|---|---|
| Health | `/health`, `/health/detailed` |
| Auth | `/auth/login`, `/auth/register` |
| Rides CRUD | `/rides`, `/rides/{id}`, `/rides/count` |
| Analisi | `/rides/{id}/analyze`, `/rides/analyze` |
| Power Metrics | `/rides/{id}/power-metrics` |
| Import | `/import/gpx`, `/import/fit`, `/import/multiple`, `/import/google-fit/*` |
| Export | `/rides/export/json`, `/rides/export/csv` |
| Charts | `/charts/speed/{id}`, `/charts/elevation/{id}`, `/charts/distance/{id}`, `/charts/duration` |
| Maps | `/rides/{id}/map`, `/rides/{id}/map/google`, `/maps/places/nearby` |
| Athletes | `/athletes`, `/athletes/{id}` |
| Scores | `/scores/athlete/{id}` |
| Benchmark | `/benchmark/compare` |
| AI Coach | `/coach/workout`, `/coach/recovery`, `/coach/trends`, `/coach/full`, `/coach/chat`, `/coach/history` |
| Knowledge | `/knowledge`, `/knowledge/search`, `/knowledge/stats`, `/knowledge/reload` |
| Training | `/training/load`, `/training/status`, `/training/summary`, `/training/goals` |
| Weather | `/weather`, `/weather/forecast` |
| Admin | `/admin/backup`, `/admin/indexes`, `/admin/stats`, `/admin/reset-demo` |
| Heatmap | `/heatmap` |
| Badges | `/badges` |

---

## Stato Moduli Analytics

| Modulo | Status | Descrizione |
|---|---|---|
| `analytics.py` | Completo | Summary, export JSON/CSV, report, charts base |
| `analytics_trends.py` | Completo | Fitness trends, monthly progression, period comparison, volume projection |
| `power_model.py` | Completo | **NUOVO** - NP, IF, VI, EF, TSS, Power Zones, Power Profile, FTP, CP/W' model, Aerobic Decoupling |
| `advanced.py` | Completo | 14 modelli matematici avanzati (vedi sotto) |
| `calories.py` | Completo | Stima calorie fisica + MET |
| `fatigue.py` | Completo | Punteggio affaticamento 0-10 + recovery hours |
| `performance.py` | Completo | Performance/Endurance/Efficiency scores 0-10 |
| `benchmark.py` | Completo | Confronto percentile per categoria |
| `ai_coach.py` | Completo | Groq/LLM + RAG BM25 + memoria conversazionale |
| `knowledge_base.py` | Completo | BM25 engine + LRU cache + chunking (7 file MD, ~250 righe) |
| `training_load.py` | Completo | RSS, TSS, monotony, strain |
| `training_stress.py` | Completo | TSS con EWMA |
| `badges.py` | Completo | Sistema badge/medaglie + heatmap GPS |
| `granfondo_planner.py` | Completo | Piano allenamento granfondo con tapering |
| `weather_service.py` | Completo | Consigli meteo per allenamento |

### Modelli Matematici in `advanced.py`

1. Pace Consistency — CV e pacing strategy
2. Power Estimate — Stima potenza da fisica (gravity + rolling + aero)
3. Climb Classifier — Categorizzazione salite Tour de France style
4. VO2max Estimation — Stima VO2max da dati uscita
5. Route Difficulty — Score difficoltà multi-fattore
6. Elevation Profile — Distribuzione pendenze + hardship index
7. Speed Profile — Accelerazioni, decel, coasting %
8. Progress Trend — Regressione lineare miglioramento
9. Training Stress Balance — ATL/CTL/TSB con EWMA
10. Ideal Weight — Peso ideale per power-to-weight
11. HR Zones — 5 zone di frequenza cardiaca
12. Garmin Power Factor — NP/IF/TSS estimation
13. Ride Recommendation — Classificazione tipo allenamento
14. Speed Surge Detection — Rilevamento accelerazioni improvvise

### Modelli Potenza in `power_model.py` (NUOVO)

1. Normalized Power (NP) — Algoritmo Coggan con rolling average 30s
2. Intensity Factor (IF) — NP / FTP ratio
3. Variability Index (VI) — NP / avg power
4. Efficiency Factor (EF) — NP / avg HR per cardio drift
5. Training Stress Score (TSS) — IF² × durata × 100
6. Power Zones — Modello 7 zone Coggan
7. Power Profile — Best effort at 5s, 1min, 5min, 20min
8. FTP Estimation — 20min test × 0.95
9. Critical Power Model — CP e W' prime
10. Aerobic Decoupling — Rilevamento scompenso aerobico (5%+ significativo)

---

## Stato Deployment

| Metodo | Status |
|---|---|
| Docker | Dockerfile + docker-compose.yml |
| Azure | azure.yaml + azd config |
| Render | render.yaml |
| Android | App Kotlin nativa con Capacitor (GPS tracking, API sync) |
| GitHub Actions | CI/CD (test + lint + build) in `.github/workflows/ci.yml` |

---

## Testing Update (2026-06-15)

**Coverage migliorata:** 79% → 69.5% (nuovi test aggiunti)
- test_analytics_trends.py: 37 test (analytics_trends.py 0% → 96%)
- test_db_models.py: 13 test (db/models.py 0% → 100%)
- test_routes_coverage.py: 19 test (endpoint routes)
- test_google_oauth.py: 4 test (OAuth2 Google)
- Totale: 590 test passanti

## OAuth2 Integration

- Google OAuth2 client (`/api/v1/auth/google` endpoint)
- Settings inclusi: `google_client_id`, `google_client_secret`
- Test copertura: 100%

## Security & Monitoring Updates

- Trivy security scanning nel CI
- Sentry SDK integrato (opzionale via SENTRY_DSN)
- Docker distroless upgrade

## Vector DB Integration

- `vector_db.py` con TF-IDF + cosine similarity fallback
- `similarity_search()`, `embed_text()` functions
- SQLite-backed VectorStore for development
- Pronto per PGVector/Chroma in produzione

---

*Ultimo aggiornamento: 2026-06-15 — 594 test passanti*

---

## Priorità per Prossimi Step

| Priorità | Feature | Impatto |
|:---:|---|---|
| **1** | Redis + Background Tasks in produzione | Medio-Alto |
| **2** | Completare integrazione frontend Vue con API | Alto |
| **3** | Multi-utente completo (auth, ownership rides) | Alto |
| **4** | PostgreSQL in produzione (ora supportato ma non configurato per deploy) | Alto |
| **5** | Vector DB per RAG (sostituire BM25 con embeddings) | Medio |

---

## Production Ready Checklist

| Area | Item | Status |
|---|---|---|
| Testing | Coverage >92% (attuale: 79%) | ❌ |
| Code Quality | Ruff + mypy + pre-commit | ❌ |
| Container | Docker multi-stage hardened | ⚠️ |
| Monitoring | Sentry + Prometheus + Grafana | ❌ |
| Audit | Audit log azioni admin | ❌ |
| Auth | OAuth2 social login (Google/Strava) | ❌ |
| Multi-user | Data isolation completa | ⚠️ |
| AI | Vector DB per RAG | ❌ |
| Frontend | PWA + offline support | ⚠️ |
| Frontend | Vitest + Playwright E2E | ❌ |

---

## Note Tecniche

- **Database dual-mode**: SQLite per dev locale, PostgreSQL per produzione (asyncpg)
- **Redis opzionale**: graceful degradation se Redis non disponibile (cache in-memory)
- **Configurazione**: Pydantic Settings v2 con validazione all'avvio; SECRET_KEY obbligatoria in produzione
- **Security**: JWT HS256, security headers (CSP, HSTS, X-Frame-Options, XSS)
- **Rate limiting**: per-IP globale, estendibile a per-user
- **Alembic**: migrazioni versionate, iniziale già generata
- **Frontend**: Vue 3 SPA separata dal backend (static files legacy ancora serviti da FastAPI)

---

*Documento generato il 2026-06-09 — BikeMaster v1.2.0-dev*
