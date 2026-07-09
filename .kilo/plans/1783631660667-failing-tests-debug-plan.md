# Piano di debug: test frontend fallenti (Vitest)

## Contesto
Esecuzione `npx vitest run` (frontend). Test identificati come fallenti in modo
riproducibile (gli altri file passano). I test backend Python (`pytest`) non sono
stati analizzati qui: la suite è molto grande e va fatta girare in modo mirato
(`pytest tests/test_xxx.py`) se serve.

Ambito confermato con l'utente: **"Test che falliscono"** → ci concentriamo sulla
suite frontend (`frontend/src/**/*.test.{js,ts}`).

## Diagnosi dei fallimenti

### 1. `src/components/LoginForm.test.js` — 10/10 FAIL (bloccante)
- Errore: `[🍍]: "getActivePinia()" was called but there was no active Pinia`.
- Causa: il componente `LoginForm.vue` usa uno store Pinia (`useAuthStore`/
  `useUIStore`), ma i test fanno `mount(LoginForm)` senza installare Pinia.
- Fix: in `LoginForm.test.js` creare una Pinia per ogni mount, es.
  ```js
  import { createPinia, setActivePinia } from "pinia";
  beforeEach(() => setActivePinia(createPinia()));
  // oppure per ogni test:
  mount(LoginForm, { global: { plugins: [createPinia()] } });
  ```
- Verifica: 10/10 verdi.

### 2. `src/utils/api.test.js` — 1/7 FAIL
- Test: `apiGet returns null body on parse error` (riga 65).
- Assert: `rejects.toThrow("GET /api/v1/x: 400")`.
- Ricevuto: `"Request failed"`.
- Causa: in `api.ts:153` il messaggio è
  `extractApiErrorMessage(err) || `${method} ${path}: ${resp.status}``.
  Con body non parsabile `extractApiErrorMessage({})` ritorna `"Request failed"`
  (`api.ts:40`, default), che è truthy → non scatta il fallback con method/path.
- Decisione da prendere (sceglierne una):
  - **A (consigliato, minimo)**: aggiornare l'asserzione del test a
    `.toThrow("Request failed")` per allinearsi al comportamento corrente
    (messaggio generico coerente col resto dell'app).
  - **B (UX migliore)**: rendere `extractApiErrorMessage` falsy su body vuoto
    (ritornare `""` invece di `"Request failed"` quando non c'è né `detail` né
    `message`), così gli errori senza messaggio usano il fallback
    `${method} ${path}: ${status}`. Impatta tutti gli errori con body vuoto
    dell'app, non solo il test.

### 3. `src/components/HeatmapPanel.test.js` — 1/10 FAIL
- Test: `renders load button text` (riga ~).
- Assert: testo contiene `"Load Heatmap"`.
- Ricevuto: `"🔥 Personal Heatmapheatmap.athleteIdh…"` → il componente renderizza
  la **chiave i18n** `heatmap.load`, non il literal inglese.
- Causa: `HeatmapPanel.vue` usa `useI18n` (chiave `heatmap.load`); il mock/test
  non traduce, quindi compare la chiave. Il test è obsoleto rispetto alla
  refactor i18n.
- Fix: aggiornare l'asserzione a `.toContain("heatmap.load")` (coerente con la
  convenzione usata in `LoginForm.test.js` che asserisce sulle chiavi, es.
  `auth.login`).

### 4. `src/components/RideMapPanel.test.js` — 1/10 FAIL
- Test: `renders panel with title`.
- Assert: `"Route Maps"`.
- Ricevuto: `"maps.routeMaps"` (chiave i18n).
- Fix: stesso di #3 → asserire su `"maps.routeMaps"`.

### 5. `src/router/index.test.js` — 5 FAIL SOLO nella run completa
- Errore: `Failed to resolve import "../components/ImportPanel.vue" ... Does the
  file exist?` — ma il file **esiste** (`src/components/ImportPanel.vue`,
  modificato di recente, mtime 09/07 23:32).
- Eseguito **da solo** il test passa (0 fail): è un problema **transient/parallel
  o di cache di Vite**, non un bug reale del router.
- Azione:
  1. Rieseguire isolato: `npx vitest run src/router/index.test.js`.
  2. Se ripete l'errore in isolamento: pulire la cache
     (`npx vitest run --clearCache` / `.vitest` cache) e riprovare; verificare che
     `vitest.config.js` non abbia alias che mascherano `../components/*`.

## Passi di implementazione (ordine)
1. **Frontend** `LoginForm.test.js`: aggiungere Pinia (blocco `beforeEach` con
   `setActivePinia(createPinia())` e/o `global.plugins`). → sblocca 10 test.
2. **Frontend** `api.test.js`: aggiornare l'asserzione del test a
   `.toThrow("Request failed")` (decisione A, confermata dall'utente).
3. **Frontend** `HeatmapPanel.test.js` e `RideMapPanel.test.js`: allineare le
   asserzioni alle chiavi i18n (`heatmap.load`, `maps.routeMaps`).
4. **Frontend** `router/index.test.js`: verificare in isolamento / pulire cache
   Vite se ripete l'errore.
5. **Backend** `security.py` (`revoke_token`, riga ~127): ritornare `True` invece
   di `False` quando `get_redis()` è `None` (fallback in memoria = successo).
   → sblocca 1 test.

## Validazione
- Eseguire in frontend:
  ```powershell
  cd frontend
  npx vitest run src/components/LoginForm.test.js src/utils/api.test.js src/components/HeatmapPanel.test.js src/components/RideMapPanel.test.js
  npx vitest run src/router/index.test.js   # deve passare
  npx vitest run                            # run completa, target: 0 fail
  ```
- Backend:
  ```powershell
  cd D:\BikeMaster
  python -m pytest tests/test_auth_enhanced.py -q
  python -m pytest -q   # run completa, target: 0 failed
  ```
- Opzionale: `npm run typecheck` per non introdurre regressioni TS nei test.

## Rischi / note
- I componenti usano `useI18n` che ritorna la **chiave** nei test (convenzione del
  repo). Le asserzioni su stringhe letterali inglesi sono fragile: meglio
  asserire sulle chiavi o introdurre un mock i18n con dizionario EN condiviso.
- I log `Failed to export traces to localhost:4317 ... UNAVAILABLE` durante
  `pytest` sono **rumore** di OpenTelemetry (nessun collector in esecuzione), non
  fallimenti di test.
- La modifica a `revoke_token` cambia il valore di ritorno solo nel caso Redis
  assente; i chiamanti che gestiscono il fallback in memoria ne traggono
  beneficio. Verificare che nessun caller interpreti `False` come "revoca non
  effettuata" in modo critico.

## Riepilogo fallimenti
- Frontend: LoginForm 10, api 1, HeatmapPanel 1, RideMapPanel 1, router 5 (transient).
- Backend: test_auth_enhanced 1 (revoke_token fallback).
