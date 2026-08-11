# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Organizzazione immagini in `assets/images/` per documentazione GitHub
- File `SECURITY.md` con policy di sicurezza
- `analytics/repositories/training_goal_repository.py` — wrapper PostgreSQL/SQLAlchemy per training goals
- `analytics/training_load.py` — +5 funzioni: `TrainingLoadDay`, `calculate_atl_ctl_tsb()`, `calculate_rss()`, `get_current_training_status()`, `get_7day_fitness_summary()`
- `review_db_architecture.md` — report architetturale completo di `database.py` e dipendenze

### Changed
- Refactoring `database.py` — estrazione Calendar (P1) in `db/repositories/calendar_repository.py`
- Circular import resolution: tutti i repository `analytics/repositories/` convertono import top-level in lazy import dentro metodi
- `db/repositories/calendar_repository.py` — aggiunto `_get_db_connection()` lazy per risolvere ciclo `database.py` → `repositories/` → `database.py`
- `analytics/repositories/calendar_repository.py` — rediretto da `db/repositories/calendar_repository.py` a `db.database` diretto
- `training_routes.py` — adotta `TrainingGoalRepository` invece di import diretti da `db.postgres_db`
- `tests/test_database.py` — import `recalculate_training_stress_for_athlete` spostato da `db.database` a `analytics.training_load`
- Allineamento licenza: `LICENSE` e `pyproject.toml` ora dichiarano "All Rights Reserved"
- Rimosso riferimento obsoleto a ngrok in `ROADMAP.md`
- Corretto duplicato in tabella documentazione `README.md`

### Fixed
- Risolti conflitti git nel file `LICENSE`

## [0.2.0] - 2026-08-11

### Added
- Refactoring `database.py` — estrazione domini in repository pattern
- `analytics/repositories/training_goal_repository.py` — wrapper PostgreSQL/SQLAlchemy
- `analytics/training_load.py` espanso con ATL/CTL/TSB, RSS, 7-day fitness summary
- `review_db_architecture.md` — report architetturale database

### Changed
- Circular import resolution via lazy imports in tutti i repository analytics
- Calendar (P1) estratta in `db/repositories/calendar_repository.py`
- `training_routes.py` adotta `TrainingGoalRepository`
- `db/repositories/calendar_repository.py` ottiene `_get_db_connection()` lazy

### Fixed
- Import path `training_load.py`: `..models.models` → `...core.models`

## [0.1.0] - 2026-07-15

### Added
- Architettura locale-first Tauri 2 + SQLite primario
- Backend FastAPI embedded + modulo hub PostgreSQL
- Frontend Vue 3 + Vite + TypeScript (PWA)
- BM2 Simulation Engine (9 algoritmi, 7 pipeline)
- AI Coach (Groq + RAG knowledge base)
- Import Strava/Garmin/Wahoo/Google Fit
- Phone GPS Tracking (Android + iOS)
- Traffic Safety Analysis
- Multi-tenant + data isolation
- AetherMap (fasi 1-5 complete, convergenza in BikeMaster)
