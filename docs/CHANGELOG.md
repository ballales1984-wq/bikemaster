# Changelog

Tutte le modifiche significative a questo progetto sono documentate in questo file.

## [1.1.0] - 2026-06-05

### Fixati
- Corretto test `test_benchmark_categories`: weight 60kg è "Lightweight", non "Medium"
- Aggiunta migrazione automatica colonna `goals` nello schema database `athletes`

### Aggiunte
- Test Google Maps mock (`test_google_maps_mock.py`)
- Test scores API (`test_scores_api.py`)
- Test benchmark API (`test_benchmark_api.py`)
- Test knowledge base (`test_knowledge_api.py`)
- Test database backup (`test_database_backup.py`)
- Test batch import (`test_import_batch.py`)
- Test athlete profile (`test_athlete_profile.py`)

**Test coverage: 79 test passanti**

## [1.0.0] - 2026-06-05

### Aggiunte
- API REST con 40+ endpoint per gestione rides e analytics
- Parser GPX e FIT per importazione file GPS
- Integrazione Google Fit OAuth2
- Mappe interattive con Folium e Google Static Maps
- Grafici velocità, elevazione, distanza, durata
- Sistema di punteggi (performance, endurance, efficiency, fatigue)
- AI Coach con raccomandazioni allenamento e recupero
- Knowledge base con contenuti training/recovery/cardio
- Database SQLite con backup integrato
- Dashboard web dark-themed
- Supporto Docker e Docker Compose
- Deployment Azure con azd
- Test automatici (pytest)

### Analytics
- Calcolo distanza totale con formula haversine
- Rilevamento pause e fermate
- Analisi accelerazioni/rallentamenti
- Segmentazione percorsi
- Stima calorie (fisico + MET)
- Punteggio affaticamento con formula pesata
- Stime ore recupero post-allenamento

### API Endpoints Principali
- `/api/v1/rides/*` — CRUD rides
- `/api/v1/import/*` — Importazione GPX/FIT/Google Fit
- `/api/v1/export/*` — Esportazione JSON/CSV
- `/api/v1/charts/*` — Grafici immagine
- `/api/v1/athletes/*` — Gestione profili atleta
- `/api/v1/scores/*` — Punteggi performance
- `/api/v1/benchmark/*` — Confronto atleti
- `/api/v1/coach/*` — AI recommendations
- `/api/v1/knowledge/*` — Knowledge base

## [0.2.0] - 2026-05-01

### Aggiunte
- Modello dati Ride con GPSPoint
- Parser file GPX base
- Database SQLite con tabella rides
- Analytics base (distanza, velocità, tempo)

## [0.1.0] - 2026-04-01

### Aggiunte
- Struttura progetto iniziale
- README e configurazione
- Setup environment Python
- Primi script di importazione