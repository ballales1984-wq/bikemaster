# Shared Event Log

Log eventi strutturato condiviso da tutti gli agenti (§30). L'ORCHESTRATOR
osserva questo log per prendere decisioni in tempo reale.

## Formato di un evento

```
timestamp | agent | task | event_type | description | evidence | files | result | status
```

| Campo | Descrizione |
|---|---|
| timestamp | ISO 8601 |
| agent | nome agente (FRONTEND, BACKEND, DATABASE, TESTER, DEBUGGER, SECURITY, REVIEWER, LIBRARIAN, RELATION, VERIFIER, ARCHITECT, ORCHESTRATOR) |
| task | TASK-XXX (vedi bug-database / task registry) |
| event_type | BUG_FOUND, ROOT_CAUSE_FOUND, FIX_APPLIED, API_ERROR, TEST_PASS, TEST_FAIL, TEST_SKIP, REGRESSION_FAIL, VERIFICATION_PASS, VERIFICATION_FAIL, MEMORY_UPDATED, CONFLICT, DEPLOY, AUDIT_DONE |
| description | descrizione breve dell'evento |
| evidence | riferimento a evidenza concreta (file:line, log, URL, screenshot) |
| files | file coinvolti |
| result | PASS / FAIL / SKIP / INSUFFICIENT_EVIDENCE / N/A |
| status | OK / BLOCKED / ATTENTION |

## Esempi (§30)

```
10:20 | FRONTEND | TASK-042 | API_ERROR        | GET /api/stats → HTTP 500                 | logs/errors.log:12  | api/stats.py     | FAIL   | ATTENTION
10:24 | BACKEND  | TASK-042 | BUG_FOUND        | KeyError: calories in calculate_stats   | bike_analyzer/analytics/stats.py:78 | stats.py | FAIL | OK
10:28 | RELATION | TASK-042 |                  | calories dipende da missing field 'weight'| data-graph.md | models.py | FAIL | OK
10:32 | DEBUGGER | TASK-042 | ROOT_CAUSE_FOUND | weight_kg non popolato su import FIT    | import.py:203 | import.py | - | OK
10:36 | BACKEND  | TASK-042 | FIX_APPLIED      | validation aggiunta su import weight_kg  | import.py:203 | import.py | PASS | OK
10:40 | TESTER   | TASK-042 | TEST_PASS        | tests/test_stats.py 4/4 pass            | tests/test_stats.py | - | PASS | OK
10:44 | VERIFIER | TASK-042 | VERIFICATION_PASS | regression: 12/12 pass, no new secrets    | - | - | PASS | OK
```

## Stato del log

> Il LIBRARIAN mantiene aggiornato questo file registrando gli eventi emersi
> durante le sessioni. La sezione "Eventi recenti" sotto è popolata
> automaticamente.

## Eventi recenti

```
01:56 | ORCHESTRATOR | TASK-SW-001 | SCAN_STARTED       | Ciclo cognitivo Zero-Error (§42) avviato: SCAN → TEST → FIX → VERIFY | .kilo/command/software-team.md | - | - | OK
01:57 | ORCHESTRATOR | TASK-SW-001 | SCAN_COMPLETE      | ESLint 3 error, typecheck 0 error, backend test_dashboard_auth 9p, test_metabolism_api 33p | frontend/src/App.vue:235, VoiceAssistant.vue:304 | FAIL | ATTENTION
01:58 | FRONTEND       | TASK-SW-001 | LINT_ERROR_FOUND   | 3 no-unused-vars: appUrl (App.vue:235), shareOnLinkedIn (App.vue:249), backend (VoiceAssistant.vue:304) | npx eslint output | App.vue, VoiceAssistant.vue | FAIL | OK
01:59 | FRONTEND       | TASK-SW-001 | FIX_APPLIED        | Rimossi 3 variabili inutilizzate (dead code); nessun cambiamento comportamentale; flusso OAuth intatto | git diff: 17 deletions, 0 additions | App.vue, VoiceAssistant.vue | PASS | OK
02:01 | VERIFIER       | TASK-SW-001 | VERIFICATION_PASS  | ESLint exit=0 (0 error); typecheck nessun error TS; vitest App+auth+ErrorBoundary 9/9 pass | eslint/VITEST_EXITCODE=0 | same | PASS | OK
02:01 | ORCHESTRATOR   | TASK-SW-001 | SESSION_END        | Primo ciclo completato. Frontend lint a 0 error. Obiettivo "Porta a zero errori" in corso. | - | - | - | OK
```
