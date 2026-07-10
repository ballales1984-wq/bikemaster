# AGENTS.md — BikeMaster

Guida per agenti AI e contributor che lavorano su questo repository. Documenta
struttura, build, auth/OAuth e le insidie già risolte, così da evitare regressioni.

## Stack
- **Frontend**: Vue 3 + Pinia + Vue Router 4 + Vite 5 + TypeScript (`vue-tsc`).
  PWA via `vite-plugin-pwa` (`sw.js` custom in `frontend/src/sw.js`).
  Test: Vitest (unit) + Playwright (E2E).
- **Backend**: FastAPI (Python) in `bike_analyzer/backend/`, esposto con prefisso
  `/api/v1` (vedi `bike_analyzer/backend/api/app_factory.py:202`).
- **Deploy**: Render via Docker (vedi `Dockerfile`/`render.yaml` a root o `docker/`).
- **Altro**: Capacitor (Android), Prometheus/Grafana (`prometheus/`, `docker/grafana/`),
  Alembic per le migration DB.

## Struttura repo
```
frontend/                 # App Vue 3 (src/, public/, tests)
  src/
    main.ts               # bootstrap: Pinia, router, SW register, OAuth token da URL
    App.vue               # shell + overlay oauthLoading + LoginForm
    router/index.ts       # guard auth, sync localStorage, redirect post-login
    stores/auth.ts        # JWT in localStorage, isTokenValid(), login/register/logout
    stores/ui.ts          # tema, lingua, oauthLoading
    utils/api.ts          # wrapper fetch (apiGet/Post/Put/Delete/Upload) + clearAuth
    components/           # pannelli (RidesPanel, ImportPanel, AthletePanel, ...)
    views/                # RidesView, RideTracking, pagine legali
    composables/          # useRides, useToast, usePWA, useI18n, useChart
bike_analyzer/
  backend/
    api/routes.py         # tutte le route FastAPI (auth, rides, import, health)
    api/app_factory.py    # creazione app, mount router, middleware
    auth/                 # login, JWT, google oauth
    security.py           # OAuth2 scheme, cookie refresh
    rate_limiter.py       # rate limiting (esistente, da cablare su login/register)
    monitoring.py         # health checks DB/Redis/task queue
  core/                   # motore analisi (engine, pipeline, calculators)
  frontend/dashboard.py   # dashboard server-side (non l'app Vue)
tests/                    # test Python (pytest) backend
```

## Comandi

### Frontend
```bash
cd frontend
npm install
npm run dev          # vite dev server
npm run build        # vite build  (ATTENZIONE: vedi "Build su Windows" sotto)
npm run typecheck    # vue-tsc --noEmit --incremental
npm run lint         # eslint --fix
npm run test         # vitest unit
npm run e2e          # playwright test (config: playwright.config.js)
npm run e2e:local    # playwright --config playwright.local.config.js
```
- Config Vitest: `frontend/vitest.config.js`. Test unit esistenti in
  `frontend/src/stores/auth.test.ts`, `ui` test, `trackingStore.test.ts`.
- **NON esiste** `playwright.prod.config.js` né `frontend/tests/e2e`: i test E2E
  stanno in `frontend/tests/` con `playwright.config.js`. Se serve un config
  "prod", crearlo a partire da quello esistente.

### Backend
```bash
pip install -e .            # o via .venv
pytest                      # test Python (tests/)
```
- Health endpoints (già presenti in `bike_analyzer/backend/api/routes.py`):
  - `GET /api/v1/health` (routes.py:261)
  - `GET /api/v1/health/redis` (routes.py:280)
  - `GET /api/v1/health/detailed` (routes.py:952)
  - Esclusi dal tracing: `/metrics`, `/health` (app_factory.py:90).
  **Nota**: il path è `/api/v1/health`, non `/health` nudo.

## Auth & OAuth (importante — flusso reale)

### Token storage
- Il JWT è letto/scritto da **`localStorage`** (chiave `bikemaster_token`,
  `bikemaster_user`, `bikemaster_just_logged_in`).
- `utils/api.ts` `request()` su 401 (senza `suppressAuthClear`) chiama
  `clearAuth()` (rimuove le chiavi localStorage), lancia `ApiError("expired", 401)`
  e, tramite `notifySessionExpired()`, mostra il toast "Sessione scaduta" ed esegue
  un **logout silenzioso** nello store (`auth.logout()`). `logout()` richiama anche
  `POST /api/v1/auth/logout` (no-op perché il token è già stato cancellato).
  Nota: il logout silenzioso è già implementato; AGENTS.md versioni precedenti
  lo descrivevano come mancante.

### Flusso login
1. `auth.login()` (stores/auth.ts:63) chiama `POST /api/v1/auth/login`
   (form-urlencoded) e salva token+user in localStorage.
2. `App.vue` `onLogin` fa `router.push('/rides')`.
3. Per OAuth (Google), il backend redirige al frontend con `?token=...&email=...`
   (o `#token=...`). `main.ts` (righe 19-31) legge il token dall'URL e chiama
   `auth.setAuthFromUrl()`, poi `history.replaceState` per pulire l'URL.
   In caso di errore: `?oauth_error=...` → `auth.setOauthError()`.

### Guard del router (router/index.ts) — RACE CONDITION GIÀ RISOLTA
Il `beforeEach` sincronizza lo stato Pinia da localStorage **prima** di valutare
l'auth, perché `main.ts` può impostare il token prima che il guard parta.
Punti critici da NON rompere:
- Sync `auth.token` / `auth.user` da localStorage (righe 160-174).
- Invalidazione token scaduto (righe 176-182) → pulisce localStorage.
- Gestione token OAuth da hash/query (righe 185-204) → chiama
  `ui.setOauthLoading(false)`.
- Redirect post-login: se `hasToken && (to.path === '/' || justLoggedIn)` →
  `checkProfileComplete()` → `/rides` se profilo completo, altrimenti `/athlete`
  (righe 221-229). `checkProfileComplete` chiama `GET /api/v1/auth/me`.
- **Pulire `bikemaster_just_logged_in` DOPO `next()`** (righe 225-226), altrimenti
  `App.vue` non renderizza la dashboard (dipende da `ui.oauthLoading` e da
  `justLoggedIn`).
- Alla fine del flusso OAuth imposta sempre `ui.setOauthLoading(false)`.

### `oauthLoading`
- Stato in `stores/ui.ts` (`ui.oauthLoading`), NON nel router.
- `App.vue` mostra l'overlay di loading se `ui.oauthLoading` è true e nasconde
  login/dashboard. Va sempre resettato a `false` al termine di OAuth (main.ts,
  router guard, evento `oauth-loading-end` in App.vue:131).

## Build su Windows (problema EPERM)

`vite build` su Windows può fallire con `EPERM` per colpa del lock di Windows
Defender / Antivirus. Il lock colpisce sia i file generati (`dist/registerSW.js`)
sia i file sorgente appena riscritti (es. `src/components/CalendarPanel.vue`)
durante la trasformazione di Rollup/PWA. Sintomi tipici:
`EPERM, Permission denied` o `EPERM: operation not permitted, realpath '<file>'`.
Mitigazioni applicate/consigliate:
- **Wrapper di retry**: `frontend/scripts/build.mjs` esegue `vite build
  --emptyOutDir` e, in caso di `EPERM`, ripulisce `dist` e ritenta fino a 3 volte
  (attesa 4s). `package.json` deve puntare `build` a questo script:
  ```json
  "build": "node scripts/build.mjs --emptyOutDir",
  "prebuild": "powershell -NoProfile -Command \"try { Add-MpPreference -ExclusionPath (Get-Location).Path -ErrorAction Stop } catch { Write-Host 'prebuild: skipping Defender exclusion (needs admin or already set)' }\""
  ```
- Esclusione Defender (richiede admin): `Add-MpPreference -ExclusionPath
  "<repo>\frontend"` — risolve alla radice i lock persistenti. Senza admin il lock
  è solo ritardato (Defender rilascia dopo la scansione) e il retry wrappa.
- Alternativa: `vite build --emptyOutDir` (svuota `dist` prima di scrivere).
- Se anche il retry fallisce in modo persistente, il file è bloccato a livello OS:
  servono i permessi admin per l'esclusione, oppure attendere il rilascio del lock.

## Rate limiting
- `bike_analyzer/backend/rate_limiter.py` espone `limiter` (slowapi) con chiave
  `get_limiter_key` (rispetta `X-Forwarded-For` dai proxy trusted).
- Già cablato sulle route di auth per prevenire brute force:
  - `POST /api/v1/auth/login` → `5/minute` (routes.py:302)
  - `POST /api/v1/auth/register` → `3/minute` (routes.py:417)
- Requisito slowapi: la route decorata deve avere `request: Request` come primo
  parametro (entrambe le route lo soddisfano).
- Altri endpoint limitati: OAuth Google (`10/minute`), `/api/v1/rides`
  (`10/minute`), ecc. Cercare `@limiter.limit` in `routes.py` per l'elenco
  completo.

## Note per agenti
- Non introdurre dipendenze non presenti in `package.json` / `requirements` senza
  verificarle prima.
- I test Python sono numerosi (`tests/test_*.py`); eseguire `pytest` prima di
  modifiche backend ampie.
- Il service worker (`sw.js`) usa caching su `/api`: attenzione a dati stale sulle
  rides; prevedere invalidazione cache (SKIP_WAITING già gestito in main.ts:46).
- `RidesPanel.vue` ha export CSV; `ImportPanel.vue` gestisce import
  (Strava/Garmin/Google Fit) — l'import da Strava/Garmin passa già da
  `ImportPanel`, non serve ricrearlo.
