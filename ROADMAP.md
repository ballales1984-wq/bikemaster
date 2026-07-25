# BikeMaster — Roadmap Unificata

*Ultimo aggiornamento: 2026-07-24*

> **Principio guida**: fare le cose una volta, farle bene. Questo documento è la
> *fonte di verità unica* per stato, priorità e azioni. Non eseguire feature
> duplicate: verificare qui prima di iniziare qualsiasi lavoro.

---

## 1. Stato Attuale (checklist veloce)

| Area | Stato | Note |
|:--|:--|:--|
| Backend FastAPI | **Stabile** | 2611 test pass, 138 endpoint |
| Frontend Vue 3 | **Stabile** | Vitest + Playwright configurati |
| Tauri 2 desktop | **Funzionante** | Backend embedded + SQLite primario |
| BM2 simulation engine | **Baseline** | 9 algoritmi, cablato via API |
| AetherMap R&D | **Fasi 1-4 ok** | Fasi 3-5 in corso |
| Multi-tenant / auth | **Completo** | tenant_id + OAuth2 (Google, Strava, Garmin) |
| Sync device↔cloud | **In corso** | 3 branch aperti da mergiare |
| Coverage test | **In corso** | ~30% routes.py, ~34% ai_coach, ~55% knowledge_base — nuovi test in `tests/test_coverage_ai_routes.py` |

---

## 2. Branches Aperti (azioni immediate)

Tutti e 3 i branch feat sono stati mergiati in `main`. Nessun branch aperto.

---

## 3. Working Tree Non Committato

File modificati non staged in `frontend/src/components/` (10 file Vue):
`RideComparison.vue`, `RideDetail.vue`, `RideMapPanel.vue`, `RideMetricsPanel.vue`,
`SpeedMap.vue`, `StatsSummary.vue`, `SyncSettingsPanel.vue`, `ToastContainer.vue`,
`WeatherPanel.vue`, `ZonesPanel.vue`.

**Azione**: verificare se queste modifiche sono già nei branch aperti oppure sono
lavoro isolato. Se sono superflue (duplicano modifiche già nei branch), reset.
Altrimenti, committare prima del merge.

---

## 4. Priorità Assoluta (ordine di esecuzione)

### Fase 1 — Chiudere il lavoro in corso (questa settimana)

1. **Merge dei 3 branch** in sequenza (vedi sezione 2)
2. **Commit working tree** oppure reset se duplicato
3. **Run test completo** backend + frontend per verificare integrità post-merge
4. **Pulizia repo**: rimuovere file temporanei e cache dalla root:
   - `temp_aethermap/` (duplicato di `aethermap/`, eliminare)
   - `backend_e2e.log`, `cov_*.log`, `errlines.log`, `fail*.log`, `pytest*.txt`,
     `test*.txt`, `test_run*.log`, `routes_*.log`, `routes_*.json`
   - `build_log.txt`, `duration_chart.png`, `google_map.png`, `ride_1_*.png`
   - `playwright-screenshot.png`, `dashboard.html`, `dashboard.png`
   - `.benchmarks/`, `.chroma_db/`, `chroma.sqlite3`
   - Backup DB nella root: `rides_backup_*.db`, `rides_export.*`
   - File `.db` nella root: `rides.db`, `rides_api.db` (esiste già in `bike_analyzer/`)

### Fase 2 — Stabilizzare (prossime 2 settimane)

5. **Fix test frontend**: 31 failed + 20 errors su 363 — risolvere i fallimenti
   bloccanti, prioritizzare quelli che rompono feature shipped
6. **Fix 2 test backend** (MissingGreenlet): spostare in `pytest.ini` come skip
   noto d'ambiente, oppure fixare il fixture setup
7. **Coverage > 90%** su `routes.py` e moduli AI — routes.py ~30%, ai_coach ~34%, knowledge_base ~55% (file `tests/test_coverage_ai_routes.py`, 84+ test function, ~64 passati al primo run)
8. **Documentazione consolidata**:
   - Eliminare duplicati IT in `docs/archive/`
   - Unificare `docs/MASTER.md` + `docs/UNIFIED_DOCUMENTATION.md` in un solo file
   - `docs/DELUXE_ROADMAP.md` → riferire a `ROADMAP.md` invece di duplicare

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

### Fase 5 — AetherMap (R&D, tempo libero)

16. Completare Fase 3 (AI pipeline) e Fase 5 (digital twin)
17. Decisione esplicita: `aethermap/` converge in BikeMaster o resta R&D separato
18. Se convergente: definire contratto dati `Ride/GPSPoint → terrain input`

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
├── aethermap/              # R&D cartografia (separato da BikeMaster)
├── docs/                   # Documentazione sviluppatore
│   ├── archive/            # Materiale obsoleto (non toccare)
│   └── reference/          # Dizionario dati, schemi
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
- **Non modificare `docs/archive/`**: materiale storico, lasciare in pace.
