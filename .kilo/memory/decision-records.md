# Architecture Decision Records

Registro delle decisioni architetturali (§43 SELF-IMPROVEMENT, §45 DECISION).
Ogni decisione è tracciata con rationale, stato e data. Il LIBRARIAN la registra.

## Schema

```
ADR-XXXX

TITLE:        Breve titolo
STATUS:        PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED
CONTEXT:      Situazione che richiede una decisione (problema)
DECISION:     Cosa è stato deciso
RATIONALE:    Perché questa scelta (pro/contro, trade-off)
CONSEQUENCES: Impatto (pozitivo/negativo)
EVIDENCE:     Fonti, test, dati a supporto
AUTHOR:       Agente/Utente (es. ARCHITECT, ORCHESTRATOR)
CREATED_AT:   ISO 8601
SUPERSEDED_BY: ADR-XXXX (se sostituita)
```

## Registry

> Popolata dal LIBRARIAN. Alcune decisioni chiave già note del progetto:

- **DECISION** (da `project.md`): Render hosts only the cloud backend (FastAPI
  Docker + managed PostgreSQL); frontend remains on Vercel. (§ render_cloud_backend_only)
- **DECISION**: Tauri 2 è la piattaforma desktop primaria (effettivo 2026-07-15).
- **DECISION**: Backend locale SQLite porta 8000; no ngrok necessario in dev.
- **DECISION**: Backend locale vs cloud hub module — instradamento
  SQLite↔PostgreSQL basato su `DATABASE_URL`.
- **DECISION**: Le modifiche al flusso OAuth in `router/index.ts` e
  `stores/auth.ts` richiedono conferma esplicita.

## Stati (§45)

- **PROPOSED** — in discussione, non ancora accettata.
- **ACCEPTED** — approvata, in vigore.
- **SUPERSEDED** — sostituita da una decisione più recente.
- **DEPRECATED** — ritirata, non più valida.

(nuove decisioni vengono aggiunte qui dal LIBRARIAN)
