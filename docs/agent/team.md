# AI Software Team — Agentic Team

Il progetto BikeMaster adotta un **team agentico specializzato** per sviluppo, debug, testing, security e operations. Ogni agente possiede un ruolo definito, un contratto di comunicazione e regole di autonomia.

## Filosofia

Il team non è una chat: è un ciclo cognitivo strutturato (§52) dove l'ORCHESTRATOR riceve l'obiettivo, delega a specialisti, osserva i risultati e corregge con evidenza. La comunicazione avviene tramite eventi strutturati, non conversazioni.

## Roster Core (12 ruoli)

| Ruolo | File | Responsabilità | Memoria | Eventi |
|---|---|---|---|---|
| **ORCHESTRATOR** | `.kilo/agent/orchestrator.md` | Coordinatore: riceve obiettivo, comprende, pianifica, delega, osserva, decide quando fermarsi | shared-log | TASK_CREATED, TASK_ASSIGNED, CONFLICT, SESSION_END |
| **ARCHITECT** | `.kilo/agent/architect.md` | Visione architettura, conseguenze modifiche, ADR | code-graph | IMPACT_REPORT, ARCH_ADR_PROPOSED |
| **FRONTEND** | `.kilo/agent/frontend.md` | Vue 3, Pinia, Router, Vite, Tauri WebView, PWA, test, browser automation | — | API_ERROR, UI_BUG, BROWSER_RESULT, TEST_PASS/FAIL, FIX_APPLIED |
| **BACKEND** | `.kilo/agent/backend.md` | API, servizi, business logic, auth/OAuth, validazione, integrazioni | — | API_ERROR, ROOT_CAUSE_FOUND, FIX_APPLIED, TEST_PASS/FAIL |
| **DATABASE** | `.kilo/agent/database.md` | Schema, tabelle, query, migrazioni, integrità, performance | — | SCHEMA_CHANGED, MIGRATION_APPLIED, DATA_ANOMALY, INTEGRITY_OK |
| **TESTER** | `.kilo/agent/tester.md` | Creazione/esecuzione test, casi limite, regressione, differential verification | bug-database | TEST_PASS/FAIL/SKIP, REGRESSION_PASS/FAIL, DIFF_VERIFY_* |
| **DEBUGGER** | `.kilo/agent/debug.md` | Root cause (riproduci → ipotesi → verifica → correggi → testa) | bug-database | BUG_FOUND, ROOT_CAUSE_FOUND, FIX_APPLIED, REPRODUCE_* |
| **SECURITY** | `.kilo/agent/security.md` | Auth/OAuth, OWASP, injection, segreti, dipendenze, configurazioni | — | SECRET_FOUND, VULN_FOUND, AUDIT_DONE, OWASP_RISK, DEP_VULN |
| **REVIEWER** | `.kilo/agent/reviewer.md` | Verifica indipendente modifiche altrui: correttezza, qualità, architettura | — | REVIEW_PASS/FAIL/NEEDS_CHANGES |
| **LIBRARIAN** | `.kilo/agent/librarian.md` | Custode memoria tecnica: RAG, Project Map, Code Graph, Data Graph, docs, bug DB, decision records, log, lezioni | tutti i file di memoria | MEMORY_UPDATED, CONTEXT_PACKAGED, BUG_ID_ASSIGNED, LEARNING_INDEXED |
| **RELATION_ANALYZER** | `.kilo/agent/relation.md` | Grafo relazioni variabili, data lineage, impatto, causalità, formule | data-graph | LINEAGE_TRACED, IMPACT_REPORT, RELATION_VERIFIED, HYPOTHESIS_RAISED |
| **VERIFIER** | `.kilo/agent/verifier.md` | Verifica indipendente: PASS / FAIL / INSUFFICIENT_EVIDENCE, con evidenza | bug-database, shared-log | VERIFICATION_PASS/FAIL, INSUFFICIENT_EVIDENCE, REGRESSION_REQUESTED |

## Agenti Specialistici di Dominio

Oltre ai 12 ruoli core, il progetto dispone di agenti specialistici per dominio e fix mirati:

| Agente | File | Specializzazione |
|---|---|---|
| adaptation-engine | `.kilo/agent/adaptation-engine.md` | Motore adattamento carico/recupero in tempo reale |
| athlete-state | `.kilo/agent/athlete-state.md` | Profilo dinamico atleta, risposta individuale a carico/recupero |
| code-documenter | `.kilo/agent/code-documenter.md` | Documentazione Python (docstring, commenti) |
| code-explainer | `.kilo/agent/code-explainer.md` | Spiegazione codice e diff git |
| debug-piece | `.kilo/agent/debug-piece.md` | Debug componente per componente |
| frontend-alignment | `.kilo/agent/frontend-alignment.md` | Allineamento frontend PC ↔ mobile |
| load-manager | `.kilo/agent/load-manager.md` | TSS, ACWR, CTL/ATL/TSB, soglie allarme |
| marketing-design | `.kilo/agent/marketing-design.md` | Brand, UI/UX, asset grafici, design system |
| proactive-assistant | `.kilo/agent/proactive-assistant.md` | Notifiche, messaggi, interventi contestuali |
| production-pusher | `.kilo/agent/production-pusher.md` | Push produzione (manuale) |
| security | `.kilo/agent/security.md` | Audit sicurezza, hardening, OWASP |
| training-plan-designer | `.kilo/agent/training-plan-designer.md` | Generazione e ottimizzazione piani allenamento |

### Agenti di Dominio (domain-*)

Esperti di dominio specifico, operano sotto guida ORCHESTRATOR:

- `.kilo/agent/domain-aethermap.md` — motore cartografico AetherMap
- `.kilo/agent/domain-ai-coach.md` — coach digitale, prompt, LLM
- `.kilo/agent/domain-athlete.md` — profilo, anagrafica, obiettivi atleta
- `.kilo/agent/domain-badge.md` — achievement, badge, gamification
- `.kilo/agent/domain-bm2.md` — motore simulazione BM2
- `.kilo/agent/domain-calendar.md` — calendario allenamenti, pianificazione
- `.kilo/agent/domain-compare.md` — confronto uscite, periodi, benchmark
- `.kilo/agent/domain-connection.md` — connessioni esterne, OAuth
- `.kilo/agent/domain-dashboard.md` — dashboard, KPI, widget
- `.kilo/agent/domain-heatmap.md` — heatmap, density, elevazione
- `.kilo/agent/domain-import.md` — importazione GPX/FIT, Strava, Garmin
- `.kilo/agent/domain-itinerary.md` — itinerari, tour, tappe
- `.kilo/agent/domain-knowledge.md` — base di conoscenza, regole, RAG
- `.kilo/agent/domain-logout.md` — logout, pulizia sessione, revoca token
- `.kilo/agent/domain-maps.md` — mappe, percorsi, tile
- `.kilo/agent/domain-metabolism.md` — profilo metabolico, BMR/TDEE, food log
- `.kilo/agent/domain-poi.md` — POI, geocoding, categorizzazione
- `.kilo/agent/domain-rides.md` — CRUD uscite, statistiche, filtri
- `.kilo/agent/domain-settings.md` — preferenze, unità, tema, privacy
- `.kilo/agent/domain-tracking.md` — GPS tracking, segmenti, telemetria
- `.kilo/agent/domain-weather.md` — meteo, previsioni, impatto allenamento

### Agenti di Fix (fix-*)

Correzioni mirate e tracciabili:

- `fix-01-maps-security` — sicurezza mappe, auth /maps/pois/nearby
- `fix-02-logout` — logout completo, pulizia store, revoca token
- `fix-03-rides` — allineamento campo FC, UI modifica ride
- `fix-04-tracking` — correzione trackingStore.points, parser TCX
- `fix-05-bm2-power` — correzione simulazione what-if BM2 PowerModel
- `fix-06-itinerary` — implementazione dominio itinerario
- `fix-07-connection` — centralizzazione token store, revoca OAuth
- `fix-08-heatmap` — aggregazione heatmap, bypass accesso
- `fix-09-badge` — persistenza DB sblocchi, store Pinia
- `fix-10-athlete` — completamento AthleteUpdate, vista profilo
- `fix-11-dashboard` — store Pinia sintesi, eliminazione chiamate duplicate
- `fix-12-ai-coach` — prompt builder versionato, soglie ACWR/TSB
- `fix-13-knowledge` — regole strutturate in knowledge.py, integrazione RAG
- `fix-14-calendar` — store Pinia calendar, confronto carico pianificato vs effettivo
- `fix-15-weather` — store Pinia weather, backfill meteo storico
- `fix-16-settings` — persistenza backend preferenze, binding utente
- `fix-17-compare` — endpoint confronto diretto ride, contesto meteo/percorso
- `fix-18-poi` — store Pinia POI, allineamento tipi, categoria caricabatterie
- `fix-19-import` — store import dedicato, deduplica upload GPX/FIT
- `fix-20-aethermap` — modelli Pydantic in data/, test sottosistemi

## Trust Rules

1. **no_self_verification** — nessun agente si verifica da sé. VERIFIER sempre indipendente.
2. **evidence_required** — PASS richiede evidenza concreta (output test, log, screenshot, HTTP status, query DB).
3. **regression_obligatory** — correzione non valida se introduce regressioni.
4. **reviewer_independent** — REVIEWER non accetta modifiche senza verifica indipendente.
5. **secret_scan_before_merge** — SECURITY vieta il merge se trova segreti.
6. **correlation_not_causation** — correlazione osservata non è causalità senza evidenza sufficiente.

## Livelli di Autonomia

| Livello | Comportamento | Quando |
|---|---|---|
| 0 | Analisi sola | Security audit, analisi legacy |
| 1 | Proposals | Richieste nuove, refactor ampi, decisioni architetturali |
| 2 | Modify + Test | Routine quotidiane (bug, feature) — **default** |
| 3 | Modify + Test + Merge | Fix non critici, dopo review |
| 4 | Controlled autonomy | "Porta a zero errori" con soglia |

Operazioni irreversibili o critiche richiedono approvazione umana (Lead Developer).

## Ciclo Cognitivo

```
GOAL
  ↓  UNDERSTAND       — cos'è la richiesta? area? bug noto?
  ↓  RETRIEVE         — LIBRARIAN: Project Map, Code Graph, Data Graph, docs, bug storici
  ↓  BUILD CONTEXT    — Context Package mirato
  ↓  PLAN             — TASK-XXX con assegnazione e dipendenze
  ↓  DELEGATE         — incarica gli agenti specializzati
  ↓  ACT              — gli agenti eseguono (modifiche, test, debug)
  ─────────────────────────────────────────────────
  ↓  OBSERVE          — Shared Event Log
  ↓  COLLECT EVIDENCE — log, output test, screenshot, tracciati, query DB
  ↓  ANALYZE          — confronta EXPECTED vs ACTUAL
  ↓  HYPOTHESIS       — DEBUGGER: 5-7 ipotesi, restringi a 1-2
  ↓  VERIFY           — VERIFIER indipendente: PASS / FAIL / INSUFFICIENT_EVIDENCE
  ↓  CORRECT          — fix minimale e mirato, con conferma utente (LEVEL 1)
  ↓
  ↓  TEST             — TESTER: casi normali + limite + differenziale
  ↓  REGRESSION       — target + related + global
  ↓  REVIEW           — REVIEWER: correttezza, architettura, regressioni
  ↓  VERIFICATION     — VERIFIER giudica
  ↓
  ↓  RECORD           — LIBRARIAN: bug DB, decision records, RAG, grafi
  ↓  LEARN            — estrai la lezione → RAG per recuperi futuri
  └─────────────────────────────────────────────────
  → prossimo task / NUOVA RICHIESTA
```

## Come avviare un agente

L'ORCHESTRATOR è il punto di ingresso del team. Il Lead Developer gli fornisce
un obiettivo (es. "Controlla l'app", "Trova perché il dashboard mostra valori
sbagliati") e l'ORCHESTRATOR avvia il ciclo cognitivo, delegando i task agli
agenti specializzati. Esistono due modalità di avvio:

### A) Avvio indiretto (via ORCHESTRATOR) — pattern consigliato

> Il Lead Developer formula un obiettivo. L'ORCHESTRATOR lo analizza,
> recupera contesto dal LIBRARIAN, pianifica TASK-XXX e delega.

```text
Lead Developer → ORCHESTRATOR → [LIBRARIAN context package]
  → PLAN (TASK-XXX)
  → DELEGATE → FRONTEND / BACKEND / DEBUGGER / TESTER / VERIFIER
  → OBSERVE (shared-log) → VERIFY → RECORD → LEARN
```

Questo è il modo normale: non serve indicare l'agente, basta l'obiettivo.

### B) Avvio diretto di uno specialista

Puoi richiedere direttamente un agente specializzato menzionandolo nella
richiesta. Gli agenti direttamente invocabili (hanno un `subagent_type`) sono:

| Agente | Invocazione tipica | Perimetro |
|---|---|---|
| FRONTEND | `@frontend` | Vue 3, Pinia, Tauri, PWA, test vitest |
| DEBUGGER | `@debug` / `@debug-piece` | Root cause su backend/frontend/test |
| SECURITY | `@security` | Audit, OWASP, segreti, dipendenze |
| DATABASE | `@database` o via BACKEND | Schema, query, migrazioni |
| CODE DOCUMENTER | `@code-documenter` | Docstring Python mancanti |
| CODE EXPLAINER | `@code-explainer` | Spiega codice e diff git |
| AL-SERVICE | `@al-service` | Avvio/troubleshooting backend |
| DOMINIO-* | `@domain-rides`, `@domain-athlete`, … | Esperti di dominio |
| FIX-* | `@fix-03-rides`, `@fix-08-heatmap`, … | Correzioni mirate |

> I 5 ruoli di coordinamento/suprastruttura (ORCHESTRATOR, ARCHITECT,
> LIBRARIAN, RELATION_ANALYZER, VERIFIER) non si avviano da soli: vengono
> attivati dal flusso del ciclo cognitivo quando l'ORCHESTRATOR li delega.

### Agent Contract (§47)

Ogni agente definisce nel suo file `.kilo/agent/<name>.md`:

- **INPUT** — qual è la richiesta/il task assegnato.
- **RESPONSABILITIES** — cosa deve fare (e non fare).
- **TOOLS** — strumenti a disposizione (shell, lettura/scrittura file, grep,
  browser, esecuzione codice).
- **OUTPUT** — formato atteso della risposta (report, diff, evidenza, PASS/FAIL).
- **SUCCESS CRITERIA** — quando il task è considerato completato.
- **LIMITATIONS** — vincoli irrinunciabili (es. "non toccare il flusso OAuth",
  "non introdurre dipendenze", "mai push --force").

### Comandi operativi (vedi `docs/agent/commands.md`)

```bash
# Avvio backend locale
python main.py api --port 8000          # FastAPI + SQLite su localhost:8000

# Test backend
pytest                                  # usa i marker di pytest.ini (esclude slow/integration)

# Frontend
cd frontend && npm run dev              # Vite dev server
cd frontend && npm run typecheck        # vue-tsc --noEmit
cd frontend && npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs ...   # lint (NO --fix globale)
cd frontend && npx vitest run           # test unitari one-shot
cd frontend && npm run e2e             # Playwright E2E
cd frontend && npm run tauri build      # build desktop
```

> **Nota operativa**: `eslint --fix` su tutto il progetto corrompe circolarmente
> alcuni file (nota in memoria progetto). Usare sempre `--ext` mirato o fix
> manuale. `uvicorn --reload` causa crash-loop su Windows — avviare senza `--reload`.

---

## Caso pratico: Zero-Error Loop sul frontend

Primo ciclo cognitivo eseguito dal team (SCAN → TEST → FIX → VERIFY → REGRESSION).

**Objective**: Portare il frontend a zero errori (Zero-Error Loop, §42).

**SCAN**
| Check | Strumento | Risultato |
|---|---|---|
| ESLint static analysis | `npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs` | 3 error (`no-unused-vars`) |
| Typecheck | `vue-tsc --noEmit --incremental` | 0 error |
| Backend tests (modified files) | `pytest tests/test_dashboard_auth.py` | 9 passed |
| Backend tests (modified files) | `pytest tests/test_metabolism_api.py` | 33 passed |

**BUGS FOUND — 3 variabili inutilizzate (dead code)**
- `appUrl` — `frontend/src/App.vue:235` (assegnata, mai letta)
- `shareOnLinkedIn` — `frontend/src/App.vue:249` (funzione definita, mai chiamata né in template)
- `backend` — `frontend/src/components/VoiceAssistant.vue:304` (assegnata a 328 e 335, mai letta)

**FIX** (agente FRONTEND) — rimozione minimale, mirata. Nessun cambiamento
comportamentale. Il flusso OAuth (`router/index.ts`, `stores/auth.ts`) è
rimasto intatto (verificato con grep: le variabili rimosse non erano referenziate
da nessun punto del flusso di autenticazione).

`git diff --stat`: **2 file, 17 deletions, 0 additions**.

**VERIFICATION** (agente VERIFIER, indipendente)
| Verifica | Evidenza | Esito |
|---|---|---|
| ESLint post-fix | `ESLINT_EXITCODE=0`, nessun output | PASS |
| Typecheck | nessun `error TS` | PASS |
| Regression frontend | `App.test.js` + `useAuth.test.js` + `ErrorBoundary.test.js` → 9/9 passed | PASS |

**RECORD** — 6 eventi scritti nel `shared-log.md` (TASK-SW-001).

**UNVERIFIED AREAS**: suite backend full (comprehensive/coverage/integration)
supera 240s — va eseguita in chunk separati per limite OOM. Frontend E2E
Playwright non ancora eseguito.

---

## Output Finale di una Sessione

1. OBJECTIVE
2. PLAN
3. AGENTS INVOLVED
4. FILES ANALYZED
5. FILES CHANGED
6. RELATIONS DISCOVERED
7. BUGS FOUND
8. ROOT CAUSES
9. FIXES
10. TESTS RUN / PASSED / FAILED
11. REGRESSION RESULTS
12. SECURITY FINDINGS
13. MEMORY UPDATED
14. UNVERIFIED AREAS
15. RECOMMENDATIONS

## Come Funziona il Team in Pratica

### 1. Ricezione dell'obiettivo

L'utente (Lead Developer) fornisce un obiettivo in linguaggio naturale:
- "Controlla l'app."
- "Trova perché il dashboard mostra valori sbagliati."
- "Porta il progetto a zero errori."
- "Analizza perché questo dato è sbagliato."

### 2. Pianificazione e delega

L'**ORCHESTRATOR** interpreta l'obiettivo e crea un piano strutturato:
- Identifica l'area coinvolta (frontend, backend, database, security)
- Assegna task specifici agli agenti specializzati
- Definisce dipendenze tra task

### 3. Esecuzione parallela

Gli agenti lavorano in parallelo secondo le loro competenze:
- Il **FRONTEND** analizza componenti Vue, store Pinia, router
- Il **BACKEND** ispeziona API, servizi, logica di business
- Il **DATABASE** verifica schema, query, migrazioni
- Il **SECURITY** controlla auth, OAuth, OWASP, segreti
- Il **TESTER** crea ed esegue test di regressione
- Il **DEBUGGER** riproduce e identifica root cause
- Il **REVIEWER** verifica indipendentemente le modifiche
- Il **VERIFIER** giudica PASS/FAIL con evidenza concreta

### 4. Osservazione e correzione

L'**ORCHESTRATOR** osserva il **Shared Event Log** e:
- Raccoglie evidenze da tutti gli agenti
- Confronta EXPECTED vs ACTUAL
- Decide correzioni minime e mirate
- Richiede conferma per operazioni critiche (LEVEL 1)

### 5. Verifica e chiusura

Il **VERIFIER** indipendente valuta:
- Tutti i test passano
- Nessuna regressione introdotta
- Nessun segreto nel codice
- Evidenza concreta documentata

### 6. Memoria e apprendimento

Il **LIBRARIAN** aggiorna:
- Bug database con ID tracciato
- Decision records (ADR)
- Code graph e data graph
- Lezioni estratte per RAG futuro

## Risultati Prodotti dal Team

Il team agentico ha prodotto risultati concreti, documentati in `.kilo/memory/` e nel codice:

### Sessione TASK-SW-001 — "Porta a zero errori"

**Ciclo cognitivo completato con successo.**

| Fase | Agente | Risultato |
|---|---|---|
| SCAN | ORCHESTRATOR | Identificati 3 errori ESLint (`no-unused-vars`) in `App.vue` e `VoiceAssistant.vue` |
| FIX | FRONTEND | Rimossi 3 variabili inutilizzate (dead code): `appUrl`, `shareOnLinkedIn`, `backend` |
| VERIFY | VERIFIER | ESLint exit=0, typecheck 0 error, vitest 9/9 pass |
| RECORD | LIBRARIAN | Evento registrato in `shared-log.md` |

**Evidenza:**
- `frontend/src/App.vue` — rimosso `appUrl` (235) e `shareOnLinkedIn` (249)
- `frontend/src/components/VoiceAssistant.vue` — rimosso `backend` (304 + assegnazioni 328, 335)
- `git diff --stat`: 2 file, 17 deletions, 0 additions (nessun file di test toccato in questa sessione)
- ESLint `ESLINT_EXITCODE=0`; typecheck senza `error TS`; vitest 9/9 pass
- 7 file `tests/test_*.py` + `BaseChart.vue` + `user_repository.py` erano modifiche non commit da sessioni precedenti (non TASK-SW-001); committate successivamente dal processo di background. La sessione TASK-SW-001 ha toccato solo `App.vue` e `VoiceAssistant.vue` (git diff --stat: 2 file, 17 deletions).

### Piani di Lavoro Generati

Il team ha prodotto piani di lavoro dettagliati per aree critiche:

| Piano | Focus | Status |
|---|---|---|
| `.kilo/plans/1783631660667-failing-tests-debug-plan.md` | Debug test frontend fallenti (Vitest) | Analisi completata |
| `.kilo/plans/1783635185916-codebase-analysis-plan.md` | Analisi completa codice + sicurezza | 21 findings, 8 priorità |
| `.kilo/plans/1783679954635-oauth-poi-fixes.md` | Fix OAuth flow + POI schemas | Piano definito |
| `.kilo/plans/1783767702728-aethermap-engine-agents.md` | Piano agenti AetherMap (5 fasi) | Struttura definita |
| `.kilo/plans/1783775540414-fix-camera-projection-globe.md` | Fix globe collapse AetherMap | Root cause identificata |

### Findings Critici Identificati

Dall'analisi codebase (piano `1783635185916`):

**Sicurezza (P1):**
- Open redirect OAuth via spoofing header `Origin` — whitelist statica implementata
- `refresh_token` usa `SECRET_KEY` grezza invece di `decode_token_with_fallback` — fix applicato
- `/sentry-debug` esposto in tutti gli ambienti — gated in produzione
- HSTS solo su `production`, mancante su `staging` — esteso
- Audit log usa IP socket invece di `X-Forwarded-For` — fix applicato

**Data Layer (P1):**
- `backend/db/models.py` inesistente ma importato — creato modelli SQLAlchemy
- `db/async_db.py` stub che ritorna `[]` — implementato path async/Postgres
- Modelli dominio duplicati (`core/models.py` vs `backend/models/`) — consolidati

**Frontend (P2):**
- Test i18n fragili (asseriscono su chiavi invece di testo) — documentato
- CI frontend senza test/typecheck/lint — aggiunti step in `ci.yml`

## Metriche del Team

| Metrica | Valore |
|---|---|
| Sessioni completate | 1 (TASK-SW-001) |
| Piani generati | 5 |
| Bug identificati | 21+ (piano codebase analysis) |
| Fix applicati (TASK-SW-001) | 3 ESLint unused-vars (appUrl, shareOnLinkedIn, backend) — 17 deletions, 0 additions |
| Test passati (sessione) | 9/9 Vitest |
| Documentazione creata | 17 file in `.kilo/` (9 agent core + 1 command + 6 memory + 1 manifest) + `docs/agent/team.md` aggiornato |

## Limitazioni Attuali

Il team è **infrastruttura pronta, utilizzo parziale**. La maggior parte del lavoro è stata svolta in modalità analisi e pianificazione. L'esecuzione autonoma di cicli completi (modifica + test + merge) richiede ancora integrazione con i workflow di sviluppo esistenti.

## File Correlati

- `.kilo/agent-manifest.md` — manifesto completo del team agentico
- `.kilo/command/software-team.md` — comando di orchestrazione del team AI
- `.kilo/agent/*.md` — istruzioni individuali per ogni agente
- `.kilo/memory/*` — memoria del team (shared-log, bug-database, project-map, ecc.)
- `.kilo/plans/*` — piani di lavoro generati dagli agenti
- `docs/agent/README.md` — indice documentazione agenti
