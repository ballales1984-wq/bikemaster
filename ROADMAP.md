# BikeMaster — Roadmap Consolidata

*Ultimo aggiornamento: 2026-07-12*

> Stato: **Late Beta / Early Production** (multi-tenant completato, deploy su Render stabile).
> Questo documento è la *fonte di verità* unica per le idee/feature. Le fasi 1-25
> sono completate; sotto il backlog riordinato (3 track) e lo stato di pulizia repo.

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
| Frontend | Vitest + Playwright E2E | ✅ |
| Security | Security headers + rate limiting | ✅ |
| Database | Dual-mode SQLite/PostgreSQL | ✅ |
| CI/CD | GitHub Actions | ✅ |
