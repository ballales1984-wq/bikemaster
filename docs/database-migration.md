# Migrazione Database: SQLite → PostgreSQL

## Setup Iniziale (completato)

- [x] Installate dipendenze: `alembic`, `asyncpg`, `aiosqlite`
- [x] Creati modelli ORM in `bike_analyzer/backend/db/models.py`
- [x] Creato layer async in `bike_analyzer/backend/db/async_db.py`
- [x] Configurato Alembic con `alembic/env.py` adattato per SQLite/PostgreSQL
- [x] Generata migrazione iniziale: `alembic/versions/08ee39bfe529_initial_models.py`

## Passaggi futuri per attivare PostgreSQL

1. **Configurare DATABASE_URL nel `.env`**:
   ```env
   # SQLite (default attuale)
   DB_PATH=rides.db
   # oppure PostgreSQL
   DATABASE_URL=postgresql://user:pass@localhost:5432/bikemaster
   # oppure PostgreSQL async (per app)
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bikemaster
   ```

2. **Eseguire migrazioni**:
   ```bash
   alembic upgrade head
   ```

3. **(Opzionale) Popolare dati esistenti**:
   ```python
   python -c "
   from bike_analyzer.backend.db.database import get_all_rides, get_all_athletes
   from bike_analyzer.backend.db.async_db import save_ride_async, save_athlete_async
   import asyncio
   asyncio.run(init_async_db())
   for a in get_all_athletes():
       asyncio.run(save_athlete_async(a))
   for r in get_all_rides():
       asyncio.run(save_ride_async(r))
   print('Migration complete!')
   "
   ```

4. **Cambiare import nelle route**:
   Sostituire `from ..db.database import ...` con equivalenti async quando `DATABASE_URL` è PostgreSQL.

## Architettura

```
backend/db/
├── __init__.py
├── models.py          # SQLAlchemy ORM models (AthleteModel, RideModel, etc.)
├── async_db.py        # Async PostgreSQL/SQLite layer (asyncpg/aiosqlite)
├── database.py        # Sync SQLite layer (main.py, tests — default)
└── postgres_db.py     # Esistente — estensione per Alembic/stored procedures
```
