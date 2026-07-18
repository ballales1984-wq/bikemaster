# Resoconto Progetto BikeMaster

**Data:** 2026-07-18  
**Versione:** 1.5.0  
**Stato:** Architettura locale-first completata — distribuzione primaria desktop Tauri 2

---

## 1. Riepilogo Esecutivo

BikeMaster è un sistema di **intelligenza dello stile di vita** che definisce lo stato di salute come il bilanciamento dinamico delle variabili acquisite dalla vita reale di ogni persona. L'attività ciclistica funge da dominio strutturato per analisi, raccomandazioni e ottimizzazione.

Il progetto è attualmente in fase avanzata di sviluppo, con architettura **local-first** basata su **Tauri 2** (desktop), **FastAPI** (backend embedded) e **SQLite** (database primario). Include un motore di simulazione sportiva interno (BM2), un progetto R&D cartografico indipendente (AetherMap) e supporto per sync cloud opzionale.

---

## 2. Visione e Missione

### Missione ufficiale

Il programma definisce lo stato di salute come il bilanciamento delle variabili acquisite dal tuo stile di vita. Tu scegli cosa mangiare, il sistema analizza, consiglia la quantità compatibile, propone micro-correzioni e calcola la quantità giusta di movimento per mantenere l'equilibrio.

### Le VAR — firma metabolica

| VAR | Descrizione |
|:---|:---|
| **Energia** | Livello energetico disponibile |
| **Macronutrienti** | Bilanciamento proteine/carboidrati/grassi |
| **Acqua_totale** | Idratazione giornaliera |
| **Glicemia** | Controllo glicemico |
| **VO2** | Capacità cardio-respiratoria |
| **Respirazione** | Efficienza respiratoria |
| **Battito** | Frequenza cardiaca a riposo e sotto sforzo |
| **Orario** | Ritmi circadiani e tempistiche |
| **Storico** | Andamento nel tempo |
| **Stato_generale** | Percezione soggettiva del benessere |

### Ciclo operativo giornaliero

1. **Analizza** ciò che scegli di mangiare
2. **Consiglia** la quantità compatibile
3. **Propone** micro-correzioni intelligenti
4. **Calcola** la quantità giusta di movimento
5. **Bilancia** le VAR per riportare in equilibrio

---

## 3. Architettura del Sistema

### Pattern: Clean Architecture

```
Presentation      API (FastAPI) · Frontend Vue · Android/iOS (Capacitor) · Tauri 2 (desktop)
        │
Application       Use cases: StartSession, PromoteSession, ImportActivity,
                  AnalyzeActivity, SyncHealth, CoachAdvise, PlanTraining
        │
Domain            Entities + UnifiedMetricsEngine (pure calculation logic)
        │
Infrastructure    Repositories · Ingestion (Strava/Garmin/Fit/GPX) ·
                  Tracking · Maps · Weather · Traffic · VectorDB
```

### Piattaforma primaria (effective 2026-07-15)

- **Desktop:** Tauri 2 (Rust + WebView) — distribuzione primaria `.exe`/`.dmg`/`.AppImage`
- **Frontend:** Vue 3 + Vite + TypeScript — bundle inside Tauri WebView
- **Backend:** FastAPI embedded — `localhost` nel device
- **Database:** SQLite (primario, locale) + PostgreSQL (opzionale, cloud hub)
- **Mobile:** Android (Capacitor + Kotlin) · iOS (Capacitor, in valutazione)
- **Web:** PWA per utenti browser-only

### Modularità

Il backend è separato in due moduli:
- **Modulo locale** (default): FastAPI + SQLite, gira su `localhost` nel device
- **Modulo hub** (opzionale): FastAPI + PostgreSQL multi-tenant, per sync e community

L'utente può attivare la modalità **"Mai"** (mai sync) e usare l'app 100% offline.

---

## 4. Stack Tecnologico

### Backend

| Layer | Tecnologia |
|:---|:---|
| Framework | FastAPI 0.110+ (embedded) o Axum (Rust) — Tauri 2 desktop app |
| Core/Domain | Python dataclasses, Clean Architecture |
| Database | SQLite (primario, locale) + PostgreSQL (opzionale, cloud hub) |
| ORM | SQLAlchemy 2.0 (declarative + async) |
| Migrations | Alembic |
| Vector DB | PGVector (cosine similarity search, solo cloud) |
| Cache | SQLite-based o Redis locale |
| Analytics | NumPy, Pandas, Matplotlib, SciPy, scikit-learn, statsmodels, endurance-metrics |
| Parsing GPS | gpxpy, fitparse |
| AI/LLM | Groq SDK + embeddings locali (sentence-transformers) |
| Auth | python-jose[cryptography], passlib, bcrypt, Google OAuth2 |
| Rate Limit | slowapi (proxy-aware IP) |
| Security | CSP, HSTS, X-Frame-Options, XSS, Referrer-Policy, Permissions-Policy |
| Config | Pydantic Settings v2 |
| Testing | pytest, pytest-asyncio, Playwright |

### Frontend

| Layer | Tecnologia |
|:---|:---|
| Framework | Vue 3 (Composition API + `<script setup>`) |
| Language | TypeScript (`strict: true`) |
| Build | Vite 5 |
| State | Pinia |
| Router | Vue Router 4 |
| Charts | Chart.js |
| Maps | Leaflet (+ heatmap plugin) |
| PWA | vite-plugin-pwa + custom `sw.js` |
| Mobile | Capacitor 5 (Android + iOS) |
| Testing | Vitest (unit) + Playwright (E2E) |
| Lint/Typecheck | ESLint + vue-tsc |

---

## 5. Componenti Principali

### Backend (`bike_analyzer/backend/`)

| Modulo | Ruolo |
|:---|:---|
| `api/` | FastAPI Presentation Layer — routes, schemas, app factory |
| `analytics/` | Analytics Engine (Clean Architecture) — 14 modelli avanzati, power metrics, fatigue, AI Coach |
| `db/` | Data Access Layer — SQLite sync, async SQLAlchemy, PostgreSQL ORM |
| `database/` | Vector DB — PGVector wrapper per similarity search |
| `auth/` | Authentication providers — Google OAuth2, Strava, Garmin |
| `ingestion/` | Data Ingestion — GPX/FIT parser, Google Fit, Strava, Garmin, Wahoo |
| `maps/` | Map Rendering — Folium, Google Static Maps, OSM, SerpApi |
| `traffic/` | Traffic & road safety analysis — Overpass API, incident data |
| `weather/` | Weather service — consigli meteo per allenamento |
| `event_bus.py` | Domain event bus — pub/sub per RideCreated, BadgeEarned, ecc. |
| `security.py` | JWT auth + security headers |
| `rate_limiter.py` | slowapi rate limiter proxy-aware |
| `redis_client.py` | Async Redis client + cache decorator |
| `task_queue.py` | Background tasks asincrone |
| `audit_log.py` | Admin audit log (JSONL) |

### Frontend (`frontend/`)

- **Router** — Vue Router con guard auth e sync localStorage
- **Pinia Stores** — `auth.ts`, `ui.ts`, `trackingStore.ts`
- **Composables** — `useAuth.ts`, `useChart.ts`, `useRides.ts`, `usePWA.ts`, `useI18n.ts`
- **Plugin Capacitor** — `bikeTracking.ts` per native Android features
- **Error Boundaries** — `ErrorBoundary.vue` + `ErrorState.vue`
- **PWA** — Service worker + `PWAInstallPrompt.vue`
- **Componenti principali** — 35+ componenti Vue (HeaderTabs, RidesPanel, ChartsPanel, ImportPanel, AthletePanel, CoachPanel, KnowledgePanel, HeatmapPanel, BadgesPanel, CalendarPanel, GranfondoPlanner, AdminPanel, LoginForm, RideDetail, RideMapPanel, SpeedMap, StatsSummary, WeatherPanel, DashboardPanel, RidesView, ToastContainer, ErrorBoundary, ConfirmModal, LiveMap, PWAInstallPrompt)

---

## 6. BikeMaster 2.0 — Simulation Engine

BM2 è il **motore di simulazione sportiva** interno ("what-if") con filosofia type-safe.

### Architettura

| Modulo | Ruolo |
|:---|:---|
| `bm2/units.py` | `Quantity` + `UnitRegistry` — analisi dimensionale lineare/non-lineare |
| `bm2/models.py` | `AnalysisContext`, `Athlete`, `Bike`, `WorldObject`, `Activity` |
| `bm2/algorithms/` | 9 algoritmi — Movement, Energy, Power, Fatigue, Performance, Recovery, Nutrition, RouteDifficulty, TrainingLoad |
| `bm2/simulation.py` | `SimulationEngine` — compare/preset/sensitivity analysis |
| `bm2/orchestrator.py` | `AIOrchestrator` + agenti per domande in linguaggio naturale |
| `bm2/transformer.py` | `TransformerEngine` — geo → metric points |
| `bm2_routes.py` | Endpoint API esposti in FastAPI |

### Algoritmi

| Algoritmo | Output |
|:---|:---|
| MovementModel | avg/max speed, acceleration (m/s) |
| EnergyModel | Calorie (kcal) |
| PowerModel | Potenza stimata/sostenibile (W) |
| FatigueModel | Fatigue score + recovery hours (0-10) |
| PerformanceModel | Normalized performance index (score) |
| RouteDifficultyModel | Route difficulty score (0-100) |
| RecoveryModel | Readiness score (0-100) |
| NutritionModel | Carbs, water, proteins (g/L) |
| TrainingLoadModel | TSS, CTL, ATL, TSB (score) |

### Integrazione

- Baseline completo e testato (`test_bm2_*`)
- Integrato col flusso Ride/analytics esistente via `bm2/adapters.py`
- Validato contro potenza misurata via `core/physics/validation.py`

---

## 7. AetherMap — Progetto R&D

Progetto cartografico indipendente in `aethermap/` — motore "dal nulla" con:

- **Earth model:** cube-sphere + S2/H3
- **Data model:** "database del mondo"
- **AI pipeline:** "ricercatore" con confidence e buffer/latenza
- **Rendering:** WebGL con LOD adattivo
- **Digital twin:** oggetti vivi con sintesi Fasi 1-4

Condivide lo stack (Vue + FastAPI) ma **non è importato** dal backend BikeMaster.

### Fasi

| Fase | Status | Descrizione |
|:---|:---|:---|
| 1 | ✅ | Earth model (cube-sphere, coordinate) |
| 2 | ✅ | Data model (classe Oggetto, storage, S2/H3) |
| 3 | 🔄 | AI pipeline "ricercatore" (ingest, proposte con confidence) |
| 4 | ✅ | Rendering (WebGL, camera-relative, LOD) |
| 5 | 🔄 | Digital twin (oggetti vivi, sintesi Fasi 1-4) |

Demo: `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`

---

## 8. Stato del Progetto

### Metriche verificate (2026-07-17)

| Area | Metriche | Stato |
|:---|:---|:---|
| Backend test | ~3255 passed / 2 failed su ~3257 eseguiti | 🟢 Stabile |
| Backend test (collection completa) | 2611 test pass | 🟢 Verde |
| Frontend test | 332 passed / 31 failed / 20 errors su 363 | 🟡 In miglioramento |
| Endpoint REST | 138 endpoint | 🟢 Completo |
| File backend | 108 file test | 🟢 |
| File frontend | 47 file test | 🟢 |

I 2 failure backend sono errori d'ambiente SQLAlchemy async (`MissingGreenlet`) in `test_ai_coach_helpers.py` e `test_athlete_state_integration.py`, non bug di logica.

### Branch aperti (da mergiare)

| Branch | Contenuto | Azione |
|:---|:---|:---|
| `feat/local-auth` | Local auth handlers, OAuth flow Tauri, dev port 5177 | **Mergiare** |
| `feat/auth-sync-ui` | UI sync settings, auth sync frontend | Mergiare dopo local-auth |
| `feat/local-sync` | Sync locale ↔ cloud, modelli DB sync, Alembic migrations | Mergiare dopo auth-sync-ui |

### Priorità assoluta

1. Merge dei 3 branch in sequenza
2. Commit working tree oppure reset se duplicato
3. Run test completo backend + frontend
4. Pulizia repo (file temporanei, cache, backup DB)

---

## 9. Funzionalità Implementate

### Core

- [x] GPS Ingestion — GPX/FIT parsing
- [x] Route Analysis — distance, speed, elevation, accelerations, pause detection
- [x] Calorie Estimation — physics + MET
- [x] Fatigue Scoring — 0-10 weighted score
- [x] Interactive Maps — Folium/Leaflet speed-colored routes
- [x] Knowledge Base — RAG con BM25 + PGVector
- [x] AI Coach — Groq + LLM + RAG + memoria conversazionale
- [x] Phone GPS Tracking — Android + iOS (Capacitor)
- [x] Traffic Safety Analysis — Overpass API + incident data
- [x] Event Bus — pub/sub domain events
- [x] PWA — install prompt + offline support
- [x] Multi-tenant — data isolation completa (tenant_id)
- [x] PostgreSQL dual-mode — SQLite/PostgreSQL switchabile

### Integrazioni

- [x] Strava — OAuth2 + PKCE + batch import
- [x] Garmin Connect — OAuth2 + activity fetch
- [x] Wahoo Fitness — activity import
- [x] Google Fit — OAuth2 + cycling import
- [x] Google Maps — static maps + elevation
- [x] Google OAuth2 — social login

### Analytics

- [x] 14 modelli matematici avanzati
- [x] Power Metrics — NP, IF, VI, EF, TSS, CP, FTP, decoupling
- [x] Training Load — TSS, ATL/CTL/TSB, EWMA
- [x] Granfondo Planner — tapering incluso
- [x] Badge System — medaglie + heatmap GPS
- [x] Benchmark — confronto percentile per categoria

### Sicurezza e Monitoring

- [x] JWT Auth — HS256 con key rotation
- [x] Rate Limiting — slowapi per-IP + proxy-aware
- [x] Security Headers — CSP, HSTS, X-Frame-Options, XSS
- [x] Sentry — error tracking
- [x] Prometheus + Grafana — metrics e dashboard
- [x] OpenTelemetry — distributed tracing
- [x] Docker Hardened — multi-stage, non-root, read-only fs

---

## 10. Modelli Matematici

### `advanced.py` — 14 modelli

1. Pace Consistency — CV e pacing strategy
2. Power Estimate — stima potenza da fisica (gravity + rolling + aero)
3. Climb Classifier — categorizzazione salite Tour de France style
4. VO2max Estimation — stima VO2max da dati uscita
5. Route Difficulty — score difficoltà multi-fattore
6. Elevation Profile — distribuzione pendenze + hardship index
7. Speed Profile — accelerazioni, decel, coasting %
8. Progress Trend — regressione lineare miglioramento
9. Training Stress Balance — ATL/CTL/TSB con EWMA
10. Ideal Weight — peso ideale per power-to-weight
11. HR Zones — 5 zone di frequenza cardiaca
12. Garmin Power Factor — NP/IF/TSS estimation
13. Ride Recommendation — classificazione tipo allenamento
14. Speed Surge Detection — rilevamento accelerazioni improvvise

### `power_model.py` — 10 modelli potenza

1. Normalized Power (NP)
2. Intensity Factor (IF)
3. Variability Index (VI)
4. Efficiency Factor (EF)
5. Training Stress Score (TSS)
6. Power Zones (Coggan 7-zone)
7. Power Profile — best efforts 5s/1min/5min/20min
8. FTP Estimation — 20min test × 0.95
9. Critical Power / W′
10. Aerobic Decoupling — 5%+ threshold

---

## 11. Integrazioni Esterne

### OAuth2

- **Google OAuth2** — `/auth/google` + `/auth/google/callback`
- **Strava OAuth2 + PKCE** — `/import/strava/auth` + `/import/strava/callback`
- **Garmin Connect OAuth2** — client completo con token storage e refresh
- **Google Fit OAuth2** — `/import/google-fit/auth` + `/import/google-fit/token`

### APIs Esterne

- **Strava API** — batch activity import & sync
- **Garmin Connect API** — activity fetch + normalization
- **Google Fit API** — automatic cycling activity import
- **OpenStreetMap Overpass API** — bike lanes e road types
- **OpenWeatherMap** — weather forecast
- **Google Static Maps** — route images
- **SerpApi** — luoghi vicini

---

## 12. Sicurezza e Monitoring

- **Security Headers:** CSP, HSTS, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy
- **JWT Auth:** HS256 con python-jose, bcrypt password hashing, key rotation (`SECRET_KEY` + `SECRET_KEY_PREVIOUS`)
- **Rate Limiting:** slowapi per-IP + proxy-aware (`X-Forwarded-For`)
- **CORS:** origini configurabili, wildcard vietato in produzione
- **Audit Logging:** JSONL persistence, `/admin/audit-logs` endpoint
- **Sentry:** error tracking opzionale via `SENTRY_DSN`
- **Prometheus:** `/metrics` endpoint via `prometheus-fastapi-instrumentator`
- **Grafana:** dashboard provisioning in `docker/`
- **OpenTelemetry:** distributed tracing (gRPC OTLP → Zipkin)
- **Docker Hardened:** multi-stage build, non-root user, read-only fs, no-new-privileges, healthcheck

---

## 13. Deployment

### Metodi supportati

| Metodo | Config | Status |
|:---|:---|:---|
| Docker | `Dockerfile` + `docker-compose.yml` | ✅ Multi-stage hardened |
| GitHub Actions | `.github/workflows/ci.yml` | ✅ Test + lint + security + build |
| GitHub Actions (Android) | `.github/workflows/android-release.yml` | ✅ APK/AAB |
| Render | `render.yaml` + `render-hub.yaml` | ✅ |
| Vercel | `vercel.json` | ✅ Frontend |
| Azure | `azure.yaml` | ✅ |
| Fly.io | `docker/deploy/flyio.md` | 📄 Documentato |
| Railway | `docker/deploy/railway.md` | 📄 Documentato |
| Kubernetes | `docker/helm/bikemaster/` | 📄 Helm chart |

### Desktop (Tauri 2)

```bash
cd frontend && npm run tauri build   # .exe / .dmg / .AppImage
```

### Docker

```bash
docker compose up -d
```

---

## 14. Testing

### Backend

- **~3255 test pass** su ~3257 eseguiti (pytest, in chunk per stabilità)
- **108 file** `test_*.py` nella root legacy + **2611 test** nella collection completa
- **Coverage:** informativa in CI (~82% linee)
- **Target:** >90% su `routes.py` e moduli AI

### Frontend

- **363 test** totali (332 pass / 31 fail / 20 error)
- **Vitest:** unit test su componenti, store, composables
- **Playwright:** E2E spec in `frontend/tests/e2e` (14 file `.spec.js` + 3 `.spec.ts`)
- **Config:** `vitest.config.js` + `playwright.config.js`

### BM2

- Test dedicati: `pytest tests/test_bm2_*.py -v`
- Demo: `cd bike_analyzer && python -m bm2.simulation.demo`

---

## 15. Roadmap e Prossimi Passi

### Completato

- [x] Architettura locale-first Tauri 2 + SQLite primario
- [x] 7 Engine BM2 + 9 algoritmi
- [x] AI Coach (Groq + RAG)
- [x] Import Strava/Garmin/Wahoo/Google Fit
- [x] Phone GPS Tracking (Android + iOS)
- [x] Traffic Safety Analysis
- [x] Multi-tenant + data isolation
- [x] AetherMap (fasi 1-4 baseline)
- [x] 22 fasi di sviluppo completate

### In corso

- [ ] AetherMap fasi 3-5 (AI pipeline + digital twin)
- [ ] Anomaly detection + piano di allenamento LLM
- [ ] Voice Coach (TTS/audio)
- [ ] Merge branch `feat/local-auth`, `feat/auth-sync-ui`, `feat/local-sync`
- [ ] Fix test frontend (31 failed + 20 errors)
- [ ] Fix 2 test backend (MissingGreenlet)
- [ ] Coverage >90% su `routes.py` e moduli AI
- [ ] Documentazione consolidata

### Prossimi 3-6 mesi

1. PostgreSQL in produzione + connection pooling
2. Voice input/output AI Coach + prompt engineering
3. Memoria persistente conversazioni per utente
4. Design System + theme tokens
5. Test coverage >90% come metrica informativa

---

## 16. Struttura Directory

```
D:\BikeMaster/
├── bike_analyzer/          # Backend + BM2 + core (codice Python)
│   ├── backend/            # FastAPI app (api, analytics, db, ingestion, maps...)
│   ├── core/               # Domain layer (models, pipeline, engine, physics)
│   ├── bm2/                # BikeMaster 2.0 simulation engine
│   ├── frontend/           # Dashboard Flask legacy (non il frontend principale)
│   ├── tests/              # Test backend (pytest)
│   └── main.py             # Entrypoint
├── frontend/               # Frontend principale (Vue 3 + Vite + TS)
│   ├── src/
│   │   ├── components/     # Componenti Vue (35+)
│   │   ├── views/          # Page-level views
│   │   ├── stores/         # Pinia stores
│   │   ├── composables/    # Composables
│   │   ├── utils/          # API client, helpers
│   │   ├── services/       # Auth, notifications, Tauri
│   │   ├── types/          # TypeScript types
│   │   └── db/             # Local DB (SQLite WASM)
│   ├── src-tauri/          # Tauri 2 Rust backend
│   └── tests/              # E2E Playwright
├── aethermap/              # R&D cartografia (separato da BikeMaster)
├── docs/                   # Documentazione sviluppatore
│   ├── reference/          # Dizionario dati, schemi
│   └── archive/            # Materiale obsoleto
├── scripts/                # Utility (tauri_agent.py, frontend_aligner.py)
├── tests/                  # Test legacy root (108 file — migrare in bike_analyzer/tests/)
├── android/                # Android Kotlin nativo (Capacitor)
├── knowledge_base/         # Documenti RAG
├── alembic/                # Migrazioni DB
├── docker/                 # Dockerfile + docker-compose
├── .github/workflows/      # CI/CD
├── ROADMAP.md              # Fonte di verità per stato e priorità
├── PROJECT_STATUS.md       # Sintesi stato moduli
├── AGENTS.md               # Istruzioni agenti
├── main.py                 # Entrypoint root (delega a bike_analyzer)
├── pyproject.toml          # Config Python
├── requirements.txt        # Dipendenze Python
├── render.yaml             # Deploy backend Render
├── render-hub.yaml         # Deploy hub Render
└── vercel.json             # Deploy frontend Vercel
```

---

## 17. Conclusioni

BikeMaster è un progetto maturo con architettura solida, test automatizzati estesi e stack tecnologico moderno. L'approccio **local-first** con Tauri 2 + SQLite garantisce privacy, offline capability e performance native. Il motore BM2 e il progetto AetherMap rappresentano asset R&D distintivi. Le priorità immediate sono il merge dei branch in corso, la stabilizzazione dei test frontend e la pulizia del repository.

---

*Documento generato il 2026-07-18. Fonti: README.md, PROJECT_STATUS.md, ROADMAP.md, docs/MASTER.md, main.py.*
