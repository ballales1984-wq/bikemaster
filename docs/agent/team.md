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

## File Correlati

- `.kilo/agent-manifest.md` — manifesto completo del team agentico
- `.kilo/command/software-team.md` — comando di orchestrazione del team AI
- `.kilo/agent/*.md` — istruzioni individuali per ogni agente
- `.kilo/memory/*` — memoria del team (shared-log, bug-database, project-map, ecc.)
