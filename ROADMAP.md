# BikeMaster — Roadmap Consolidata

*Ultimo aggiornamento: 2026-07-13*

> Stato: **Production Ready** (multi-tenant completato, deploy su Render stabile).
> Numeri verificati: backend 108 file / 1674 test · frontend 47 file / 318 test · 138 endpoint REST.
> Questo documento è la *fonte di verità* unica per stato, checklist e idee/feature.
> Le fasi 1-25 sono completate; sotto il backlog riordinato (4 track) e lo stato di pulizia repo.

---

## Track A — BikeMaster (prodotto)

### A.1 Stato di completamento
- **Fasi 1-25**: completate (fondamenta, analytics, AI Coach base, sicurezza,
  testing/DevOps, phone GPS tracking, event-driven/clean arch, vector DB/RAG).
- Conteggio storico: 145/145 base + 78/80 estensioni.

### A.2 Backlog riordinato per priorità
Ordine: stabilità → mobile nativo → maturità AI → distribuzione/integrazioni.

| ID | Idea | Fascia | Stato |
|:--:|---|---|:--:|
| P0.1 | Logging centralizzato e strutturato | Stabilità | 🔄 |
| P0.2 | Servizi registrati nel lifespan FastAPI | Stabilità | 🔄 |
| P1.1 | Verifica build iOS con Xcode su dispositivo | Mobile nativo | 🔄 |
| P1.2 | Voice input/output AI Coach + prompt engineering avanzato | Mobile nativo | ❌ |
| P2.1 | Memory persistente conversazioni per utente | AI Coach | 🔄 |
| P2.2 | Design System + theme tokens | AI Coach | 🔄 |
| P3.1 | Wahoo integration | Distribuzione | ✅ |
| P3.2 | Versione cloud hosted (Render/Azure/Fly/Railway/Vercel) | Distribuzione | ✅ |
| P3.3 | Helm chart Kubernetes | Distribuzione | ✅ |
| P3.4 | One-click deploy docs (Railway/Fly/Vercel) | Distribuzione | ✅ |
| P3.5 | Coverage test >90% come metrica informativa | Qualità | 🔄 |

---

## Track B — AetherMap (R&D, progetto separato mantenuto)

Motore cartografico "dal nulla" (cube-sphere + S2/H3, data model, pipeline IA
"ricercatore", rendering WebGL, digital twin). Indipendente da BikeMaster, ma
tracciato in questo repo (`aethermap/`, agent `.kilo/agent/aethermap-*.md`).
Catena di dipendenze: **1 → 2 → {3,4} → 5**.

| ID | Fase | Stato |
|:--:|---|:--:|
| AM1 | Fase 1 — Earth model (cube-sphere + S2/H3): doc + `core/coordinates.py` | ✅ baseline |
| AM2 | Fase 2 — Data model ("database del mondo"): doc + `data/` | ✅ baseline |
| AM3 | Fase 3 — AI pipeline "ricercatore": `ai/` | 🔄 in corso |
| AM4 | Fase 4 — Rendering WebGL: `render/` | 🔄 in corso |
| AM5 | Fase 5 — Digital twin: `twin/` | 🔄 in corso |

Demo: `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`.

---

## Track D — BikeMaster 2.0 / Deluxe Simulation Engine (`bm2`)

Motore di simulazione sportiva ("what-if") già presente in `bike_analyzer/bm2/`,
con filosofia type-safe (`Quantity` + `UnitRegistry` con analisi dimensionale,
algoritmi `Algorithm`→`ModelResult`, dominio `AnalysisContext`). È **già cablato**
via `bm2_routes.py` (montato in `app_factory.py`). La visione "BikeMaster Deluxe"
è documentata in `docs/DELUXE_ROADMAP.md`.

Catena: kernel fisico (`core/physics`) → algoritmi (`bm2/algorithms`) →
`SimulationEngine` (what-if/preset/sensitivity) → `AIOrchestrator` (agenti NL).
Il forward model fisico è **condiviso** (`bm2` delega a `core.physics`, fusione
2026-07-12).

| ID | Modulo | Stato |
|:--:|---|---|
| D1 | `core/physics/` — kernel numerico unico (`cycling_forces`, `instantaneous_power`, `required_speed_for_power`, `grade_between`) | ✅ consolidato |
| D2 | `bm2/algorithms/` — 9 algoritmi (power, energy, fatigue, performance, recovery, nutrition, movement, route_difficulty, training_load) | ✅ baseline |
| D3 | `bm2/simulation.py` — `SimulationEngine` (compare/preset/sensitivity) + `parse_override_from_text` | ✅ baseline |
| D4 | `bm2/orchestrator.py` — `AIOrchestrator` + agenti (Athlete/Environment/GPS/Sensor) | ✅ baseline |
| D5 | `bm2/units.py` — `Quantity` + `UnitRegistry` (analisi dimensionale) | ✅ baseline |
| D6 | `bm2_routes.py` — endpoint API esposti | ✅ cablato |
| D7 | Integrazione col flusso `Ride`/analytics esistente (via `bm2/adapters.py` + `POST /api/v1/bm2/simulate-ride`) | ✅ completato |
| D8 | Validazione su dati reali (potenza/HR misurate) via `core/physics/validation.py` + `POST /api/v1/bm2/validate` | ✅ completato |
| D9 | Documentazione `bm2` in `PROJECT_STATUS.md` + `AGENTS.md` | ✅ completato |

---

## Track C — Pulizia repo (stato)

### C.1 Completato in questa sessione
- [x] Rimosso debris non tracciato: `frontend/android_bak/`, `frontend/android_temp/`, `.sixth/`.
- [x] Eliminati branch locali fusi: `android-fix`, `chain-pomelo`.
- [x] Eliminato branch scratch `temp-security-fix-tmp` (security hardening già in main, item 15).
- [x] `AGENTS.md` aggiornato per documentare AetherMap come track R&D.
- [x] ROADMAP.md riorganizzato in 3 track con numerazione corretta.
- [x] Documentazione obsoleta IT spostata in `docs/archive/obsolete/`.
- [x] `config.py` legacy rimosso (v1.4.1).

### C.2 Branch non-fusi aperti (da revisionare, NON eliminati — contengono lavoro)
| Branch | Contenuto | Azione suggerita |
|---|---|---|
| `chore/sistema-repo` | Cleanup temp files + DB layer (async/postgres/vector) + fix Dockerfile | Revisionare e fare merge |
| `feature/core-engine-refactor` | Core engine refactor, Google Fit/OAuth, PGVector RAG, Ollama | Revisionare (ampio) |
| `fix/frontend-assets` | Asset frontend prebuild per deploy Render | Revisionare/merge |
| `inconclusive-pastry` | Progressi AetherMap (camera projection, SVO, ASCII render) — in worktree | Mantenere (AetherMap) |

### C.3 Da fare (richiede conferma/permessi)
- [ ] **Prune remote-tracking obsoleti** (`codex/esamina-il-codice`, `cloudy-tower`,
      `loud-paste`, `docker-create-production-dockerfile`, `models-consolidate-domain-models`,
      `security-add-auth-to-endpoints`, `bm2-*`) — richiede `git push` (conferma utente).
- [ ] Merge/review dei branch in C.2.

---

## Production Ready Checklist
| Area | Item | Stato |
|---|---|---|
| Testing | Coverage reported as informational | ✅ |
| Code Quality | Ruff + mypy + pre-commit | ✅ |
| Container | Docker multi-stage hardened | ✅ |
| Monitoring | Sentry + Prometheus + Grafana | ✅ |
| Audit | Audit log azioni admin | ✅ |
| Auth | OAuth2 social login (Google, Strava) | ✅ |
| Multi-user | Data isolation completa | ✅ |
| AI | Vector DB per RAG | ✅ |
| Frontend | PWA + offline support | ✅ |
| Frontend | Vitest (47 file / 318 test) | ✅ |
| Frontend | Playwright E2E (`frontend/tests/e2e`, 14 spec esistenti + 3 aggiunti backend-independent) | ✅ |
| Security | Security headers + rate limiting | ✅ |
| Database | Dual-mode SQLite/PostgreSQL | ✅ |
| CI/CD | GitHub Actions | ✅ |
