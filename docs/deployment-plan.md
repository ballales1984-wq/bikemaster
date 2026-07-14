# BikeMaster — Piano di Deployment

## 1. Visione d'Insieme

BikeMaster è un hub intelligente per il ciclismo che integra servizi diversi mantenendo
la maggior parte dei calcoli sul dispositivo dell'utente. L'architettura è **local-first**,
con sincronizzazione cloud opzionale e controllata dall'utente.

### Principi guida

1. **Local-first**: ogni utente ha il proprio database locale; il cloud è opzionale.
2. **Device-compute**: calcoli pesanti (GPS, calorie, VO2max, TSS, IA locale) restano sul device.
3. **Sync contrattata**: l'utente decide frequenza e direzione della sincronizzazione.
4. **Privacy by design**: i dati sensibili non lasciano il device a meno di sync esplicita.
5. **Modularità**: integrazioni attivabili/disattivabili senza dipendenze forzate.

---

## 2. Architettura di Deployment

### 2.1 Frontend

| Piattaforma | Tecnologia | Hosting | Note |
|---|---|---|---|
| Web | Vue 3 + Vite + PWA | **Vercel** | Build statico, CDN edge, HTTPS automatico |
| Desktop | Tauri 2 (Rust + WebView) | Release su GitHub | Bundle nativo Windows/macOS/Linux |
| Mobile Android | Capacitor 5 + Vue 3 | Google Play Store | APK/AAB, GPS background service |
| Mobile iOS | Capacitor 5 + Vue 3 | Apple App Store (futuro) | Dipende da roadmap |

**Flusso deploy frontend web:**
```
git push origin main
  → GitHub Actions (lint, typecheck, test, build)
  → Vercel preview (PR) / production (main)
  → PWA con service worker per offline
```

### 2.2 Backend

| Fase | Infrastruttura | Target | Note |
|---|---|---|---|
| Sviluppo | Locale (PC sviluppatore) | 1-5 utenti | SQLite locale, nessun deploy |
| Beta / Early adopters | **Render** (Docker web + PostgreSQL gestito) | 5-500 utenti | Piano Starter/Free, auto-deploy da git |
| Produzione / Scale | **Infrastruttura dedicata** (K8s o VPS) | 500+ utenti | Bilanciamento, cache distribuita, backup |

**Render stack:**
- Web service: Docker runtime, piano `starter` o `standard`
- PostgreSQL gestito: piano `starter` (o superiore per produzione)
- Auto-deploy da branch `main`
- HTTPS gestito da Render

**Stack dedicato (futuro):**
- Kubernetes + Helm chart (`docker/helm/bikemaster/`)
- PostgreSQL con pgvector (self-hosted o managed)
- Redis per caching/sessioni
- Prometheus + Grafana per osservabilità

### 2.3 Database

```
┌─────────────────────────────────────────────────────────┐
│                    DATABASE STRATEGY                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Device (SQLite)          Cloud (PostgreSQL)            │
│  ┌──────────────┐         ┌──────────────┐             │
│  │ rides.db     │         │  users       │             │
│  │ activities   │◄───────►│  activities  │ (sync)     │
│  │ health_data  │  sync   │  community   │            │
│  │ fusion_logs  │         │  leaderboard │            │
│  └──────────────┘         │  sessions    │            │
│                           └──────────────┘             │
│                                                         │
│  Ogni riga porta metadati:                              │
│  - source (device / strava / garmin / manual)           │
│  - reliability_score (0.0-1.0)                          │
│  - last_modified (UTC timestamp)                        │
│  - sync_status (local / synced / conflict / pending)    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Migrazione DB**: gestita con Alembic. Le migrazioni sono incluse in ogni release.

---

## 3. Strategia di Sincronizzazione

### 3.1 Modalità di Sync (scelta utente)

| Modalità | Frequenza | Impatto batteria | Uso dati | Adatto a |
|---|---|---|---|---|
| Real-time | Continuo | Alto | Variabile | Allenamenti live |
| Giornaliera | 1x/giorno (es. 02:00) | Basso | Basso | Uso quotidiano |
| Settimanale | 1x/settimana | Minimo | Minimo | Utenti occasionali |
| Manuale | Su richiesta | Minimo | Variabile | Controllo totale |
| Mai | — | Zero | Zero | Solo locale |

### 3.2 Protocollo di Sync

```
Device                          Cloud
  │                               │
  │  1. GET /sync/check           │
  │──────────────────────────────►│
  │◄──────────────────────────────│  last_sync_ts, server_changes
  │                               │
  │  2. POST /sync/push           │
  │     (delti locali + metadata) │
  │──────────────────────────────►│
  │◄──────────────────────────────│  conflitti (se presenti)
  │                               │
  │  3. GET /sync/pull            │
  │──────────────────────────────►│
  │◄──────────────────────────────│  cambiamenti remoti
  │                               │
  │  4. Merge + risoluzione       │
  │     (device-side o cloud)     │
```

**Gestione conflitti:**
- `reliability_score` determina quale fonte prevale (score più alto vince)
- In caso di parità: ultimo `last_modified` vince
- Conflitti irrisolvibili: flag `conflict` + notifica utente
- Audit trail completo per ogni operazione di merge

### 3.3 Dati Sincronizzati

| Categoria | Sync | Direzione | Note |
|---|---|---|---|
| Profilo utente | Sempre | Bidirezionale | Nome, peso, FTP, soglie |
| Attività complete | Se attivo | Push (device→cloud) | Source + metadata inclusi |
| Health data (sonno, HRV) | Se attivo | Push | Solo metriche aggregate, mai raw sensori |
| Community / Classifiche | Sempre | Pull | Read-only dal device |
| Fusion logs / AI cache | Se attivo | Push | Per migliorare modelli AI |
| Impostazioni app | Sempre | Bidirezionale | Preferenze sync, integrazioni |

---

## 4. Sicurezza

### 4.1 Autenticazione

| Metodo | Device | Cloud | Note |
|---|---|---|---|
| Google OAuth 2.0 | Login web | Primary | Username/password non memorizzato |
| PIN locale | Opzionale | — | 6 cifre, hashed localmente |
| Biometria | Opzionale | — | Face ID / impronta, sblocca app |
| Access token | JWT (HS256) | JWT (HS256) | 30 min access + 30 giorni refresh |
| Refresh token rotation | — | Max 5 attivi | Revoca automatica |

### 4.2 Crittografia

- **In transito**: HTTPS/TLS 1.3 obbligatorio (HSTS enforced)
- **A riposo (device)**: SQLite con crittografia opzionale (SQLCipher)
- **A riposo (cloud)**: PostgreSQL con crittografia volume + TLS
- **API keys**: conservate in secrets manager (Render) o vault; mai in codice/repo
- **Token JWT**: `SECRET_KEY` rotazione supportata con `SECRET_KEY_PREVIOUS`

### 4.3 Autorizzazione

- Rate limiting per-IP (slowapi)
- CORS configurato per origini esplicite (no wildcard in produzione)
- Security headers: CSP, HSTS, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- Audit log JSONL per azioni sensibili

---

## 5. Integrazioni Modulari

Ogni integrazione è un modulo opzionale. L'utente attiva solo quelle necessarie.

| Servizio | Tipo | Auth | Costo | Note |
|---|---|---|---|---|
| Strava | Import/Export dati | OAuth 2.0 | Free | Batch sync con paginazione |
| Google Fit | Import salute | OAuth 2.0 | Free | Sonno, HRV, passi |
| Google Maps | Mappe, elevation | API Key | Freemium | Static Maps + Elevation API |
| OpenAI | AI Coach | API Key | A pagamento | Fallback dopo Groq |
| Groq | AI Coach | API Key | Freemium | Provider primario (velocità) |
| Modelli IA locali | AI Coach | — | Free | ONNX/sentence-transformers su device |
| Garmin Connect | Import dati | OAuth 2.0 | Free | FIT file + attività |
| Wahoo Fitness | Import dati | OAuth 2.0 | Free | Attività |

**Gestione API key:**
- Cloud: secrets in Render environment variables o vault dedicato
- Device: keychain nativo (iOS Keychain / Android Keystore / Tauri secure storage)
- Nessuna chiave hardcoded; rotazione supportata

---

## 6. Backup Multi-livello

```
┌───────────────────────────────────────────────────────────┐
│                    BACKUP STRATEGY                        │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Livello 1 — Locale (device)                              │
│  ┌─────────────────────────────────────────────┐          │
│  │ SQLite journal + WAL                        │          │
│  │ Backup automatico pre-aggiornamento app     │          │
│  │ Export GPX/FIT/JSON su richiesta             │          │
│  └─────────────────────────────────────────────┘          │
│                                                           │
│  Livello 2 — Cloud sincronizzato                          │
│  ┌─────────────────────────────────────────────┐          │
│  │ PostgreSQL (Render / managed)               │          │
│  │ Replica primaria + standby (futuro)         │          │
│  │ Point-in-time recovery (PITR)               │          │
│  └─────────────────────────────────────────────┘          │
│                                                           │
│  Livello 3 — Backup server                                │
│  ┌─────────────────────────────────────────────┐          │
│  │ Dump giornaliero PostgreSQL                 │          │
│  │ Retention: 30 giorni                        │          │
│  │ Storage: S3-compatible / GCS                │          │
│  └─────────────────────────────────────────────┘          │
│                                                           │
│  Livello 4 — Utente (esterno)                             │
│  ┌─────────────────────────────────────────────┐          │
│  │ Export manuale: GPX, JSON, CSV              │          │
│  │ Disco esterno / NAS utente                  │          │
│  └─────────────────────────────────────────────┘          │
│                                                           │
│  RPO (Recovery Point Objective): configurabile per livello │
│  RTO (Recovery Time Objective):  < 4h (cloud), < 24h (server) │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 7. Modello Economico e Piani

| Piano | Prezzo | Cloud | AI | Community | Strumenti Avanzati |
|---|---|---|---|---|---|
| **Free** | €0 | Solo locale | Offline base | No | Analisi base |
| **Pro** | €X/mese | Sync cloud | AI Coach cloud | Read-only leaderboard | TSS, VO2max, piani allenamento |
| **Premium** | €Y/mese | Backup server + sync | AI avanzata + modelli locali | Piena partecipazione | Coaching personalizzato, previsioni |

**Gate di funzionalità:**
- Feature flags lato backend per abilitare/disabilitare per piano
- Frontend consulta `/api/v1/subscription/features` all'avvio
- Graceful degradation: funzionalità Pro/Premium disabilitate silenziosamente su Free

---

## 8. CI/CD

### 8.1 Pipeline GitHub Actions

| Job | Trigger | Azioni |
|---|---|---|
| `test` | Push/PR | pytest + coverage → Codecov |
| `lint` | Push/PR | ruff (Python) + eslint + vue-tsc (frontend) |
| `frontend` | Push/PR | npm run lint, typecheck, vitest, build |
| `security` | Push/PR | Trivy scan → SARIF → CodeQL |
| `build` | Push main | Docker build + push registry |
| `deploy-render` | Push main | Deploy backend su Render |
| `deploy-vercel` | Push main | Deploy frontend su Vercel |
| `android-release` | Tag `mobile-*` | Build APK/AAB + GitHub Release |

### 8.2 Git Hooks

- **Lefthook** (pre-commit): typecheck, eslint, unit test Python
- **Commitizen** (opzionale): conventional commits

---

## 9. Monitoring e Osservabilità

| Strumento | Scope | Dettagli |
|---|---|---|
| **Prometheus** | Metriche backend | `/metrics` endpoint, scraping automatico |
| **Grafana** | Dashboard | Preconfigurate: requests, latenza, errori, sistema |
| **Alertmanager** | Alerting | Soglie: errore rate > 1%, latenza p99 > 2s, CPU > 80% |
| **OpenTelemetry** | Tracing distribuito | gRPC OTLP → Zipkin |
| **Sentry** | Error tracking | APM + crash reporting, DSN in env |
| **Health check** | Liveness/readiness | `/api/v1/health` (DB, Redis, task queue) |

---

## 10. Roadmap di Deployment

### Fase 1 — Sviluppo Locale (ora)

- Backend in locale con SQLite
- Frontend Vite dev server
- Testing E2E locale
- Nessun deploy cloud

### Fase 2 — Beta su Render (Q3 2026)

- Deploy backend su Render (Docker, piano Starter)
- PostgreSQL gestito su Render
- Frontend su Vercel preview/production
- Android APK distribuito via GitHub Releases
- Max 500 utenti beta

### Fase 3 — Produzione (Q4 2026)

- Upgrade Render piano o migrazione a K8s self-hosted
- Redis per caching e sessioni
- Backup server automatizzato
- Tauri desktop app release
- iOS app (se roadmap approvata)

### Fase 4 — Scale (2027+)

- Infrastruttura dedicata con bilanciamento
- CDN per mappe e asset statici
- Replica database geografica
- AI Coach con modelli personalizzati

---

## 11. Considerazioni Aperte

Da approfondire:

1. **Strategia di sync dettagliata**: algoritmo di merge, gestione offline estesa,
   compressione dati su connessioni lente.
2. **Gestione API key**: rotazione automatica, scope minimization, audit usage.
3. **Termini d'uso provider esterni**: conformità Strava, Google Fit, Garmin,
   limiti di rate e condizioni di servizio.
4. **GDPR / Privacy**: data retention policy, diritto all'oblio, export dati utente.
5. **Fallback offline**: comportamento app quando cloud è irraggiungibile.
