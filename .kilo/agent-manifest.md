# Agent Manifest — AI SOFTWARE TEAM

Questo manifesto lega i **12 ruoli core** (§53) ai contratti della Project
Memory (§21, §27, §30, §40, §45). È il punto di riferimento per
l'ORCHESTRATOR quando delega e per il LIBRARIAN quando mantiene la memoria.

- **Progetto**: BikeMaster
- **Radice memoria**: `.kilo/memory/`
- **Visione**: Un ambiente software nel cui una squadra di agenti specializzati
  possiede memoria, strumenti, conoscenza strutturata, capacità di osservazione
  e sistemi indipendenti di verifica. (§2)

## Roster core

| Ruolo | Agent file | Responsabilità | Possiede memoria | Pubblica eventi |
|---|---|---|---|---|
| **ORCHESTRATOR** | `.kilo/agent/orchestrator.md` | Coordinatore principale: riceve obiettivo, comprende, pianifica, delega, osserva, decide quando fermarsi. (§4) | `shared-log.md` | `TASK_CREATED`, `TASK_ASSIGNED`, `CONFLICT`, `SESSION_END` |
| **ARCHITECT** | `.kilo/agent/architect.md` | Visione globale architettura, conseguenze di modifiche. (§5) | `code-graph.md` | `IMPACT_REPORT`, `ARCH_ADR_PROPOSED` |
| **FRONTEND** | `.kilo/agent/frontend.md` | Vue 3, Pinia, Router, Vite, Tauri WebView, PWA, test, browser automation. (§7, 32) | — | `API_ERROR`, `UI_BUG`, `BROWSER_RESULT`, `TEST_PASS/FAIL`, `FIX_APPLIED` |
| **BACKEND** | `.kilo/agent/backend.md` | API, servizi, business logic, auth/OAuth, validazione, integrazioni, gestione errori. (§6) | — | `API_ERROR`, `ROOT_CAUSE_FOUND`, `FIX_APPLIED`, `TEST_PASS/FAIL` |
| **DATABASE** | `.kilo/agent/database.md` | Schema, tabelle, query, migrazioni, integrità, performance, coerenza codice↔DB. (§8) | — | `SCHEMA_CHANGED`, `MIGRATION_APPLIED`, `DATA_ANOMALY`, `INTEGRITY_OK` |
| **TESTER** | `.kilo/agent/tester.md` | Creazione/esecuzione test, casi limite, regressione, differential verification. (§9, 34, 41) | `bug-database.md` | `TEST_PASS/FAIL/SKIP`, `REGRESSION_PASS/FAIL`, `DIFF_VERIFY_*` |
| **DEBUGGER** | `.kilo/agent/debug.md` | Ricerca root cause (riproduci → ipotesi → verifica → correggi → testa). (§10) | `bug-database.md` | `BUG_FOUND`, `ROOT_CAUSE_FOUND`, `FIX_APPLIED`, `REPRODUCE_*` |
| **SECURITY** | `.kilo/agent/security.md` | Auth/OAuth, OWASP, injection, segreti, dipendenze, configurazioni, esposizione dati. (§11) | — | `SECRET_FOUND`, `VULN_FOUND`, `AUDIT_DONE`, `OWASP_RISK`, `DEP_VULN` |
| **REVIEWER** | `.kilo/agent/reviewer.md` | Verifica indipendente di modifiche altrui: correttezza, qualità, architettura, regressioni. (§10) | — | `REVIEW_PASS/FAIL/NEEDS_CHANGES` |
| **LIBRARIAN** | `.kilo/agent/librarian.md` | Custode memoria tecnica: RAG, Project Map, Code Graph, Data Graph, docs, bug DB, decision records, log, lezioni. (§13) | tutti i file di memoria | `MEMORY_UPDATED`, `CONTEXT_PACKAGED`, `BUG_ID_ASSIGNED`, `LEARNING_INDEXED` |
| **RELATION_ANALYZER** | `.kilo/agent/relation.md` | Grafo relazioni variabili, data lineage, impatto, causalità, formule. (§14) | `data-graph.md` | `LINEAGE_TRACED`, `IMPACT_REPORT`, `RELATION_VERIFIED`, `HYPOTHESIS_RAISED` |
| **VERIFIER** | `.kilo/agent/verifier.md` | Verifica indipendente: PASS / FAIL / INSUFFICIENT_EVIDENCE, con evidenza. (§12, 40) | `bug-database.md`, `shared-log.md` | `VERIFICATION_PASS/FAIL`, `INSUFFICIENT_EVIDENCE`, `REGRESSION_REQUESTED` |

## Trust Rules (§40, §48, §49)

1. **no_self_verification** — Nessun agente si verifica da sé (§40). Il VERIFIER è
   sempre indipendente dall'autore della modifica.
2. **evidence_required** — PASS richiede evidenza concreta: output test, log,
   screenshot, HTTP status, query DB (§48).
3. **regression_obligatory** — Una correzione non è valida se introduce
   regressioni (§41).
4. **reviewer_independent** — Il REVIEWER non accetta modifiche senza verifica
   indipendente (§10).
5. **secret_scan_before_merge** — SECURITY vira il merge (§11).
6. **correlation_not_causation** — Una correlazione osservata non è causalità
   senza evidenza sufficiente (§49).

## Livelli di Autonomia (§46)

| Livello | Comportamento | Quando |
|---|---|---|
| 0 | Analisi sola | Security audit, analisi legacy |
| 1 | Proposals | Richieste nuove, refactor ampzi, decisioni architetturali |
| 2 | Modify + Test | Routine quotidiane (bug, feature) — **default** |
| 3 | Modify + Test + Merge | Fix non critici, dopo review |
| 4 | Controlled autonomy | "Porta a zero errori" con soglia |

Operazioni irreversibili o critiche richiedono approvazione umana (Lead Developer).

## Agenti correlati (domain + fix)

Oltre ai 12 ruoli core, il progetto possiede agenti specialistici di dominio
e agenti di fix che operano sotto la guida dell'ORCHESTRATOR:

- `.kilo/agent/debug-piece.md` — debug pezzo per pezzo
- `.kilo/agent/al-service.md` — service & operations (boot, troubleshooting)
- `.kilo/agent/code-documenter.md` — documentazione Python
- `.kilo/agent/code-explainer.md` — spiega codice e diff git
- `.kilo/agent/frontend-alignment.md` — allineamento frontend PC ↔ mobile
- `.kilo/agent/adaptation-engine.md` — motore di adattamento carico
- `.kilo/agent/load-manager.md` — calcolo TSS, ACWR, CTL/ATL/TSB
- `.kilo/agent/domain-rides.md` e altri `domain-*` — esperti di dominio
- `.kilo/agent/fix-01-maps-security.md` ... `fix-20-aethermap.md` — correzioni mirate

## Event Log contract (§30, §31)

Tutti gli agenti pubblicano eventi nello stesso formato in `memory/shared-log.md`:

```
timestamp | agent | task | event_type | description | evidence | files | result | status
```

La comunicazione è orientata all'esecuzione: niente conversazioni inutili.
