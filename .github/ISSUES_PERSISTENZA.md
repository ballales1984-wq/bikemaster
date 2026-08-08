# GitHub Issues — Persistenza Render & Migrazione PostgreSQL

## Issue 1: Fix dispatch guard mancante per `get_metrics_by_athlete`

**Priorità:** Alta  
**Stato:** Fix applicato in `main` (commit da creare)

### Problema
La funzione `db.get_metrics_by_athlete()` in `bike_analyzer/backend/db/database.py` non disponeva di un dispatch guard verso PostgreSQL quando `DATABASE_URL` è configurato. Su Render, le metriche vengono salvate correttamente su PostgreSQL tramite `save_metric` (che ha il dispatch), ma la lettura tramite `get_metrics_by_athlete` leggeva direttamente da SQLite, restituendo risultati vuoti o obsoleti.

Questo bug causava:
- Export dati incompleto (route `/api/v1/export` chiama `get_metrics_by_athlete`)
- Dashboard che non mostrava metriche in produzione
- Inconsistenza tra scrittura (PostgreSQL) e lettura (SQLite)

### Fix applicato
1. Aggiunta `get_metrics_by_athlete` in `bike_analyzer/backend/db/postgres_rides.py`
2. Aggiunto dispatch guard in `bike_analyzer/backend/db/database.py`
3. Aggiornato `tests/test_database_dispatch.py` con la funzione nella lista `_MIGRATED_FUNCTIONS`
4. Aggiunto `test_get_metrics_by_athlete_pg` in `tests/test_postgres_rides_dispatch.py`

### Verifica
```bash
pytest tests/test_database_dispatch.py tests/test_postgres_rides_dispatch.py -v
```

---

## Issue 2: Mitigazione temporanea — volume persistente e backup per `rides.db`

**Priorità:** Alta  
**Stato:** Aperto

### Problema
Su Render (piano free/starter), il container non ha volumi persistenti. `rides.db` viene perso al resume post-sospensione. I domini non migrati su PostgreSQL (POI, metabolico, chat, calendario, weather, BLE, sensor, users, ecc.) sono a rischio di perdita dati.

### Soluzione proposta
1. **Montare volume persistente su Render** per `rides.db` (se supportato dal piano)
   - Aggiornare `render.yaml` con `disk` mount
   - Verificare che il percorso `DB_PATH` punti al volume montato
2. **Configurare backup automatico** (cron job o snapshot Render)
3. **Test di restore** da backup
4. **Documentare** la procedura di recovery

### Workaround immediato (se volume non disponibile)
- Aggiungere health check che verifichi l'integrità del DB all'avvio
- Implementare export automatico periodico di `rides.db` su storage esterno

---

## Issue 3: CI — test automatici backend/frontend + build Tauri

**Priorità:** Media  
**Stato:** Aperto

### Problema
Attualmente non esiste una pipeline CI che esegua automaticamente:
- `pytest` (backend)
- `npm run lint && npm run typecheck && npm run test` (frontend)
- Build check Tauri

### Soluzione proposta
1. Creare `.github/workflows/ci.yml` con job separati:
   - `backend-test`: pytest su Python 3.11
   - `frontend-test`: lint, typecheck, test su Node.js
   - `tauri-build`: build check (richiede runner con Android SDK/NDK se necessario)
2. Configurare fallover policy: blocco merge se qualsiasi job fallisce
3. Aggiungere badge README

---

## Issue 4: Migrazione domini rimanenti su PostgreSQL

**Priorità:** Media  
**Stato:** Aperto

### Problema
I seguenti domini sono ancora SQLite-only e non hanno moduli PostgreSQL dedicati:
- POI (`save_poi`, `get_poi`, `list_pois`, `get_nearby_pois`, `delete_poi`)
- HR 24h (`log_hr_sample`, `log_hr_samples`, `get_hr_24h_samples`, ecc.)
- Metabolico/food logs
- Chat history
- Calendario eventi
- Weather cache
- Road incidents
- Route safety scores
- Fitness states
- Nutrition food items
- Beck assessments
- BLE devices
- Users/consent/legal/ai_audit
- Sensor/activity data
- Sync/backup

### Soluzione proposta
1. Per ogni dominio, creare modulo `postgres_<domain>.py` seguendo il pattern esistente
2. Aggiungere dispatch guard in `database.py` per ogni funzione
3. Creare tabelle PostgreSQL corrispondenti (via Alembic o SQLAlchemy models)
4. Aggiungere test dispatch per ogni nuovo modulo
5. Implementare feature flag per switchover graduale

### Piano di migrazione suggerito
| Fase | Domini | Priorità |
|------|--------|----------|
| 1 | Users, consent, sessions, tokens | Alta (auth critica) |
| 2 | POI, weather cache | Media |
| 3 | Chat, calendar, HR 24h | Media |
| 4 | Metabolico, nutrition, Beck | Bassa |
| 5 | BLE, sensor, road incidents | Bassa |

---

## Issue 5: Allineamento documentazione architettura database

**Priorità:** Bassa  
**Stato:** Aperto

### Problema
`AGENTS.md` e `settings.py` contengono documentazione che descrive SQLite come "primary store" anche in produzione, mentre nella realtà i domini migrati usano PostgreSQL come store effettivo quando `DATABASE_URL` è configurato.

### Soluzione proposta
1. Aggiornare `settings.py` commenti per riflettere il comportamento reale del dispatch
2. Aggiornare `AGENTS.md` per distinguere chiaramente:
   - Domini con dispatch PostgreSQL (protetti da perdita dati)
   - Domini SQLite-only (a rischio su Render)
   - Store locale offline (Tauri/PWA)
3. Aggiungere diagramma architettura database
