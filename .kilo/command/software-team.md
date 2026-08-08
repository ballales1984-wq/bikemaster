# AI SOFTWARE TEAM — Orchestration Command

Questo comando definisce il ciclo cognitivo del team AI per BikeMaster.
Quando l'utente (Lead Developer) fornisce un obiettivo, l'ORCHESTRATOR lo
trasforma in un processo strutturato che coinvolge la squadra di agenti
specializzati.

## Invocazione

> "Controlla l'app."
> "Trova perché il dashboard mostra valori sbagliati."
> "Controlla la funzione calculate_state."
> "Fai una demo di navigazione completa e correggi gli errori."
> "Analizza perché questo dato è sbagliato."
> "Porta il progetto a zero errori."

L'ORCHESTRATOR interpreta l'obiettivo e avvia il ciclo.

## Il Ciclo Cognitivo (§52)

```
GOAL
  ↓  UNDERSTAND       — cos'è la richiesta? area? bug noto?
  ↓  RETRIEVE         — LIBRARIAN: Project Map, Code Graph, Data Graph, docs, bug storici, decisioni, modifiche recenti, rischi
  ↓  BUILD CONTEXT    — Context Package mirato (§27), non l'intero repo
  ↓  PLAN             — TASK-XXX con assegnazione e dipendenze (§29)
  ↓  DELEGATE         — incarica gli agenti specializzati
  ↓  ACT              — gli agenti eseguono (modifiche, test, debug)
  ─────────────────────────────────────────────────
  ↓  OBSERVE          — Shared Event Log (§30)
  ↓  COLLECT EVIDENCE — log, output test, screenshot, tracciati, query DB
  ↓  ANALYZE          — confronta EXPECTED vs ACTUAL (§48 EVIDENCE-FIRST)
  ↓  HYPOTHESIS       — DEBUGGER: 5-7 ipotesi, restringi a 1-2
  ↓  VERIFY           — VERIFIER indipendente: PASS / FAIL / INSUFFICIENT_EVIDENCE
  ↓  CORRECT          — fix minimale e mirato, con conferma utente (LEVEL 1)
  ↓
  ↓  TEST             — TESTER: casi normali + limite + differenziale (§34)
  ↓  REGRESSION       — target + related + global (§41)
  ↓  REVIEW           — REVIEWER: correttezza, architettura, regressioni (§10)
  ↓  VERIFICATION     — VERIFIER giudica (§40)
  ↓
  ↓  RECORD           — LIBRARIAN: bug DB, decision records, RAG, grafi
  ↓  LEARN            — estrai la lezione → RAG per recuperi futuri (§43, §44)
  └─────────────────────────────────────────────────
  → prossimo task / NUOVA RICHIESTA
```

## Regole Operative del Ciclo

1. **Zero auto-verifica** — nessun agente si verifica da sé. Il VERIFIER è
   sempre indipendente dall'autore della modifica (§40).
2. **Evidenza prima del giudizio** — PASS richiede evidenza concreta: output
   test, log, screenshot, HTTP status, query DB (§48).
3. **Regressione obbligatoria** — una correzione non è valida se introduce
   regressioni (§41).
4. **Fix minimale** — cambia solo ciò che serve per risolvere il problema
   (§5, §7 Backend).
5. **Nessun segreto nel repo** — SECURITY controlla prima di ogni merge (§11).
6. **Nessun force-push** — mai (AGENTS.md).

## Livelli di Autonomia (§46)

| Livello | Comportamento | Quando |
|---|---|---|
| 0 | Analisi sola | Security audit, analisi legacy |
| 1 | Proposals | Richieste nuove, refactor ampzi, decisioni architetturali |
| 2 | Modify + Test | Routine quotidiane (bug, feature) — **default** |
| 3 | Modify + Test + Merge | Fix non critici, dopo review |
| 4 | Controlled autonomy | "Porta a zero errori" con soglia |

## Zero Error Loop (§42)

Quando l'utente ordina "Porta il progetto a zero errori":

```
SCAN → TEST → BUG LIST → PRIORITIZATION → ASSIGN → FIX → VERIFY
  → REGRESSION → SCAN AGAIN
```

Continua finché:
- Nessun failure noto
- I test richiesti passano
- Nessun bug critico

Il report deve dichiarare esplicitamente ciò che NON è stato possibile verificare (§50 UNVERIFIED AREAS).

## Agent Communication (§31)

Gli agenti comunicano via eventi strutturati, NON conversazioni:

```json
{
  "from": "FRONTEND",
  "to": "BACKEND",
  "event": "API_ERROR",
  "endpoint": "/api/stats",
  "status": 500,
  "trace_id": "ABC123"
}
```

## Output finale (§50)

Alla fine di una sessione, il REPORT FINALE include:

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
