# BikeMaster — Roadmap Unificata

*Ultimo aggiornamento: 2026-08-14*

> **Principio guida**: fare le cose una volta, farle bene. Questo documento è la
> *fonte di verità unica* per stato, priorità e azioni. Non eseguire feature
> duplicate: verificare qui prima di iniziare qualsiasi lavoro.
>
> **Regola v1**: un dominio/fix alla volta. Nessun nuovo fronte finché il corrente
> non è chiuso (merge + test + deploy).

---

## 0. Definizione v1 "Finito per Davvero"

### v1 Must-Have (obbligatorio per release)

| # | Item | Stato |
||:--|:--|
| 1 | Tutti i domini dati critici sopravvivono al resume/suspend Render | ✅ Fatto |
| 2 | Disco persistente Render configurato + check startup | ✅ Fatto |
| 3 | Calendar migrato a PostgreSQL con dispatch | ✅ Fatto |
| 4 | OAuth produzione stabile (race condition 401/logout risolta) | ✅ Fatto |
| 5 | PWA/Vercel funzionante (CSP, service worker, auth storage) | ✅ Fatto |
| 6 | Test suite: tutti i test critici passano (auth, persistenza, dispatch) | 🔄 In corso |
| 7 | Documentazione stato reale in PROJECT_STATUS.md | ✅ Fatto |
| 8 | Backup manuale DB prima di ogni deploy | ✅ Fatto |

### v2 Backlog (dopo v1)

| # | Item | Priorità |
|:--|:--|:--|
| 1 | Voice Coach (TTS/audio) | Bassa |
| 2 | Anomaly detection + training plan LLM | Bassa |
| 3 | Coverage test >90% su routes.py e moduli AI | Media |
| 4 | Rifiniture AetherMap oltre il minimo | Bassa |
| 5 | Estrazione repository HR, metabolico, chat, BLE, legal, POI, safety da database.py | Media |
| 6 | Playwright E2E spec complete | Media |
| 7 | Android release verificata (APK/AAB) | Media |

> **Decisione (2026-08-14)**: v1 si concentra su persistenza dati e stabilità produzione.
> Voice Coach, anomaly detection e training plan LLM sono spostati in v2.
> Coverage test target ridotto da 90% a "solo path critici" per v1.

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

- **Branch**: `main`
- **Modified**: `bike_analyzer/backend/db/database.py` (+calendar functions con `@pg_dispatch`, +persistenza warning), `bike_analyzer/backend/db/dispatch.py` (+calendar in POSTGRES_BACKENDS), `bike_analyzer/backend/db/postgres_calendar.py` (nuovo), `bike_analyzer/backend/analytics/repositories/calendar_repository.py` (re-export da database.py), `bike_analyzer/backend/api/app_factory.py` (+persistent disk check), `render.yaml` (+disk persistente), `PROJECT_STATUS.md` (stato migrazione), `ROADMAP.md` (v1 definition)
- **Deleted**: `bike_analyzer/backend/db/repositories/calendar_repository.py` (sostituito da dispatch in database.py)

---

## 4. Priorità Assoluta (ordine di esecuzione)

### Fase 0 — Ferma l'emorragia dati ✅ COMPLETATA (2026-08-14)

1. ✅ **Disco persistente Render** — 1GB su `/mnt/data`, `DB_PATH=/mnt/data/rides.db`
2. ✅ **Check startup** — fallisce rumorosamente se disco non montato (produzione)
3. ✅ **Warning log** — scritture SQLite su path non persistente vengono loggate
4. ✅ **Backup manuale** — `rides_backup_YYYYMMDD_HHMMSS.db` creato prima di modifiche
5. ✅ **Calendar migrato** — `postgres_calendar.py` + `@pg_dispatch` in `database.py`
6. ✅ **Training Goals** — già migrato (`postgres_db.py` + SQLAlchemy)
7. ✅ **Domini dispatchati** — 5 domini su PostgreSQL (athlete, rides, itineraries, users, calendar)
8. ✅ **Domini con postgres_*.py** — 17 moduli PostgreSQL esistenti, collegati via dispatch

### Fase 1 — Congela scope ✅ COMPLETATA (2026-08-14)

9. ✅ **v1 must-have definito** — 8 item critici per release
10. ✅ **v2 backlog definito** — Voice Coach, anomaly detection, coverage test, AetherMap rifiniture
11. ✅ **Regola "un dominio/fix alla volta"** — documentata in ROADMAP.md

### Fase 2 — Refactoring database.py 🔄 IN CORSO

12. 🔄 **HR 24h** — `postgres_hr.py` esiste, dispatch in `database.py`, repository analytics già convertito
13. 🔄 **Metabolico** — `postgres_metabolic.py` esiste, dispatch in `database.py`
14. 🔄 **Chat** — `postgres_chat.py` esiste, dispatch in `database.py`
15. 🔄 **BLE** — `postgres_ble.py` esiste, dispatch in `database.py`
16. 🔄 **Legal** — `postgres_legal.py` esiste, dispatch in `database.py`
17. 🔄 **POI** — `postgres_poi.py` esiste, dispatch in `database.py`
18. 🔄 **Safety** — `postgres_safety.py` esiste, dispatch in `database.py`
19. 🔄 **Nutrition** — `postgres_nutrition.py` esiste, dispatch in `database.py`
20. 🔄 **Beck** — `postgres_beck.py` esiste, dispatch in `database.py`
21. 🔄 **Fitness states** — `postgres_fitness.py` esiste, dispatch in `database.py`
22. 🔄 **Sensor/activity** — `postgres_sensor.py` esiste, dispatch in `database.py`
23. 🔄 **Weather** — `postgres_weather.py` esiste, dispatch in `database.py`
24. 🔄 **User OAuth** — `postgres_user_oauth.py` esiste, dispatch in `database.py`

> **Nota**: tutti i domini sopra hanno già il modulo PostgreSQL e il dispatch in `database.py`.
> L'estrazione in repository dedicati (`db/repositories/`) è il passo successivo per
> ridurre la dimensione di `database.py`. Priorità: Calendar → HR → metabolico → chat → BLE → legal → POI → safety.

### Fase 3 — Stabilizzazione produzione ✅ COMPLETATA (2026-08-10)

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
  PWA → backend FastAPI (localhost:8001) + SQLite
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
