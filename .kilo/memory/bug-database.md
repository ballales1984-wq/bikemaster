# Bug Database

Registro dei bug (§37). Ogni bug ha un ID univoco `BUG-XXXX`.
Il LIBRARIAN assegna gli ID e traccia gli stati.

## Schema

```
BUG-XXXX

TITLE:        Breve descrizione
DESCRIPTION:   Dettaglio del problema (cosa succede, cosa atteso)
REPRO:         Passi per riprodurre (comando, input, stato)
EVIDENCE:       Evidenza concreta (file:line, log, output, screenshot)
ROOT_CAUSE:    Cause radice identificata (o "INVESTIGATING")
FILES:         File coinvolti (file:line)
FIX:           Correzione applicata (diff o descrizione)
TESTS:         Test aggiunti/aggiornati (file:line)
STATUS:        OPEN | INVESTIGATING | ROOT_CAUSE_FOUND | FIXED | VERIFYING | RESOLVED | REOPENED
CREATED_AT:    ISO 8601
RESOLVED_AT:    ISO 8601 (se risolto)
OWNER:         Agente principale (es. DEBUGGER)
VERIFIER:      Agente che ha verificato (se FIXED)
```

## Stati (§37)

- **OPEN** — bug appena segnalato, non ancora iniziato.
- **INVESTIGATING** — DEBUGGER sta lavorando alla root cause.
- **ROOT_CAUSE_FOUND** — causa radice identificata, attesa fix.
- **FIXED** — correzione applicata, in attesa verifica.
- **VERIFYING** — VERIFIER sta verificando.
- **RESOLVED** — verificato e chiuso.
- **REOPENED** — verifica fallita o regressione.

## Registry

> Popolata dal LIBRARIAN. Ogni BUG-XXXX è assegnato, tracciato e aggiornato.

(nessun bug registrato — popolato durante le sessioni)

## Priorità

Il LIBRARIO/ML-clusterer assegna priorità in base a:

- **critical** — crash, perdita dati, vulnerabilità sicurezza.
- **high** — errore funzionale bloccante.
- **medium** — bug con workaroun, test falliti non critici.
- **low** — refactoring, tech debt, documentazione.
