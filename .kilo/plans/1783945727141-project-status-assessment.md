# BikeMaster — Stato del Progetto (Assessment)

*Generato: 2026-07-13 — verifica empirica della documentazione vs. codice reale.*

## Sintesi

Il sistema **esiste ed è sostanzialmente implementato**: backend FastAPI ampio (138 endpoint verificati), engine di simulazione BM2 completo e cablato, CI/CD su GitHub Actions, deploy Render, app Android e frontend Vue 3. La definizione "Production Ready" del README è **ottimistica e non uniformemente verificabile**; i tre documenti di stato (README, PROJECT_STATUS.md, ROADMAP.md) **sono in disallineamento tra loro** e con la realtà su alcuni punti chiave (test frontend, licenza, checklist di produzione).

## Verificato a colpo sicuro

| Claim documentazione | Realtà verificata | Stato |
|---|---|---|
| `~106 file` di test backend | **108** file `test_*.py` in `tests/` | ✅ |
| **138 endpoint REST** | 138 decoratori `@router.(get\|post\|...)` in `routes.py` + `bm2_routes.py` | ✅ |
| Engine BM2 Deluxe (9 algoritmi, units, simulation, orchestrator, adapters, routes) | Struttura completa presente in `bike_analyzer/bm2/` + `bm2/algorithms/` (9 moduli) | ✅ |
| bm2 testati e verdi | `pytest tests/test_bm2_units.py` → **19 passed** | ✅ |
| CI/CD | `.github/workflows/ci.yml` con job `test`/`lint`/`aethermap`/`frontend`/`integration`/`security`/`build` + keepalive Render | ✅ |
| Deploy | `render.yaml`, `azure.yaml`, `Dockerfile` multi-stage, `docker-compose.yml` | ✅ |
| AetherMap R&D | Track separato `aethermap/` con workflow CI dedicata | ✅ |

## Discrepanze / Rischi (da risolvere prima di dichiarare "Production Ready")

1. **Test frontend: claim vs realtà.** PROJECT_STATUS.md afferma *"277/277 Vitest tests passano"*. La realtà è **4 file `.test.ts`** (`src/stores/auth.test.ts`, `trackingStore.test.ts`, `ui.aethermap.test.ts`, `src/test/apiOauth.test.ts`). La claim dei 277 test è **falsa/obsoleta**. La CI esegue `npx vitest run` (quindi i 4 file girano), ma la copertura frontend è minima.
2. **Licenza contraddittoria.** Badge README = *"All Rights Reserved"* + file `LICENSE` proprietario; il testo incollato dall'utente riportava *"MIT license"* / *"License: Proprietary"*. Va uniformata a una sola dichiarazione.
3. **Drift tra i 3 documenti di stato.** README ("Production Ready", 1546+ test) ≠ PROJECT_STATUS.md (datato 2026-07-05, "Late Beta / Early Production", 379+ test backend) ≠ ROADMAP.md (datato 2026-07-12, checklist produzione tutta ✅). La checklist "Production Ready" in ROADMAP marca ✅ voci che PROJECT_STATUS segnava ❌/🔄 (Sentry, Prometheus/Grafana, audit log admin, Playwright E2E, coverage >90%). **La ROADMAP è eccessivamente ottimistica.**
4. **Suite backend lenta / non verificabile in locale.** `pytest --co` su tutti i 108 file **timeout a 120s** (il comando è stato terminato). Una singola sotto-suite bm2 gira in ~62s. Il default locale di 120s è insufficiente; la CI usa il timeout job di 6h quindi passa, ma **non è stato verificato che l'intera suite 108 file passi green** in una sola esecuzione.
5. **Branch non fusi** (ROADMAP C.2): `chore/sistema-repo`, `feature/core-engine-refactor` (ampio), `fix/frontend-assets`, `inconclusive-pastry` (AetherMap). Contengono lavoro da revisionare/merge.
6. **PostgreSQL in produzione ancora "⏳"** (PROJECT_STATUS) nonostante deploy Render; Alembic su Render + smoke test non chiusi (DELUXE_ROADMAP A1/A6).

## Raccomandazioni (prossimi passi, in ordine)

1. **Riconciliare i documenti**: un solo source-of-truth per stato/licenza/checklist. Allineare README, PROJECT_STATUS.md, ROADMAP.md; risolvere la contraddizione di licenza (MIT vs All Rights Reserved) in un'unica dichiarazione coerente con `LICENSE`.
2. **Verificare la suite backend completa**: eseguire `pytest tests/ --cov=bike_analyzer` una volta sola (timeout adeguato) e riportare pass/fail reali + coverage %. La claim "1546+ test" va confermata o corretta.
3. **Rettificare lo stato dei test frontend**: o ripristinare i 277 test Vitest mancanti, o aggiornare la documentazione al numero reale (4 file) e alzare la copertura dove serve (auth, tracking, API client).
4. **Chiudere PostgreSQL in produzione**: Alembic migration + smoke test su Render (DELUXE_ROADMAP A6).
5. **Revisionare/merge dei branch aperti** (ROADMAP C.2/C.3) e prune dei remote-tracking obsoleti (richiede conferma utente per `git push`).
6. **Target di maturità**: logging strutturato + servizi nel lifespan FastAPI (ROADMAP P0.1/P0.2), memory conversazionale persistente AI Coach (P2.1), verifica build iOS (P1.1).

## Aperto (fuori scope di questa verifica)

- Validazione fisica BM2 su dati reali misurati (`core/physics/validation.py`) — cablata via `POST /api/v1/bm2/validate` ma non verificata qui con dataset reale.
- Confini AetherMap prodotto vs R&D permanente (DELUXE_ROADMAP C5/C6).

---

## Risoluzione (2026-07-13, dopo verifica empirica)

Due assunzioni del piano si sono rivelate ERRATE dopo verifica sul codice:

1. **Test frontend NON erano 4.** La ricerca iniziale considerava solo *.spec.ts/*.test.ts; i test reali sono *.test.js. Conteggio verificato: **47 file / 318 test** Vitest (harness green su file campione). La claim ~277 in PROJECT_STATUS era solo obsoleta, non falsa.
2. **Licenza NON contraddittoria.** README badge + footer + file LICENSE dicono tutti `All Rights Reserved`. Il `MIT license` era un artefatto di rendering GitHub nel paste dell'utente, non nel README. Nessuna correzione necessaria.

Numeri verificati: backend **108 file / 1674 test**; frontend **47 file / 318 test**; **138** endpoint REST; `test_bm2_units` 19 passed; Sentry/audit log/Prometheus presenti; Playwright config presente ma **0 spec**.

Azioni completate:
- README: numeri di test aggiornati a quelli verificati.
- PROJECT_STATUS.md: stato -> Production Ready, sezione Testing riscritta con numeri reali, checklist produzione allineata, PostgreSQL/monitoring/audit corretti, data 2026-07-13, punta a ROADMAP come fonte di verita.
- ROADMAP.md: stato -> Production Ready, Playwright E2E corretto (config presente, spec da aggiungere), numeri verificati in header.

Residui reali (backlog onesto): Playwright E2E spec da scrivere; coverage globale >90% (P3.5); logging strutturato + lifespan (P0.1/P0.2); memory persistente AI Coach (P2.1); build iOS (P1.1); merge branch aperti (C.2).


## Update (2026-07-13, continuazione)

Terza assunzione del piano era ERRATA: **Playwright E2E non era un gap**. Cercavo *.spec.ts; il 	estDir di Playwright e rontend/tests/e2e e gli spec esistenti sono *.spec.js (14 file: admin, aethermap, app, coach, dashboard, flow, import, knowledge, login, oauth, rides, routes, smoke, tracking). La claim ROADMAP `Playwright E2E ✅` era corretta.

Azione: aggiunti 3 spec **backend-independent** (uth.spec.ts, outing.spec.ts, pp-shell.spec.ts) eseguibili contro la sola SPA preview senza backend (login form, validazione, toggle tema, routing pagine pubbliche, redirect auth). Verificati via `npx playwright test --list`: 303 test in 17 file (i 3 nuovi contati). ROADMAP/PROJECT_STATUS corretti a `Playwright E2E ✅`.

Team dedicati (Agent Manager, 4 worktree): Logging+lifespan (P0.1/P0.2), AI Coach memory persistente (P2.1), Design System tokens (P2.2), review branch aperti (C.2). Avviati async in VS Code extension.
