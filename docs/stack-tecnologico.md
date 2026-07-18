# BikeMaster — Stack Tecnologico

Documento che descrive le tecnologie informatiche alla base di BikeMaster,
un sistema di *intelligenza dello stile di vita*: definisce lo stato di salute come il bilanciamento dinamico delle variabili acquisite dalla vita reale.

**Architettura:** local-first, desktop-first (Tauri 2). Il device è la sorgente di verità.

---

## 1. Desktop & Frontend

### Platform
- **Tauri 2** (Rust + WebView) — distribuzione primaria (`.exe`/`.dmg`/`.AppImage`)
- **Vue 3** con Composition API — framework UI reattivo inside Tauri WebView
- **TypeScript** — typing statico (`strict: true`)
- **Vue Router 4** — routing lato client
- **Pinia** — state management

### Build e bundling
- **Vite 5** — dev server e bundler
- **vite-plugin-pwa** — Progressive Web App con service worker custom
  - Caching strategico per `/api`, immagini e dati delle uscite
  - Supporto offline per utenti web-only

### Librerie UI e visualizzazione
- **Chart.js** — grafici (andamenti, potenza, frequenza cardiaca, ecc.)
- **Leaflet** + **leaflet.heat** — mappe interattive e heatmap dei percorsi
- **DOMPurify** — sanitizzazione HTML per prevenire XSS
- **Google Fonts** (Inter, Outfit) — tipografia

### Mobile
- **Capacitor 5** — wrapper per app Android nativa
  - Plugin custom `BikeTracking` per GPS in background
  - Target: Android API 24-34
- **iOS** — Swift plugin (`BikeTrackingPlugin.swift`) + Capacitor config

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
- **Groq SDK** — unico provider LLM attivo (inferenza ad alta velocità)
- **sentence-transformers** — embedding di testo (locale)
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

- **SQLite** — primario, locale su ogni device (Tauri desktop, mobile)
  - **aiosqlite** — driver asincrono
- **PostgreSQL** — opzionale, cloud-only per sync/community features
  - **psycopg2** (sync) e **asyncpg** (async) — driver
  - **pgvector** — estensione per vettori (embedding AI)
- **SQLAlchemy 2.x** — ORM con supporto async
- **Alembic** — migration database
- **PGVector / TF-IDF** — vector store per knowledge base AI (RAG BM25 + cosine similarity)

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

### Distribuzione desktop (primaria)
- **Tauri 2** — wrapper desktop Rust + WebView
  - Bundle nativi: `.exe` (Windows), `.dmg` (macOS), `.AppImage` (Linux)
  - Backend FastAPI embedded + SQLite locale
  - CI/CD: GitHub Actions → Tauri build → GitHub Releases

### Containerizzazione
- **Docker** multi-stage:
  - Stage 1: `node:22-alpine` — build frontend
  - Stage 2: `python:3.11-slim` — produzione backend
  - Utente non-root `bikemaster`
  - Healthcheck su `/api/v1/health`

### Hosting cloud (opzionale)
- **Render** — piattaforma di deployment cloud
  - Docker web service + PostgreSQL gestito
  - Auto-scaling, HTTPS gestito

### CI/CD
- **GitHub Actions**:
  - Test Python (pytest + coverage)
  - Lint Python (ruff + mypy)
  - Build frontend (Node 20)
  - Security scan (Trivy → SARIF → CodeQL)
  - Build Docker
  - Release APK Android (tag `mobile-*`)
  - Build Tauri desktop

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
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT                                   │
│  Tauri 2 Desktop (Rust+WebView) │ Vue 3 SPA │ Capacitor (mobile)│
│  PWA (browser-only)                                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTPS /api/v1
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (embedded in Tauri)                │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐       │
│  │   Auth    │ │   Rides    │ │   AI     │ │   BM2    │       │
│  │ (JWT/OAuth│ │ (CRUD/Imp) │ │ (RAG/ML) │ │(Simul.)  │       │
│  └───────────┘ └────────────┘ └──────────┘ └──────────┘       │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Ingest    │ │  Analysis  │ │Monitor   │ │ Territory│       │
│  │(FIT/GPX/  │ │ (pandas/   │ │(Prom/    │ │(Safety/  │       │
│  │ OAuth)    │ │  sklearn)   │ │ Grafana) │ │ Maps)    │       │
│  └───────────┘ └────────────┘ └──────────┘ └──────────┘       │
└──────────────────────────┬───────────────────────────────────────┘
                           │
        ┌──────────────────┼───────────────────┐
        ▼                  ▼                   ▼
┌──────────┐      ┌──────────────┐    ┌──────────┐
│ SQLite   │      │  Redis (opz) │    │ PGVector  │
│ (locale,  │      │  (cache +    │    │ (cloud,   │
│ primario) │      │   sessioni)  │    │  opzionale│
└──────────┘      └──────────────┘    └──────────┘
```

> **Nota:** PostgreSQL è opzionale e usato solo per cloud sync/community features. SQLite è il database primario su ogni device.

---

## 7. AetherMap (R&D separato)

`aethermap/` è un progetto R&D indipendente — motore cartografico "dal nulla":
- **Stack condiviso:** Vue 3 + FastAPI (stesso framework, codice separato)
- **Tecnologie:** cube-sphere + S2/H3, WebGL rendering, digital twin, pipeline IA "ricercatore"
- **Fasi:** 1 (earth model) → 2 (data model) → {3 AI, 4 rendering} → 5 (digital twin)
- **Nessun accoppiamento** con il backend BikeMaster

---

## 7. Note tecniche rilevanti

- **Race condition risolta** nel router guard: sincronizzazione `localStorage` → Pinia prima della valutazione auth
- **Build Windows EPERM**: gestito con retry wrapper (`scripts/build.mjs`) + esclusione Defender
- **Service worker caching** su `/api`: richiede invalidazione cache per dati freschi sulle rides
- **Multi-provider AI**: configurabile (`groq`) con fallback locale
- **Key rotation JWT**: supporto `SECRET_KEY_PREVIOUS` per rotazione senza logout massivo
- **Sicurezza Docker**: `read_only`, `no-new-privileges`, tmpfs noexec

---

*Documento generato localmente — non condividerlo.*
