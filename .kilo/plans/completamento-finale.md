# Piano di Completamento BikeMaster

## Riepilogo Stato Attuale

**Progetto**: BikeMaster - Bike Ride Analyzer AI-Powered (v1.1.0)
**ROADMAP**: 140/145 completi, 5 step mancanti
**Test**: 79 test implementati, coverage da verificare (~79% stimato)

## Step Mancanti dalla Roadmap

### 1. STEP 80 - Test Score Engine (FASE 5)
**Stato**: NON COMPLETATO
**Azione**: 
- Verificare che `tests/test_scores_api.py` e `tests/test_performance.py` coprano tutti gli score (Performance, Endurance, Fatigue, Recovery, Efficiency)
- Aggiungere test mancanti per `bike_analyzer/backend/analytics/performance.py`
- Target: 100% coverage modulo performance engine

### 2. STEPS 118-120 - Google Maps Visualizzazione Dinamica (FASE 10)
**Stato**: PARZIALMENTE COMPLETATO (Static Maps OK, manca path colorata dinamica)
**Azione**:
- Step 118: Aggiungere supporto polyline colorata per velocità nella Google Static Map
- Step 119: Integrare Google Maps JavaScript API nel frontend per visualizzazione interattiva
- Step 120: Documentare endpoint Google Maps completo in docs/

### 3. STEPS 136-145 - Test Coverage > 80% (FASE 13)
**Stato**: PARZIALMENTE COMPLETATO (79 test, coverage da aumentare)
**Azione**:
- Step 136-144: Verificare tutti i test esistenti passano, aggiungere test per moduli non coperti
- Step 145: Raggiungere coverage > 80% tramite pytest-cov

## Piano Implementazione

### FASE A - Verifica e Fix Test (30 min)
1. Eseguire tutti i test: `pytest tests/ -v --tb=short`
2. Identificare e fixare eventuali test falliti
3. Verificare coverage attuale con `pytest --cov=bike_analyzer`
4. Documentare gap coverage

### FASE B - Completamento Score Engine Tests (20 min)
1. Verificare `test_scores_api.py` copre `/api/v1/scores/athlete/{id}`
2. Verificare `test_performance.py` copre tutti gli score
3. Aggiungere test mancanti se necessario
4. Target: Incrementare coverage modulo performance > 95%

### FASE C - Google Maps Dynamic Path (30 min)
1. **Step 118**: Modificare `google_maps.py` per supportare polyline colorata per velocità
   - Spezzare il percorso in segmenti
   - Assegnare colori basati su velocità (verde=veloce, rosso=lento)
   - Generare multiple path nel request Google Static Maps API
2. **Step 119**: Integrare Google Maps JS API in frontend
   - Aggiungere tab/view per mappa Google interattiva
   - Mostrare percorso su mappa Google con marker velocità
3. **Step 120**: Documentare in `docs/API_DOCS.md` e `docs/API_DOCUMENTAZIONE.md`

### FASE D - Test Coverage > 80% (40 min)
1. Aggiungere test per moduli poco coperti:
   - `google_maps.py` (views/plot functions)
   - `ai_coach.py` (funzioni edge case)
   - `knowledge_base.py` (funzioni load/reload)
   - `processing.py` (GPS cleaning edge cases)
2. Verificare nuovamente coverage con `pytest --cov=bike_analyzer --cov-report=term-missing`
3. Target: Coverage >= 80%

### FASE E - Layout Finale (10 min)
1. Aggiornare ROADMAP.md segnando tutti gli step come completati [x]
2. Aggiornare CHANGELOG.md con versione 1.2.0
3. Commit finale se richiesto

## Priorità
1. **ALTA**: Verifica test e fix (prerequisito per tutto il resto)
2. **ALTA**: Google Maps path colorata (feature visiva importante)
3. **MEDIA**: Test coverage > 80% (obiettivo qualità)
4. **BASSA**: Documentazione Google Maps (nice-to-have)

## Risorse Necessarie
- Database: PostgreSQL locale o SQLite
- Dipendenze: `pytest`, `pytest-cov`, `pytest-asyncio`
- API keys: Google Maps (opzionale per test, mock in test)

## Note
- Tests con Groq API potrebbero richiedere timeout lunghi - usare mock dove possibile
- Google Maps JS API richiede API key valida per funzionare in produzione
- Coverage target realistico: 80-85% (considerando natura monolitica del progetto)
