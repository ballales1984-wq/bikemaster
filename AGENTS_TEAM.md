# AGENTS_TEAM.md — Team Operativo & Piano di Migrazione Persistente

Complementare a [`AGENTS.md`](AGENTS.md) e [`docs/agent/team.md`](docs/agent/team.md).
Definisce il **team operativo** (ruoli, RACI) e il **piano di migrazione persistenza**
su Render — il rischio operativo critico (#1) identificato da AGENTS.md, per cui
`rides.db` (SQLite) è efimero nel container e `rides`/`metrics`/`training_stress_days`
tornano al default al resume.

---

## 1. Forza e contesto (riassunto)

- **Architettura**: local-first. Tauri 2 desktop (primario) + PWA web (secondario).
  Backend FastAPI embedded in locale (SQLite, porta 8000) e su Render (FastAPI/Docker
  + PostgreSQL gestito). Frontend Vue 3 su Vercel.
- **Fonte di verità produzione**: `render.yaml` (backend) → Vercel (frontend).
  - **Rischio #1** ✅ RISOLTO: persistenza su Render. Auth/users → PostgreSQL (sopravvive); `rides`/`metrics`/`training_stress_days` → PostgreSQL (`db/postgres_rides.py`, dispatch `has_postgres()`); SQLite riservato a locale/offline (Tauri/PWA).

## 2. Team operativo (mappatura ruoli engineering → agenti)

Organizzato attorno a **prodotti verticali** (come suggerito nell'analisi):

| Prodotto verticale | Engineering role | Agenti Kilo coinvolti | Owner codice |
|---|---|---|---|
| Sync & Persistence | Data/Sync Engineer + Migrations | BACKEND, DATABASE, DEBUGGER, TESTER, SECURITY | `.kilo/agent/database.md`, `db/postgres_athlete.py` |
| Simulator / BM2 | Simulation Engineer | `domain-bm2`, `adaptation-engine`, `load-manager`, `athlete-state` | `bike_analyzer/bm2/` |
| AetherMap (carto) | R&D Cartography Engineer | `domain-aethermap` + fasi `aethermap-*` (`airunway-aks-setup`, `aethermap-rendering`, ecc.) | `aethermap/` |
| Frontend / Tauri | Frontend Engineer | FRONTEND, `frontend-alignment` | `frontend/` |
| Auth / Users | Security + Backend Engineer | SECURITY, BACKEND, `domain-connection`, `fix-02-logout`, `fix-07-connection` | `api/auth.py`, `stores/auth.ts` |
| Deploy / Infra | DevOps/Infra Engineer | `al-service`, `production-pusher`, `github-sync` | `render.yaml`, `Dockerfile`, `vercel.json` |
| QA / Release | QA & Release Engineer | TESTER, VERIFIER, REVIEWER, `fix-09/10` (esempi) | `tests/`, `frontend/tests/` |

### RACI — decisioni chiave

| Decisione | Responsabile | Approva | Controlla | Informa |
|---|---|---|---|---|
| Schema DB / colonne | DATABASE + BACKEND | ARCHITECT | VERIFIER (test integrità) | ORCHESTRATOR |
| Migrazione/rollback DB | DATABASE (lead) | ORCHESTRATOR + Lead Dev | TESTER (regressione) | SECURITY, BACKEND |
| Modifica flusso OAuth | BACKEND / `domain-connection` | **Lead Dev (obbligatorio)** | SECURITY | FRONTEND, ORCHESTRATOR |
| Deploy in produzione | `production-pusher` | Lead Dev (LEVEL 3/4) | VERIFIER + SECURITY | ORCHESTRATOR |
| Aggiunta dipendenza | chi propone | ARCHITECT | SECURITY (audit) | ORCHESTRATOR |
| Fix di persistenza su Render | DATABASE / BACKEND | ORCHESTRATOR + Lead Dev | TESTER (snapshot/restore) | SECURITY |
| Modifica cache PWA / SW | FRONTEND | FRONTEND lead | TESTER (offline E2E) | ORCHESTRATOR |

> **Vincolo inviolabile**: il flusso OAuth in `router/index.ts` e `stores/auth.ts`
> richiede conferma esplicita del Lead Developer (sezione "Vincoli" in AGENTS.md).

## 3. Piano di migrazione persistente (Render) — RISCHIO #1

### Stato verificato (completato) ✅
La migrazione persistente richiesta da AGENTS.md "Resante" è **già implementata** nel codice corrente (verificato in `db/postgres_rides.py`):

- `db/postgres_rides.py` (485 righe) implementa completamente `rides`/`metrics`/`training_stress_days` su PostgreSQL: `save_ride` (dedup + stima calorie + JSON GPS), `get_ride`, `get_rides_by_athlete`, `get_all_rides`, `delete_ride`, `update_ride`, `save_metric`, `upsert_training_stress_day` (con `ON CONFLICT`), `get_training_stress_days`, `get_latest_training_stress`.
- `db/database.py` instrada ogni funzione su PostgreSQL quando `DATABASE_URL` è impostato, tramite `has_postgres()` (definita in `postgres_athlete.py` come `bool(DATABASE_URL)`), **identico pattern** a `postgres_athlete.py`. Quando `DATABASE_URL` non è presente (locale/offline Tauri/PWA) mantiene SQLite come store primario.
- `db/postgres_rides.py` riusa `_connect`/`has_postgres` da `postgres_athlete.py` e dichiara le medesime tabelle/colonne.

**Rimane da verificare (QA)**: test cross-store (scrivi su Postgres → leggi corretto), test dual-store offline fallback, snapshot/restore regression. → assegna a TESTER/VERIFIER. (SLO "dati persistiti recuperabili 100%" → soddisfatta dall'instradamento Postgres.)

### Scelta
- **Corto termine (produzione)**: Opzione A (priorità alta) — persistenza totale.
- **Sicurezza transizione**: Opzione B come mitigazione fino al completamento A.

## 4. Prossimi step (priorità, da analisi)

| # | Azione | Priority | Owner | Issue | Nota |
|---|---|---|---|---|---|
| 1 | Migrare rides/metrics a PostgreSQL (Opzione A) | P0 critica | DATABASE/BACKEND | [#4](https://github.com/ballales1984-wq/bikemaster/issues/4) | ✅ IMPLEMENTATO (verificato `db/postgres_rides.py`) — chiude #4 |
| 2 | CI backend/frontend + build check (web/tauri) | P0 | DevOps/QA | [#5](https://github.com/ballales1984-wq/bikemaster/issues/5) | `.github/workflows` |
| 3 | Sync contract + test riconciliazione (diverge/merge, TTL) | P0 | Data/Sync | [#6](https://github.com/ballales1984-wq/bikemaster/issues/6) | offline-first |
| 4 | Health/DB metrics + Sentry + alerting | P1 | DevOps | [#7](https://github.com/ballales1984-wq/bikemaster/issues/7) | dati persi, latenza sync |
| 5 | Ruoli/RACI + ownership componenti | P1 | ORCHESTRATOR | — (questo file) | AGENTS_TEAM.md |
| 6 | E2E offline-first + Tauri build regression | P1/P2 | QA/Frontend | [#8](https://github.com/ballales1984-wq/bikemaster/issues/8) | |

## 5. SLO/KPI team agentico
- Disponibilità API auth (prod): 99.9%; sync: 99%.
- Dati persistiti su Render recuperabili al resume: **100%** (obiettivo post-migrazione).
- MTTR incidenti critici (data loss): < 24h.
- Copertura: unit > 80%; integration/E2E in crescita.

## 6. File correlati
- `[AGENTS.md](AGENTS.md)` — regole universali (vincoli OAuth, secrets, no force-push)
- `[.kilo/agent-manifest.md](.kilo/agent-manifest.md)` — roster completo, trust rules
- `[.kilo/command/software-team.md](.kilo/command/software-team.md)` — ciclo cognitivo
- `[docs/agent/team.md](docs/agent/team.md)` — storia/sintesi del team agentico
- `[.kilo/memory/decision-records.md](.kilo/memory/decision-records.md)` — ADR
