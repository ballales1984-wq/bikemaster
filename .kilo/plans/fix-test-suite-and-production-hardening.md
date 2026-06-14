# Piano: Fix Test Suite e Hardening Produzione

## Stato Progetto Attuale
- **Progressione**: 148/145 step base + 20/80 estensioni completati
- **Coverage**: 79% (target 92% per produzione)
- **Ultimi commit**: riferimento a security hardening e lazy loading

## Problemi Identificati

### 1. Test Failure Critico
- `test_coach_workout_endpoint` fallisce con ImportError (vedi `test_output.txt`)
- Il file `test_ai_coach_api.py` attuale contiene solo test `validate_athlete_profile`
- Probabile mismatch tra test esistente e endpoint API `/api/v1/coach/workout`

### 2. Coverage Gap
- Target: 92% per produzione
- Attuale: 79%
- Mancano circa 13% di coverage

## Piano di Azione

### Fase 1: Fix Test Suite (Priorità Alta)
1. **Indagare l'ImportError** - verificare il problema di importazione legato al lazy loading
2. **Risincronizzare test_ai_coach_api.py** - aggiungere test per endpoint `/api/v1/coach/workout`
3. **Eseguire tutti i test** - `pytest tests/ -v --tb=short`
4. **Fixare test necessari** - correggere eventuali altri fallimenti

### Fase 2: Coverage Improvement (Priorità Media)
1. **Analisi gap coverage** - eseguire `pytest --cov=bike_analyzer tests/` per identificare moduli non testati
2. **Aggiungere test mancanti**:
   - `analytics/power_model.py` (14 modelli potenza)
   - `analytics/advanced.py` (14 modelli avanzati)
   - `analytics/training_load.py` e `training_stress.py`
   - `events/__init__.py` (domain events)
3. **Target 85% entro 2 settimane**

### Fase 3: Hardening Produzione (Priorità Alta)
1. **Ruff + mypy** - configurare e risolvere lint issues
2. **Docker multi-stage** - ottimizzare `Dockerfile`
3. **Monitoring** - aggiungere Sentry/Prometheus integration points
4. **Audit log** - per azioni admin (endpoint `/admin/*`)

## Prossimi Step Riccomandati (Priorità)

| Priorità | Task | Descrizione | Stima |
|---|---|---|---|
| **1** | Fix test_ai_coach_api | Sincronizzare test con endpoint workout | 2h |
| **2** | Eseguire suite test completa | Verifica stato generale | 1h |
| **3** | Aggiungere test coverage | Portare a 85% minimo | 4-6h |
| **4** | Configurare Ruff/mypy | Linting + type checking | 2h |
| **5** | Docker hardening | Multi-stage, rootless, scan | 2h |

## Note Tecniche
- Il lazy loading nei `__init__.py` potrebbe causare problemi di importazione nei test
- I test devono usare `AI_COACH_MODE=local` per evitare chiamate API esterne
- Il modulo `security.py` richiede `SECRET_KEY` obbligatoria anche in test