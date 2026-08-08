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

(vuota — popolata dal LIBRARIAN durante le sessioni)
