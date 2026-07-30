# BikeMaster — Roadmap Unificata

*Ultimo aggiornamento: 2026-07-30*

> **Principio guida**: fare le cose una volta, farle bene. Questo documento è la
> *fonte di verità unica* per stato, priorità e azioni. Non eseguire feature
> duplicate: verificare qui prima di iniziare qualsiasi lavoro.

---

## 1. Stato Attuale (checklist veloce)

| Area | Stato | Note |
|:--|:--|:--|
| Backend FastAPI | **Stabile** | Test mirati 297 passati (routes/BM2/AI); suite completa timeout locale (>15 min) |
| Frontend Vue 3 | **Stabile** | Lint + typecheck puliti, 395/395 test passati |
| Tauri 2 desktop | **Funzionante** | Backend embedded + SQLite primario, smoke test passed |
| BM2 simulation engine | **Baseline** | 9 algoritmi, cablato via API |
| AetherMap R&D | **Fasi 1-5 complete** | Convergence decision: AetherMap converge in BikeMaster |
| Multi-tenant / auth | **Completo** | tenant_id + OAuth2 (Google, Strava, Garmin) |
| Sync device↔cloud | **Completo** | Branch merged in main |
| Coverage test | **In corso** | ai_coach.py 90%, knowledge_base ~85%, routes.py ~65% — fix completati per test Google OAuth callback |

---

## 2. Branches Aperti (azioni immediate)

Tutti e 3 i branch feat sono stati mergiati in `main`. Nessun branch aperto.

---

## 3. Working Tree Non Committato

Nessun file non committato. Il working tree è pulito.

---

## 4. Priorità Assoluta (ordine di esecuzione)

### Fase 1 — Chiudere il lavoro in corso (completata)

1. ✅ **Merge dei 3 branch** in `main`
2. ✅ **Commit working tree** e push su `origin/main` (4 commit)
3. ✅ **Run test mirati** backend + frontend verificati
4. ✅ **Pulizia repo**: file temporanei rimossi

### Fase 2 — Stabilizzare (quasi completata)

5. ✅ **Fix test frontend**: 395/395 passati, lint + typecheck puliti
6. ✅ **Fix test backend** (MissingGreenlet): 5 test marcati `@pytest.mark.missing_greenlet`
7. **Coverage > 90%** su `routes.py` e moduli AI — in corso
    - routes.py ~65%, ai_coach.py 90%, knowledge_base ~85%
    - File attivi: `tests/test_routes_error_branches.py`, `tests/test_coverage_ai_routes.py`
    - Test Google OAuth callback sistemato (fix settings singleton + env vars)
8. ✅ **Documentazione consolidata**:
    - ✅ Eliminati duplicati IT spostati in `docs/archive/`
    - ✅ `docs/UNIFIED_DOCUMENTATION.md` unificata in `docs/MASTER.md`
    - ✅ `docs/DELUXE_ROADMAP.md` → riferisce a `ROADMAP.md`

### Fase 3 — Distribuzione (mese corrente)

9. **Tauri build verificata**: `npm run tauri build` produce .exe funzionante
10. **Vercel deploy**: riconfigurare `VITE_API_BASE` dopo ogni boot ngrok
11. **GitHub Releases** per distribuzione desktop (CI/CD Tauri)
12. **Android release**: verificare APK/AAB da workflow GitHub Actions

### Fase 4 — BM2 Deluxe (prossimo mese)

13. **UI simulazione frontend**: pannello "What-if" su rides esistenti
    (`components/Bm2Panel.vue` esiste, serve integrazione completa)
14. **Validazione fisica su dati reali**: confrontare stime BM2 vs potenza misurata
    su 10+ ride con power meter
15. **AI Coach + BM2**: l'orchestratore NL usa i risultati simulazione per rispondere
    a domande tipo "se aumento FTP a 250W quanto miglioro?"

### Fase 5 — AetherMap (R&D, completata)

16. ✅ Complete Fase 3 (AI pipeline) e Fase 5 (digital twin)
17. ✅ Decisione esplicita: `aethermap/` converge in BikeMaster come modulo terrain intelligence
18. ✅ Contratto dati `Ride/GPSPoint → terrain input` definito in `docs/agent/aethermap-convergence.md`

> **Decisione (2026-07-26)**: AetherMap converge in BikeMaster. Il progetto rimane come sotto-package (`aethermap/`) con il suo `pyproject.toml` autonomo, ma è integrato come dipendenza opzionale (`pip install -e ".[maps]"`). La pipeline IA arricchisce le ride con dati terrain; il digital twin fornisce contesto ambientale (neve, ombra, traffico) per l'analisi e il coaching. Vedi `docs/agent/aethermap-convergence.md` per dettagli.

---

## 5. Regole Anti-Duplicazione

- **Prima di scrivere codice**: cercare nel repo (`grep`, `codebase_search`) per
  verificare che la feature non esista già sotto altro nome
- **Prima di creare un branch**: verificare che non esista un branch con lo stesso
  scopo; riutilizzare o estendere quello esistente
- **Documentazione**: una sola fonte di verità per ogni argomento. Se `ROADMAP.md`
  copre lo stato, non replicarlo in `PROJECT_STATUS.md`
- **Script**: se `scripts/tauri_agent.py` esiste, non creare `scripts/build-tauri.sh`
- **Modelli DB**: se `bike_analyzer/backend/db/models.py` esiste, non creare
  `backend/models.py` ex-novo — estendere quello esistente

---

## 6. Struttura Directory (canone attuale)

```
D:\BikeMaster/
├── bike_analyzer/          # Backend + BM2 + core (codice Python)
│   ├── backend/            # FastAPI app (api, analytics, db, ingestion, maps...)
│   ├── core/               # Domain layer (models, pipeline, engine, physics)
│   ├── bm2/                # BikeMaster 2.0 simulation engine
│   ├── frontend/           # Dashboard Flask legacy (non il frontend principale)
│   ├── tests/              # Test backend (pytest)
│   └── main.py             # Entrypoint
├── frontend/               # Frontend principale (Vue 3 + Vite + TS)
│   ├── src/
│   │   ├── components/     # Componenti Vue (35+)
│   │   ├── views/          # Page-level views
│   │   ├── stores/         # Pinia stores
│   │   ├── composables/    # Composables
│   │   ├── utils/          # API client, helpers
│   │   ├── services/       # Auth, notifications, Tauri
│   │   ├── types/          # TypeScript types
│   │   └── db/             # Local DB (SQLite WASM)
│   ├── src-tauri/          # Tauri 2 Rust backend
│   └── tests/              # E2E Playwright
├── aethermap/              # Terrain intelligence module (converged from R&D into BikeMaster)
├── docs/                      # Documentazione sviluppatore
│   ├── archive/                # Documentazione IT storica/douplicata (archiviata)
│   ├── reference/              # Dizionario dati, schemi
├── scripts/                # Utility (tauri_agent.py, frontend_aligner.py)
├── tests/                  # Test legacy root (108 file — migrare in bike_analyzer/tests/)
├── android/                # Android Kotlin nativo (Capacitor)
├── knowledge_base/         # Documenti RAG
├── alembic/                # Migrazioni DB
├── docker/                 # Dockerfile + docker-compose
├── .github/workflows/      # CI/CD
├── ROADMAP.md              # ← Questo file (fonte di verità)
├── PROJECT_STATUS.md       # Stato moduli (sintesi)
├── AGENTS.md               # Istruzioni agenti
├── main.py                 # Entrypoint root (delega a bike_analyzer)
├── pyproject.toml          # Config Python
├── requirements.txt        # Dipendenze Python
├── render.yaml             # Deploy backend Render
├── render-hub.yaml         # Deploy hub Render
└── vercel.json             # Deploy frontend Vercel
```

---

## 7. Comandi Rapidi

```bash
# Backend test (chunk per stabilità)
pytest tests/

# Frontend test
cd frontend && npm run test

# Frontend typecheck + lint
cd frontend && npm run typecheck && npm run lint

# Tauri build desktop
cd frontend && npm run tauri build

# BM2 demo
cd bike_analyzer && python -m bm2.simulation.demo

# AetherMap demo
cd aethermap/src && python -m aethermap.ai.demo
```

---

## 8. Note di Contesto

- **Branch `feat/local-sync`** contiene ~200 file modificati (3487 insertions, 41667
  deletions). Include lavoro su: sync locale↔cloud, adattamento frontend per offline,
  modelli DB espansi, sicurezza, AetherMap temp refactor, cleaning generale.
- **Non ricreare `temp_aethermap/`**: è già stato assorbito in `aethermap/`.
- **Non ricreare script duplicati**: `scripts/` è la posizione canonica.
- **Non modificare `docs/archive/`**: contiene documentazione IT storica/douplicata archiviata, non toccare senza esplicita indicazione.
