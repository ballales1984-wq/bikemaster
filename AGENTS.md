# AGENTS.md — BikeMaster

BikeMaster is a lifestyle health intelligence system (FastAPI + Vue 3 + TypeScript) that defines health state as the dynamic balance of variables acquired from real life, with a BikeMaster 2.0 simulation engine and an independent AetherMap R&D cartography project.

## Architecture (local-first; production deployed on Render + Vercel)

- **Local-first**: la stessa app gira 100% offline (desktop Tauri o PWA/webapk installata sul dispositivo mobile).
- **Primary platform (offline/reference)**: Tauri 2 desktop app (Rust + WebView) — native `.exe`/`.dmg`/`.AppImage`.
- **Frontend**: Vue 3 + Vite + TypeScript (PWA + service worker, installabile come webapk su mobile).
- **Backend**: FastAPI (Python) — embedded in the Tauri app on `localhost` for desktop, Docker web service on Render for production.
- **Production deployment**: backend su **Render** (`bikemaster-api`, FastAPI/Docker, auto-deploy da `main`) + PostgreSQL gestito `bikemaster-db`; frontend su **Vercel** (static build). Render è fonte di verità (`render.yaml`); Vercel frontend richiama API su Render (CORS + `VITE_API_BASE`). Mobile: PWA installata dall'URL deployata (offline via service worker).
- **ngrok/local tunneling**: NON usato in produzione né più necessario (è stato il workaround durante la sospensione di Render). Sviluppo locale: `python main.py api --port 8000` (SQLite) su LAN; nessun tunnel richiesto.
- **Database**: SQLite (`db_path=rides.db`) è il primary store locale persistente su disco (offline). PostgreSQL (Render) è il backend gestito per auth/users + domini migrati (atleta, rides, metrics, training stress, itinerari, training goals); vedi "Nota persistenza" sotto per dettagli.
- **Sync**: opzionale, controllato dall'utente; può restare su "Mai" e usare l'app 100% offline.
- **AetherMap**: R&D cartography project (`aethermap/`) converged into BikeMaster as the terrain-intelligence module.

> **⚠️ Nota persistenza** — su Render il container non ha volumi persistenti: `rides.db` (SQLite) è effimero e viene perso al resume post-sospensione. I domini migrati su PostgreSQL (`athlete`, `rides`, `metrics`, `training_stress`, `itineraries`, `training_goals`) sono protetti perché il layer sincrono (`db/database.py`) effettua il dispatch automatico verso i moduli Postgres quando `DATABASE_URL` è configurato (vedi `has_postgres()`). I domini rimanenti SQLite-only (es. POI, metabolico, chat, calendario, weather, BLE, sensor) restano a rischio di perdita dati su Render.
>
> **Domini migrati su PostgreSQL** (dispatch tramite `has_postgres()` = `bool(DATABASE_URL)`):
> - **Athlete** → `db/postgres_athlete.py`: profilo (`get_athlete`/`save_athlete`/`update_athlete`), storia (`save_athlete_snapshot`/`get_athlete_history`), log metriche (`log_athlete_metric`/`get_athlete_metric_log`), lookup (`get_athlete_by_email`/`get_athletes_by_user`/`get_athlete_count_by_user`/`delete_athlete`).
> - **Rides / metrics / training stress** → `db/postgres_rides.py`: CRUD rides (`save_ride`/`get_ride`/`get_rides_by_athlete`/`get_all_rides`/`delete_ride`/`update_ride`), metrics (`save_metric`), TSS/ATL/CTL/TSB (`upsert_training_stress_day`/`get_training_stress_days`/`get_latest_training_stress`).
> - **Itineraries / stages** → `db/postgres_itineraries.py`: CRUD itinerari (`save_itinerary`/`get_itinerary`/`list_itineraries`/`update_itinerary`/`delete_itinerary`), tappe (`save_stage`/`list_stages`/`get_stage`/`update_stage`/`delete_stage`/`reorder_stages`).
> - **Training goals** → `db/postgres_db.py` (SQLAlchemy sync; attivo solo con `DATABASE_URL`, **nessun fallback SQLite** in `database.py`).
>
> **Rimangono SQLite-only** (nessun dispatch guard, dati persi al resume su Render):
> POI (`save_poi`/`get_poi`/`list_pois`/`get_nearby_pois`/`delete_poi`), HR 24h (`log_hr_sample`/`log_hr_samples`/`get_hr_24h_samples`/`get_hr_daily_summary`/`get_hr_settings`/`upsert_hr_settings`/`delete_hr_settings`/`delete_hr_samples`), metabolico/food logs (`save_metabolic_profile`/`get_metabolic_profile`/`save_food_log`/`get_food_logs_by_athlete_date`/`update_food_log`/`get_food_log`/`delete_food_log`/`save_metabolic_daily_summary`/`get_metabolic_daily_summaries`/`get_metabolic_daily_summary`/`upsert_metabolic_reference_value`/`get_metabolic_reference_value`/`get_all_metabolic_reference_values`/`save_metabolic_adaptive_weights`/`get_metabolic_adaptive_weights`), chat (`save_chat_message`/`get_chat_history`/`clear_chat_history`/`prune_chat_history`), calendario (`save_calendar_event`/`get_calendar_event`/`get_events_by_athlete`/`get_events_by_date_range`/`get_events_by_month`/`update_calendar_event`/`delete_calendar_event`), weather cache (`save_weather_cache`/`get_weather_cache`), road incidents (`save_road_incident`), route safety scores (`save_route_safety_score`/`get_route_safety_score`), fitness states (`get_fitness_states_by_athlete`), nutrition (`save_nutrition_food_item`/`search_nutrition_food_items`/`get_nutrition_food_item`/`list_nutrition_categories`/`update_nutrition_food_item`/`delete_nutrition_food_item`/`seed_nutrition_food_items`), Beck assessments (`save_beck_assessment`/`get_beck_assessment`/`get_beck_assessments_by_athlete`/`get_latest_beck_assessment`), BLE devices (`register_ble_device`/`get_ble_devices`/`get_ble_device`/`update_ble_device`/`unregister_ble_device`/`mark_ble_device_connected`/`mark_ble_device_synced`), users (`save_user`/`get_user_by_username`/`get_user_by_id`/`get_all_users`/`update_user`/`delete_user`), consent/legal/ai_audit (`save_consent`/`get_consent`/`get_consents_by_athlete`/`save_legal_acceptance`/`get_legal_acceptances_by_athlete`/`has_accepted_version`/`save_ai_audit_log`/`get_ai_audit_logs_by_athlete`), sensor/activity (`log_sensor_data`/`classify_day`/`get_activity_summary`/`get_activity_classification`), sync/backup (`backup_database`/`scheduled_backup`/`rotate_backups`).
>
> `db/database.py` mantiene SQLite come fallback offline (Tauri/PWA). Non esiste `postgres_db_full.py`; la migrazione è per-dominio in moduli separati.

## Quick Reference

- **Backend tests:** `pytest` (from repo root)
- **Frontend tests:** `cd frontend && npm run test`
- **Lint/typecheck:** `cd frontend && npm run lint && npm run typecheck`
- **Build frontend:** `cd frontend && npm run build`
- **Tauri build:** `cd frontend && npm run tauri build` (or equivalent Cargo command)
- **Windows code-signing (local):** `pwsh scripts/sign-windows.ps1` (generates self-signed cert + signs `.exe`/`.msi`/`.nsis`). Set `TAURI_SIGNING_PRIVATE_KEY` + `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` env vars (see `src-tauri/.env.signing.example`) for automatic signing during `tauri build`. SAC requires a CA-signed cert for production — GitHub Release builds are signed automatically via `tauri-release.yml`.
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
