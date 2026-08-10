# BikeMaster — Piano d'Azione: Consolidamento, Test Coverage e Produzione

> **Questo documento è storico (2026-07-18). Il piano di sviluppo aggiornato
> è in [`ROADMAP.md`](../ROADMAP.md).**

*Data: 2026-07-18 — aggiornamento post-merge branch + fix bug (commit `cec425b`)*

Questo piano parte dallo stato verificato oggi. I 3 branch (`feat/local-auth`,
`feat/auth-sync-ui`, `feat/local-sync`) **sono già mergiati in `main`**; i bug
emersi dai test sono stati fixati in `cec425b`. Restano da chiudere: stabilità
test frontend, coverage mirata, hardening CI, distribuzione desktop/cloud e
documentazione.

---

## 0. Stato verificato (oggi)

| Area | Risultato | Note |
|:--|:--|:--|
| Backend test | **~2611 pass, 0 fail** | tutti i chunk verdi dopo i fix di `cec425b` |
| Frontend test (vitest) | **381 pass / 1 fail / 5 errors** | era 332/31/20 nel report |
| Frontend fail residuo | `RideMapPanel.test.js` | errore harness Leaflet (`L.latLng is not a function`), NON bug prodotto |
| Repo | pulito | log/backup DB rimossi, `*.log` in `.gitignore` |
| CI | presente (`ci.yml`) | ma `pytest tests/` non è chunked → rischio timeout/OOM in CI |
| Coverage | solo report XML a Codecov | nessun gate su `routes.py` / moduli AI |

---

## FASE 1 — Stabilità test frontend ✅ COMPLETATA (2026-07-18)

**Risultato: vitest 382 pass / 0 fail / 0 error (i 3 file fixati passano; i 2 "fail"
residui in run combinato erano pollution parallelo, verificati green in isolamento).**

1. **`RideMapPanel.test.js`** — aggiunto `latLng` al mock Leaflet (mancava →
   `L.latLng is not a function`). Fixa 1 fail + 5 error. ✅
2. **`AthletePanel.test.js`** — aggiunta rotta `/rides` al router di test (toglie
   il warning `[Vue Router warn]: No match found for location "/rides"`). ✅
3. **`RideMetricsPanel.test.js`** — corretto assertion obsoleto sul formato tempo:
   il componente usa `MM:SS` (<1h) e `H:MM:SS` (>=1h, ore NON pad-date). ✅
4. **`useRides.test.js` / `notifications.test.js`** — verificati green in isolamento
   (5/5). I fallimenti nel run combinato erano **parallel pollution** (stato globale
   condiviso tra file). Non sono bug: da indagare `test.sequential`/`global` se
   persistono in CI.

**Nota CI**: il run completo vitest impiega ~20 min (collect ~413s, environment
~5000s di cumulato). In CI usare `--reporter=dot` e timeout generoso, oppure
split per cartella.

---

## FASE 2—6 (DA FARE)

> Le fasi seguenti NON sono state ancora eseguite.

## FASE 1 (originale, per riferimento) — Stabilità test frontend (1-2 settimane) ⚠️ PRIORITÀ

**Obiettivo: portare vitest a 0 fail / 0 error.**

1. **Fix `RideMapPanel.test.js` (1 fail + 5 error)**
   - Causa: il test gira in ambiente jsdom ma Leaflet (`L.latLng`, `L.latLngBounds`)
     non è mockato/inizializzato. Errore: `__vite_ssr_import_6__.default.latLng is not a function`.
   - Azioni:
     - Aggiungere un setup file vitest (`frontend/tests/setup/leaflet.ts`) che fa
       `vi.mock('leaflet', ...)` esponendo `latLng`, `latLngBounds`, `map` come stub,
       OPPURE montare il componente con `L` reale in `environment: 'jsdom'` +
       `globalThis.L = L`.
     - Verificare che `RideMapPanel.vue:401` (`L.latLng(ride.center.lat, ...)`) resti
       invariato (è corretto); il fix è solo nel test.
   - Exit criteria: `npx vitest run src/components/RideMapPanel.test.js` → 0 fail.

2. **Audit dei restanti errori/warning**
   - `AthletePanel.test.js` logga `[Vue Router warn]: No match found for location "/rides"`.
     Aggiungere la route `/rides` nel router di test o usare `global: { stubs }`.
   - Eseguire `npx vitest run --reporter=verbose` e raccogliere l'elenco completo
     fail/error in `frontend/tests/TEST_STATUS.md`.

3. **Playwright E2E**
   - `frontend/tests/e2e` ha 14 `.spec.js` + 3 `.spec.ts`. Eseguire `npm run test:e2e`
     (o `npx playwright test`) in CI e localmente; fissare uno smoke set minimo
     (login + import ride + dashboard) come gate di rilascio.

---

## FASE 2 — Coverage mirata su backend (2-3 settimane)

**Obiettivo: >90% su `routes.py` e moduli AI (oggi ~51%).**

4. **Misurare il baseline reale**
   - `pytest tests/ --cov=bike_analyzer.backend.api.routes --cov=bike_analyzer.backend.analytics --cov-report=term-missing`
   - Salvare l'output in `docs/coverage_baseline.md` (numero esatto, non "~51%").

5. **Aggiungere test sulle aree scoperte**
   - `api/routes.py`: endpoint auth (Google/OAuth callback), coach_chat, athletes
     CRUD, rides import — usare `fastapi.TestClient` con override DB SQLite in-memory.
   - `analytics/ai_coach.py`: casi fallback locale (già parzialmente coperti dai 2 test
     fixati in `cec425b`); aggiungere casi di successo Groq e RAG.
   - `analytics/advanced.py` e `power_model.py`: i 14 modelli + 10 power metrics —
     coprire ogni funzione con 1-2 casi limite (input vuoti, valori estremi).

6. **Gate di coverage in CI**
   - Aggiungere a `ci.yml` (job `test`):
     `--cov-fail-under=90` **solo** per i percorsi target, altrimenti il build globale
     rompe. Meglio: due step — `pytest` (senza gate) + `pytest --cov=bike_analyzer.backend.api.routes --cov-fail-under=90`.
   - Il target >90% resta *informativo* (come da report), ma il gate su `routes.py`
     diventa bloccante.

---

## FASE 3 — Hardening CI / Produzione (settimana 3-4)

7. **Chunking pytest in CI** (evita timeout/OOM come in locale)
   - In `ci.yml`, sostituire `pytest tests/` con una matrice o uno script che lancia
     i chunk (es. `scripts/run_backend_chunks.sh` che replica `run_chunks.ps1`).
   - Opzione più semplice: `pytest tests/ -x --timeout=300` + `--cov` su Ubuntu
     (più RAM di locale). Verificare prima il consumo memoria in CI.

8. **Frontend typecheck/lint come gate bloccante**
   - Già presenti in CI (`npm run lint` + `npm run typecheck`). Verificare che passino
     localmente: `cd frontend && npm run lint && npm run typecheck`.

9. **Secrets & deploy**
   - `deploy-vercel` esiste ma per il desktop Tauri serve `tauri-release.yml`
     (presente) → verificare che produca `.exe`/`.dmg`/`.AppImage` e crei GitHub Release.
   - `render.yaml` (backend locale) + `render-hub.yaml` (hub multi-tenant PostgreSQL):
     fare un deploy di prova dell'hub e verificare la sync device↔cloud end-to-end.
   - Vercel: `VITE_API_BASE` va ri-puntato dopo ogni reboot ngrok (documentato in
     `environment.md`); automatizzare con `scripts/tauri_agent.py update` se possibile.

10. **Database: Alembic vs modelli**
    - In `cec425b` ho cambiato `pois.type` da `Enum(POIType)` a `String`. Serve una
      migration Alembic per gli ambienti PostgreSQL/hub (SQLite locale tollera il
      cambio, ma l'hub no). **Azione:** generare `alembic revision --autogenerate`
      e verificare che non droppi/ricrei la colonna `type`.

---

## FASE 4 — Distribuzione desktop & mobile (mese 1)

11. **Tauri build verificata**
    - `cd frontend && npm run tauri build` → `.exe` funzionante (il fix IPv6 Axum in
      `cec425b` era necessario: il bind su `::` falliva su alcuni sistemi).
    - Smoke test: avvio app, import GPX, AI Coach, dashboard — tutto offline.

12. **GitHub Releases** per desktop via `tauri-release.yml` (auto-update opzionale).

13. **Android release** via `android-release.yml` → APK + AAB firmati.

---

## FASE 5 — BM2 Deluxe & AetherMap (mese 2+, R&D)

14. **UI simulazione frontend**: `Bm2Panel.vue` esiste → integrazione "What-if" su
    ride esistenti (usa `bm2_routes.py` già esposto).
15. **Validazione fisica BM2**: confronto stime vs power meter su 10+ ride
    (`core/physics/validation.py` già presente).
16. **AI Coach + BM2**: l'orchestratore NL usa i risultati simulazione.
17. **AetherMap**: chiudere Fase 3 (AI pipeline) e Fase 5 (digital twin); decidere
    convergenza in BikeMaster o R&D separato.

---

## FASE 6 — Documentazione consolidata (parallela, bassa priorità)

18. Unificare `docs/MASTER.md` e i contenuti di `docs/UNIFIED_DOCUMENTATION.md` in un solo file;
     `docs/DELUXE_ROADMAP.md` → riferire a `ROADMAP.md` (anti-duplicazione).
19. Non toccare `docs/archive/` (storico).

---

## Ordine di esecuzione consigliato

```
Sett. 1-2:  Fase 1 (frontend 0 fail)  →  sblocca CI verde
Sett. 2-3:  Fase 2 (coverage routes/AI >90%)
Sett. 3-4:  Fase 3 (chunking CI, migration Alembic, deploy hub)
Mese 1:     Fase 4 (Tauri/Android release)
Mese 2+:    Fase 5 (BM2/AetherMap)
```

## Rischi / attenzioni

- **Fase 1** è la più urgente: con `RideMapPanel.test.js` rotto, la CI frontend
  fallisce e non si può fare release. Il fix è solo test-harness (Leaflet mock).
- Il **chunking pytest** è obbligatorio prima di fidarsi della CI: in locale
  `pytest tests/` andava in timeout/OOM.
- La **migration Alembic per `pois.type`** è un blocco silenzioso per l'hub PostgreSQL.
- Niente segreti/API key nei commit (già in `.gitignore`: `.env`, `*.secret`).
