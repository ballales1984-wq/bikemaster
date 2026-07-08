# BikeMaster — Stack Tecnologico

Documento personale che descrive le tecnologie informatiche alla base di BikeMaster,
un'applicazione per l'analisi e il tracking di uscite ciclistiche.

---

## 1. Frontend

### Framework e linguaggio
- **Vue 3** con Composition API — framework UI reattivo
- **TypeScript** — typing statico (`strict: true`)
- **Vue Router 4** — routing lato client
- **Pinia** — state management

### Build e bundling
- **Vite 5** — dev server e bundler
- **vite-plugin-pwa** — Progressive Web App con service worker custom (`src/sw.js`)
  - Caching strategico per `/api`, immagini e dati delle uscite
  - Supporto offline e aggiornamento automatico

### Librerie UI e visualizzazione
- **Chart.js** — grafici (andamenti, potenza, frequenza cardiaca, ecc.)
- **Leaflet** + **leaflet.heat** — mappe interattive e heatmap dei percorsi
- **DOMPurify** — sanitizzazione HTML per prevenire XSS
- **Google Fonts** (Inter, Outfit) — tipografia

### Mobile
- **Capacitor 5** — wrapper per app Android nativa
  - Plugin custom `BikeTracking` per GPS in background
  - Notifiche push e locali
  - Target: Android API 24-34

### Testing
- **Vitest** — test unitari con jsdom
- **@vue/test-utils** — testing di componenti Vue
- **Playwright** — test E2E (Chrome, Firefox, mobile)

### Qualita codice
- **ESLint** + plugin Vue — linting
- **vue-tsc** — type checking di file `.vue`
- **Prettier** — formatting

---

## 2. Backend

### Linguaggio e runtime
- **Python 3.11** — linguaggio principale
- **Uvicorn** — server ASGI

### Web framework
- **FastAPI** — framework API asincrono con prefisso `/api/v1`
- **Pydantic v2** — validazione e modelli dati
- **python-multipart** — parsing form-urlencoded (login)

### Analisi dati e ML
- **pandas / numpy / scipy** — manipolazione e analisi dati
- **scikit-learn** — modelli ML (classificazione, previsioni)
- **statsmodels** — modelli statistici
- **matplotlib** — generazione grafici lato server
- **folium** — mappe (fallback OSM)

### AI e Knowledge Base
- **OpenAI SDK** — provider LLM (anche compatibile con Ollama)
- **Groq SDK** — inferenza LLM ad alta velocita
- **sentence-transformers** — embedding di testo
- **ChromaDB** — vector database per RAG (Retrieval-Augmented Generation)
- **AI Coach** — sistema di coaching ciclistico con RAG

### Ingestione dati
- **fitparse** — parsing file FIT (Garmin, Wahoo)
- **gpxpy** — parsing file GPX
- Client OAuth per **Strava**, **Garmin**, **Wahoo**, **Google Fit**
- **google-auth** — autenticazione Google OAuth

### Caching e messaging
- **Redis** — caching, rate limiting, blacklist JWT, refresh token, TOTP secrets

---

## 3. Database

- **PostgreSQL** — produzione (Render)
  - **psycopg2** (sync) e **asyncpg** (async) — driver
  - **pgvector** — estensione per vettori (embedding AI)
- **SQLite** — sviluppo locale
  - **aiosqlite** — driver asincrono
- **SQLAlchemy 2.x** — ORM con supporto async
- **Alembic** — migration database
- **ChromaDB** — vector store per knowledge base AI

---

## 4. Autenticazione e Sicurezza

- **JWT** (python-jose + cryptography) — token di accesso (30 min) e refresh (30 giorni)
  - Algoritmo HS256, key rotation supportato
- **bcrypt** — hashing password
- **OAuth2PasswordBearer** — scheme autenticazione
- **Cookie HTTP-only** — `bikemaster_access` e `bikemaster_refresh` (sicuri, same-site)
- **Redis JWT blacklist** — revoca token al logout
- **Refresh token rotation** — max 5 attivi per utente
- **TOTP / 2FA** — autenticazione a due fattori (implementazione custom)
- **Google OAuth** — login social
- **Rate limiting** (slowapi) — protezione brute-force:
  - Login: 5 req/min
  - Registrazione: 3 req/min
  - OAuth: 10 req/min
  - Rides: 10 req/min
- **DOMPurify** (frontend) — sanitizzazione input utente

---

## 5. DevOps e Deployment

### Containerizzazione
- **Docker** multi-stage:
  - Stage 1: `node:22-alpine` — build frontend
  - Stage 2: `python:3.11-slim` — produzione backend
  - Utente non-root `bikemaster`
  - Healthcheck su `/api/v1/health`

### Hosting
- **Render** — piattaforma di deployment
  - Docker web service + PostgreSQL gestito
  - Auto-scaling, HTTPS gestito

### CI/CD
- **GitHub Actions**:
  - Test Python (pytest + coverage → Codecov)
  - Lint Python (ruff + mypy)
  - Build frontend (Node 20)
  - Security scan (Trivy → SARIF → CodeQL)
  - Build Docker
  - Release APK Android (tag `mobile-*`)

### Code quality (Python)
- **Ruff** — linting veloce
- **Mypy** — type checking
- **pytest** + **pytest-asyncio** + **pytest-cov** — testing

### Osservabilita
- **Prometheus** + **prometheus-fastapi-instrumentator** — metriche (`/metrics`)
- **Grafana** — dashboard (datasource Prometheus, dashboard preconfigurate)
- **Alertmanager** — alerting su soglie
- **OpenTelemetry** — distributed tracing (gRPC OTLP → Zipkin)
- **Sentry** — error monitoring e APM

### Git hooks
- **Lefthook** — pre-commit: typecheck, eslint, unit tests

---

## 6. Architettura generale

```
┌─────────────────────────────────────────────┐
│                  CLIENT                      │
│  Vue 3 + TypeScript + Vite + PWA            │
│  Capacitor (Android app)                     │
└──────────────────┬──────────────────────────┘
                   │ HTTPS /api/v1
                   ▼
┌─────────────────────────────────────────────┐
│              FASTAPI BACKEND                 │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ │
│  │   Auth    │ │   Rides    │ │   AI     │ │
│  │ (JWT/OAuth│ │ (CRUD/Imp) │ │ (RAG/ML) │ │
│  └───────────┘ └────────────┘ └──────────┘ │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Ingest    │ │  Analysis  │ │ Monitoring│ │
│  │(FIT/GPX/  │ │ (pandas/   │ │(Prom/    │ │
│  │ OAuth)    │ │  sklearn)   │ │ Grafana) │ │
│  └───────────┘ └────────────┘ └──────────┘ │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│PostgreSQL│ │  Redis   │ │ ChromaDB │
│(dati +   │ │(cache +  │ │(vector   │
│ pgvector)│ │ sessioni)│ │ store)   │
└──────────┘ └──────────┘ └──────────┘
```

---

## 7. Note tecniche rilevanti

- **Race condition risolta** nel router guard: sincronizzazione `localStorage` → Pinia prima della valutazione auth
- **Build Windows EPERM**: gestito con retry wrapper (`scripts/build.mjs`) + esclusione Defender
- **Service worker caching** su `/api`: richiede invalidazione cache per dati freschi sulle rides
- **Multi-provider AI**: configurabile (`groq,openai`) con fallback
- **Key rotation JWT**: supporto `SECRET_KEY_PREVIOUS` per rotazione senza logout massivo
- **Sicurezza Docker**: `read_only`, `no-new-privileges`, tmpfs noexec

---

*Documento generato localmente — non condividerlo.*
