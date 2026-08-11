# BikeMaster — Roadmap Unificata

*Ultimo aggiornamento: 2026-08-11*

> **Principio guida**: fare le cose una volta, farle bene. Questo documento è la
> *fonte di verità unica* per stato, priorità e azioni. Non eseguire feature
> duplicate: verificare qui prima di iniziare qualsiasi lavoro.

---

## 1. Stato Attuale (checklist veloce)

| Area | Stato | Note |
|:--|:--|:--|
| Backend FastAPI | **Stabile** | ~3255/3257 test passati; 2 failure sono MissingGreenlet (ambiente SQLAlchemy async) |
| Frontend Vue 3 | **Stabile** | Lint + typecheck puliti, 395/395 test passati |
| Tauri 2 desktop | **Funzionante** | Backend embedded + SQLite primario, smoke test passed |
| BM2 simulation engine | **Baseline** | 9 algoritmi, cablato via API; UI Deluxe wiring completata |
| AetherMap R&D | **Fasi 1-5 complete** | Convergence completata — modulo terrain intelligence integrato in BikeMaster |
| Multi-tenant / auth | **Completo** | tenant_id + OAuth2 (Google, Strava, Garmin) + hardening produzione |
| Produzione Render | **Stabile** | Auto-deploy da main, PostgreSQL `bikemaster-db`, Redis, health check su porta 10000 |
| Produzione Vercel | **Stabile** | Frontend statico su Vercel, chiama API Render same-origin; `VITE_API_BASE` configurato |
| Coverage test | **In corso** | ai_coach.py 90%, knowledge_base ~85%, routes.py ~65% |
| OAuth produzione | **Hardening completato** | Logging granulare, lock handling, fallback user creation, sslmode Render, CORS regex per preview Vercel |

---

## 2. Branches Aperti (azioni immediate)

Nessun branch aperto. Tutti i branch feat sono stati mergiati in `main`.

---

## 3. Working Tree

- **Branch**: `refactor/split-hotspots`
- **Modified**: `bike_analyzer/backend/analytics/repositories/` (9 file — circular import resolution via lazy imports), `bike_analyzer/backend/db/repositories/calendar_repository.py` (lazy connection import), `bike_analyzer/backend/analytics/training_load.py` (+5 funzioni ATL/CTL/TSB/RSS), `bike_analyzer/backend/api/routers/training_routes.py` (adotta TrainingGoalRepository), `tests/test_database.py` (import spostato)
- **Untracked**: `bike_analyzer/backend/analytics/repositories/training_goal_repository.py` (nuovo repository PostgreSQL/SQLAlchemy), `review_db_architecture.md` (report architetturale)

---

## 4. Priorità Assoluta (ordine di esecuzione)

### Fase 1 — Refactoring database.py (estrazione repository) 🔄 IN CORSO

1. ✅ **Calendar (P1)** — CRUD estratto in `db/repositories/calendar_repository.py`, circular import risolto, `analytics/repositories/calendar_repository.py` rediretto a `db.database`, 53 test passanti
2. ✅ **Training Goals (PostgreSQL)** — `analytics/repositories/training_goal_repository.py` creato come wrapper SQLAlchemy, `training_routes.py` aggiornato
3. ✅ **Circular import resolution** — tutti i repository `analytics/repositories/` convertono import top-level in lazy import dentro i metodi; `db/repositories/calendar_repository.py` ottiene `_get_db_connection()` lazy
4. 🔄 **HR 24h (P2)** — `analytics/repositories/hr_repository.py` convertito a lazy import; `db/repositories/hr_repository.py` non esiste ancora (funzioni ancora inline in `database.py`)
5. 🔄 **Metabolico, Chat, BLE, Legal, POI, Safety** — `analytics/repositories/*` convertiti a lazy import; attesi in `db/repositories/`

### Fase 2 — Stabilizzazione produzione ✅ COMPLETATA (2026-08-10)

6. ✅ **Hardening OAuth Google** — logging granulare callback, lock handling, fallback user creation, sslmode Render PostgreSQL, CORS regex per preview Vercel, security headers (CSP, CORP, CSRF), token encryption, OAuth state validation
7. ✅ **Resilienza PostgreSQL** — schema init robusta, connection close safe, SQLite fallback, schema drift fix, dispatch `get_metrics_by_athlete` su PostgreSQL, idempotent migrations
8. ✅ **Stabilità Render deploy** — deploy timeout risolto (migrations non-blocking, lifespan background tasks, uvicorn porta 10000, Redis fromService, health check `/api/v1/health`, graceful shutdown)
9. ✅ **Vercel deploy** — rimozione cron e framework override, pin Node 20.x, serverless compatibility
10. ✅ **Security hardening** — IDOR fix su POI endpoints, CORS restriction, CSRF tokens, info disclosure fix, rate-limit persistence
11. ✅ **AetherMap convergence** — Fasi 1-5 complete, C++ renderer integrato, CityGML 2.0, Natural Earth packaging, terrain intelligence module (`useRideTerrain`, `terrain_enrichment.py`)
12. ✅ **Frontend UI/UX** — touch targets, SVG icons, skeleton loading, accessibility improvements, PWA manifest icons/screenshots
13. ✅ **Tauri Android** — HealthConnectHelper, BLE sync (weight/HR/blood pressure), Windows build scripts, JDK 17 config

### Fase 3 — Test coverage (in corso)

14. **Coverage > 90%** su `routes.py` e moduli AI — in corso
    - routes.py ~65%, ai_coach.py 90%, knowledge_base ~85%
    - Test Google OAuth callback sistemato (fix settings singleton + env vars)
    - File attivi: `tests/test_routes_error_branches.py`, `tests/test_coverage_ai_routes.py`

### Fase 4 — Distribuzione

15. **Tauri build verificata**: `npm run tauri build` produce .exe/.dmg/.AppImage funzionanti
16. **Vercel deploy**: frontend su Vercel chiama API su Render (`VITE_API_BASE=https://bikemaster.onrender.com`)
17. **GitHub Releases** per distribuzione desktop (CI/CD Tauri)
18. **Android release**: verificare APK/AAB da workflow GitHub Actions

### Fase 5 — BM2 Deluxe (prossimo mese)

19. **UI simulazione frontend**: pannello "What-if" su rides esistenti
    (`components/Bm2Panel.vue` esiste, serve integrazione completa)
20. **Validazione fisica su dati reali**: confrontare stime BM2 vs potenza misurata
    su 10+ ride con power meter
21. **AI Coach + BM2**: l'orchestratore NL usa i risultati simulazione per rispondere
    a domande tipo "se aumento FTP a 250W quanto miglioro?"

### Fase 6 — AetherMap (R&D, completata)

22. ✅ Complete Fase 1-5 (earth model, data model, AI pipeline, WebGL rendering, digital twin)
23. ✅ Decisione esplicita: `aethermap/` converge in BikeMaster come modulo terrain intelligence
24. ✅ Contratto dati `Ride/GPSPoint → terrain input` definito in `docs/agent/aethermap-convergence.md`

> **Decisione (2026-07-26)**: AetherMap converge in BikeMaster. Il progetto rimane come sotto-package (`aethermap/`) con il suo `pyproject.toml` autonomo, ma è integrato come dipendenza opzionale (`pip install -e ".[maps]"`). La pipeline IA arricchisce le ride con dati terrain; il digital twin fornisce contesto ambientale (neve, ombra, traffico) per l'analisi e il coaching. Vedi `docs/agent/aethermap-convergence.md` per dettagli.

---

## 5. Architettura Produzione (deployment attuale)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Vercel)                           │
│  Static build Vue 3 → CDN Vercel                               │
│  Chiama API su Render same-origin                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────────┐
│                     Backend (Render)                            │
│  FastAPI/Docker — auto-deploy da main                          │
│  Porta 10000 — health check Render                              │
│  PostgreSQL `bikemaster-db` (managed)                           │
│  Redis `bikemaster-redis` (managed)                             │
│  Static frontend servito same-origin (fallback)                 │
└─────────────────────────────────────────────────────────────────┘

Locale:
  Tauri 2 desktop → backend embedded FastAPI (localhost) + SQLite
  PWA → backend FastAPI (localhost:8000) + SQLite
```

> **Nota**: il modello legacy local-backend + ngrok→Vercel è ritirato. Render è
> la fonte di verità per il backend produzione (`render.yaml`). Vercel è la
> fonte di verità per il frontend produzione.

---

## 6. Regole Anti-Duplicazione

- **Prima di scrivere codice**: cercare nel repo (`grep`, `codebase_search`) per
  verificare che la feature non esista già sotto altro nome
- **Prima di creare un branch**: verificare che non esista un branch con lo stesso
  scopo; riutilizzare o estendere quello esistente
- **Documentazione**: una sola fonte di verità per ogni argomento. Se `ROADMAP.md`
  copre lo stato, non replicarlo in `PROJECT_STATUS.md`
- **Script**: se `scripts/tauri_agent.py` esiste, non creare `scripts/build-tauri.sh`
- **Modelli DB**: se `bike_analyzer/backend/db/models.py` esiste, non creare
  `backend/models.py` ex-novo — estendere quello esistente

---

## 7. Struttura Directory (canone attuale)

```
D:\BikeMaster/
├── bike_analyzer/          # Backend + BM2 + core (codice Python)
│   ├── backend/            # FastAPI app (api, analytics, db, ingestion, maps...)
│   │   ├── analytics/      # Analytics engine + repositories (19 file)
│   │   │   ├── repositories/  # Domain repositories (dual-mode sync/async)
│   │   │   │   ├── athlete_repository.py
│   │   │   │   ├── ride_repository.py
│   │   │   │   ├── training_stress_repository.py
│   │   │   │   ├── training_goal_repository.py  # PostgreSQL/SQLAlchemy wrapper
│   │   │   │   ├── calendar_repository.py
│   │   │   │   ├── hr_repository.py
│   │   │   │   ├── metabolism_repository.py
│   │   │   │   ├── chat_repository.py
│   │   │   │   ├── ble_repository.py
│   │   │   │   ├── legal_repository.py
│   │   │   │   ├── itinerary_repository.py
│   │   │   │   ├── poi_repository.py
│   │   │   │   ├── fitness_state_repository.py
│   │   │   │   ├── performance_repository.py
│   │   │   │   ├── ai_audit_repository.py
│   │   │   │   ├── user_repository.py
│   │   │   │   └── user_oauth_repository.py
│   │   │   ├── training_load.py  # ATL/CTL/TSB, RSS, 7-day summary
│   │   │   └── ...
│   │   ├── db/             # Data Access Layer
│   │   │   ├── database.py # SQLite CRUD sync (~4065 lines, in estrazione)
│   │   │   ├── postgres_db.py # PostgreSQL ORM layer
│   │   │   ├── repositories/ # SQLite repository wrappers (2 file attivi)
│   │   │   │   ├── athlete_repository.py
│   │   │   │   └── ride_repository.py
│   │   │   └── ...
│   │   └── ...
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
├── aethermap/              # Terrain intelligence module (converged from R&D into BikeMaster)
├── docs/                   # Documentazione sviluppatore
│   ├── archive/            # Documentazione IT storica/douplicata (archiviata)
│   ├── reference/          # Dizionario dati, schemi
├── scripts/                # Utility (tauri_agent.py, frontend_aligner.py)
├── tests/                  # Test legacy root (108 file — migrare in bike_analyzer/tests/)
├── android/                # Android Kotlin nativo (Capacitor)
├── knowledge_base/         # Documenti RAG
├── alembic/                # Migrazioni DB
├── docker/                 # Dockerfile + docker-compose
├── .github/workflows/      # CI/CD
├── ROADMAP.md              # ← Questo file (fonte di verità)
├── PROJECT_STATUS.md       # Stato moduli (sintesi)
├── AGENTS.md               # Istruzioni agenti
├── main.py                 # Entrypoint root (delega a bike_analyzer)
├── pyproject.toml          # Config Python
├── requirements.txt        # Dipendenze Python
├── render.yaml             # Deploy backend Render
├── render-hub.yaml         # Deploy hub Render
└── vercel.json             # Deploy frontend Vercel
```

---

## 8. Comandi Rapidi

```bash
# Backend test (chunk per stabilità)
pytest tests/

# Frontend test
cd frontend && npm run test

# Frontend typecheck + lint
cd frontend && npm run typecheck && npm run lint

# Tauri build desktop
cd frontend && npm run tauri build

# BM2 demo
cd bike_analyzer && python -m bm2.simulation.demo

# AetherMap demo
cd aethermap/src && python -m aethermap.ai.demo
```

---

## 9. Note di Contesto

- **Non ricreare `temp_aethermap/`**: è già stato assorbito in `aethermap/`.
- **Non ricreare script duplicati**: `scripts/` è la posizione canonica.
- **Non modificare `docs/archive/`**: contiene documentazione IT storica/douplicata archiviata, non toccare senza esplicita indicazione.
