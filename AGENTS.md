# AGENTS.md — BikeMaster

BikeMaster is a lifestyle health intelligence system (FastAPI + Vue 3 + TypeScript) that defines health state as the dynamic balance of variables acquired from real life, with a BikeMaster 2.0 simulation engine and an independent AetherMap R&D cartography project.

## Architecture (local-first; production deployed on Render + Vercel)

- **Local-first**: la stessa app gira 100% offline (desktop Tauri o PWA/webapk installata sul dispositivo mobile).
- **Primary platform (offline/reference)**: Tauri 2 desktop app (Rust + WebView) — native `.exe`/`.dmg`/`.AppImage`.
- **Frontend**: Vue 3 + Vite + TypeScript (PWA + service worker, installabile come webapk su mobile).
- **Backend**: FastAPI (Python) — embedded in the Tauri app on `localhost` for desktop, Docker web service on Render for production.
- **Production deployment**: backend su **Render** (`bikemaster-api`, FastAPI/Docker, auto-deploy da `main`) + PostgreSQL gestito `bikemaster-db`; frontend su **Vercel** (static build). Render è fonte di verità (`render.yaml`); Vercel frontend richiama API su Render (CORS + `VITE_API_BASE`). Mobile: PWA installata dall'URL deployata (offline via service worker).
- **ngrok/local tunneling**: NON usato in produzione né più necessario (è stato il workaround durante la sospensione di Render). Sviluppo locale: `python main.py api --port 8000` (SQLite) su LAN; nessun tunnel richiesto.
- **Database**: SQLite (`db_path=rides.db`) è il primary store locale persistente su disco (offline). PostgreSQL (Render) è il backend gestito per auth/users + (a breve) atleti/rides sync.
- **Sync**: opzionale, controllato dall'utente; può restare su "Mai" e usare l'app 100% offline.
- **AetherMap**: R&D cartography project (`aethermap/`) converged into BikeMaster as the terrain-intelligence module.

> **⚠️ Nota persistenza (aggiornata)** — su Render il layer atleta/rides/metrics (`db/database.py`) è **SQLite-only** e `rides.db` è efmero nel container (nessun volume); al resume post-sospensione i dati tornano al default, mentre auth (PostgreSQL) sopravvive. **Parzialmente risolto**: quando `DATABASE_URL` è impostato, le funzioni di profilo atleta (`get_athlete`/`save_athlete`/`update_athlete`), il log metrico (`log_athlete_metric`/`get_athlete_metric_log`) e gli snapshot (`save_athlete_snapshot`/`get_athlete_history`) sono ora instradate su PostgreSQL tramite `db/postgres_athlete.py` (sync `psycopg2`, colonne allineate a `db/models.py`), così `weight_kg` e il profilo atleta persistono. **Resante**: `rides`/`metrics`/`training_stress_days` sono ancora SQLite-only su Render e richiedono un instradamento analogo su PostgreSQL per persistenza completa.

## Quick Reference

- **Backend tests:** `pytest` (from repo root)
- **Frontend tests:** `cd frontend && npm run test`
- **Lint/typecheck:** `cd frontend && npm run lint && npm run typecheck`
- **Build frontend:** `cd frontend && npm run build`
- **Tauri build:** `cd frontend && npm run tauri build` (or equivalent Cargo command)
- **Deploy frontend (Vercel):** `cd frontend && npx vercel --prod` (richiede `vercel login` + link progetto in `.vercel/`)
- **Deploy backend (Render):** `git push origin main` (auto-deploy da `render.yaml`)
- **Simulator:** `cd bike_analyzer && python -m bm2.simulation.demo`

### Deploy wiring (Vercel frontend ↔ Render backend)

- Il frontend su Vercel chiama il backend su Render: `VITE_API_BASE=https://bikemaster.onrender.com` (impostare nella env `VITE_API_BASE` del progetto Vercel e in `frontend/.env.production`).
- Su `.vercel.app`, `resolveApiBase()` usa `VITE_API_BASE`/base salvata (`src/utils/backend-config.ts`).
- Su Render, `render.yaml` deve permettere l'origine Vercel in `CORS_ORIGINS` e `OAUTH_ALLOWED_REDIRECT_HOSTS` (OAuth callback è server-side su Render).
- `ngrok` RITIRATO: non usato in produzione; utile solo per sviluppo locale/remoto.

## Universal Rules

- Do not introduce new dependencies without verifying they are already in `package.json` / `requirements`.
- Never commit secrets or API keys.
- Run relevant tests before considering a task complete.
- For detailed instructions, see [docs/agent/README.md](docs/agent/README.md).
