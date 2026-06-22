# Changelog

Tutte le modifiche significative a questo progetto sono documentate in questo file.

## [1.4.0] - 2026-06-22

### Aggiunte
- **Clean Architecture** — Core domain layer (models, pipeline, engine, fitness_state)
- **Calculators/Services/Repositories** — Analytics scomposto in 3 layer Clean Architecture
- **Domain Events** — Event bus pub/sub (RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated)
- **Traffic Safety Module** — Risk score computation + Overpass client + incident fetcher
- **Strava Integration** — OAuth2 + PKCE + batch import + token auto-refresh
- **Garmin Connect Integration** — OAuth2 + activity fetch + normalization
- **Vector Database** — PGVector wrapper + TF-IDF fallback for RAG
- **Google OAuth2 Auth** — `/auth/google` + `/auth/google/callback` endpoints
- **Docker Hardened** — Multi-stage build, non-root user, read-only filesystem, security scan
- **CI/CD Avanzato** — GitHub Actions: ruff + mypy + Trivy scan + Codecov
- **51+ Test Files** — ~600 test passanti (unit, integration, API, error paths, coverage gaps)
- **Playwright E2E** — Suite E2E configurata (7 spec files)
- **Vitest** — Frontend unit test framework configurato
- **PWA Install Prompt** — Componente `PWAInstallPrompt.vue`
- **Error Boundary** — `ErrorBoundary.vue` + `ErrorState.vue` per gestione errori
- **Frontend Modern** — Vue 3 + Vite + TypeScript + Pinia + Router + Composables
- **Repository Pattern** — RideRepository, AthleteRepository, FitnessStateRepository (sync + async)
- **Async Database** — SQLAlchemy 2.0 async (asyncpg/aiosqlite) con API facade
- **Traffic Safety API** — `/traffic/analyze`, `/traffic/bike-lanes`, `/traffic/road-data`
- **Power Model** — 10 metriche potenza (NP, IF, VI, EF, TSS, FTP, CP, Power Zones, Decoupling)
- **14 Modelli Avanzati** — In `advanced.py` (VO2max, climb, pace, elevation, speed, ecc.)
- **Security Headers** — CSP, HSTS, X-Frame-Options, X-XSS-Protection
- **Rate Limiting** — slowapi per-IP con proxy-aware extraction

### Modificati
- Refactor completo analytics in calculators/services/repositories
- Frontend convertito a Vue 3 + Vite + TypeScript (da HTML/JS)
- Dockerfile multi-stage con security hardening
- CI workflow con security scan Trivy + Codecov upload
- Configurazione Pydantic Settings v2 estesa (Strava, Garmin, Weather, OAuth)

### Documentazione
- README.md completamente riscritto con architettura aggiornata
- ROADMAP.md aggiornato (148/145 base + 45/80 estensioni)
- PROJECT_STATUS.md ristrutturato con dettaglio moduli
- docs/DEVELOPMENT.md aggiornato con Clean Architecture pattern
- docs/API_DOCS.md aggiornato con tutti gli endpoint (auth, traffic, Strava, Garmin)

### Roadmap
- **51 file di test**, ~600 test passanti
- Coverage: ~69-79%

---

## [1.3.0] - 2026-06-18

### Aggiunte
- **Phone GPS Tracking** - Registrazione uscite direttamente dal telefono mobile
- `BikeTrackingService.kt` - Foreground service Android con GPS persistente
- `BikeTrackingPlugin.kt` - Plugin Capacitor per bridge nativo
- `trackingStore.ts` - Store Pinia con stato reattivo tracking
- `RideTracking.vue` - Pagina Vue con mappa Leaflet live
- Scrittura GPX incrementale in background
- Supporto sensori BLE (HR, Cadence, Power)
- Documentazione `docs/PHONE_TRACKING.md`

### Route
- Aggiunta `/track` per pagina di tracciamento GPS

### Android Manifest
- Aggiunti permessi: `ACCESS_BACKGROUND_LOCATION`, `FOREGROUND_SERVICE_LOCATION`, `ACTIVITY_RECOGNITION`, `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`

### Frontend
- Pulsante "Traccia Uscita" nella dashboard
- Store Pinia `trackingStore.ts` per stato tracking
- Componenti metriche live in tempo reale

---

## [1.2.0] - 2026-06-08

### Fixati
- Risolti 2 test falliti in `test_api_coverage.py`: aggiunti endpoint `/health/detailed` e `/coach/history` nel backend
- Tutti i 293 test passano

### Aggiunte
- Nuovo modulo `training_stress.py` con TSS (Training Stress Score) e EWMA
- Nuovo modulo `badges.py` con sistema di badge/medaglie e heatmap GPS
- Nuovo modulo `granfondo_planner.py` per piani di allenamento granfondo con tapering
- Nuovo modulo `weather/weather_service.py` per punteggio e consigli meteo
- Nuovi test: `test_training_stress.py`, `test_badges.py`, `test_granfondo.py`, `test_weather.py`, `test_processing.py`
- Nuovi endpoint API: `/training/load`, `/training/status`, `/training/summary`, `/training/goals`, `/training/workouts/generate`, `/training/granfondo/plan`, `/weather`, `/weather/forecast`, `/heatmap`, `/badges`
- Componente Vue `useAuth.js` composable per autenticazione frontend

### Roadmap
- **143/145 passi completati** (mancano solo 2 step opzionali)

### Fixati
- Corretto test `test_benchmark_categories`: weight 60kg è "Lightweight", non "Medium"
- Aggiunta migrazione automatica colonna `goals` nello schema database `athletes`

### Aggiunte
- Test Google Maps mock (`test_google_maps_mock.py`)
- Test scores API (`test_scores_api.py`)
- Test benchmark API (`test_benchmark_api.py`)
- Test knowledge base (`test_knowledge_api.py`)
- Test database backup (`test_database_backup.py`)
- Test batch import (`test_import_batch.py`)
- Test athlete profile (`test_athlete_profile.py`)

**Test coverage: 79 test passanti**

## [1.0.0] - 2026-06-05

### Aggiunte
- API REST con 40+ endpoint per gestione rides e analytics
- Parser GPX e FIT per importazione file GPS
- Integrazione Google Fit OAuth2
- Mappe interattive con Folium e Google Static Maps
- Grafici velocità, elevazione, distanza, durata
- Sistema di punteggi (performance, endurance, efficiency, fatigue)
- AI Coach con raccomandazioni allenamento e recupero
- Knowledge base con contenuti training/recovery/cardio
- Database SQLite con backup integrato
- Dashboard web dark-themed
- Supporto Docker e Docker Compose
- Deployment Azure con azd
- Test automatici (pytest)

### Analytics
- Calcolo distanza totale con formula haversine
- Rilevamento pause e fermate
- Analisi accelerazioni/rallentamenti
- Segmentazione percorsi
- Stima calorie (fisico + MET)
- Punteggio affaticamento con formula pesata
- Stime ore recupero post-allenamento

### API Endpoints Principali
- `/api/v1/rides/*` — CRUD rides
- `/api/v1/import/*` — Importazione GPX/FIT/Google Fit
- `/api/v1/export/*` — Esportazione JSON/CSV
- `/api/v1/charts/*` — Grafici immagine
- `/api/v1/athletes/*` — Gestione profili atleta
- `/api/v1/scores/*` — Punteggi performance
- `/api/v1/benchmark/*` — Confronto atleti
- `/api/v1/coach/*` — AI recommendations
- `/api/v1/knowledge/*` — Knowledge base

## [0.2.0] - 2026-05-01

### Aggiunte
- Modello dati Ride con GPSPoint
- Parser file GPX base
- Database SQLite con tabella rides
- Analytics base (distanza, velocità, tempo)

## [0.1.0] - 2026-04-01

### Aggiunte
- Struttura progetto iniziale
- README e configurazione
- Setup environment Python
- Primi script di importazione