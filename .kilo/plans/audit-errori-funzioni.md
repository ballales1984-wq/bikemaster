# Piano Audit BikeMaster — Controllo Funzioni e Errori

## Data
2026-06-11

## Obiettivo
Controllare tutte le funzioni del programma, identificare e correggere errori, bug e problemi di codice.

## Errore critici identificati (da correggere)

### Priorità 1 — Fix immediato (crash / dati sbagliati)

| ID | File | Descrizione |
|----|------|-------------|
| E1 | `analytics_trends.py:~437` | Dead code: `total_dist / len(valid) if valid else 0` senza assegnazione → `avg_ride_dist` mai calcolata |
| E2 | `database.py:116+207` | Funzione `_row_to_athlete` definita due volte con implementazioni diverse |
| E3 | `ai_coach.py:~335` | `_generate_fallback_training_advice()` — `format_context_for_llm(kb)` scartato, KB mai usata nel fallback |
| E4 | `ai_coach.py:~/coach/full` | `create_speed_chart` / `create_duration_chart` chiamate ma **non importate** → NameError |
| E10 | `fatigue.py:~calc` | Divisione `(220 - rider_age)` senza guard — age=220 → ZeroDivisionError |

### Priorità 2 — Fix alta (sicurezza / dati)

| ID | File | Descrizione |
|----|------|-------------|
| E5 | `database.py:281` | ORDER BY concatenato — risk SQL injection se assertion bypassata |
| E6 | Alembic `08ee39bfe529` | Migrazione distruttiva: droppa tabelle e colonne → perdita dati |
| E7 | `models.py` vs `database.py` | Schema drift: ORM non corrisponde a schema SQLite reale |
| E9 | `database.py` | Nessun try/except su save/update/delete → errori DB silenziosi |

### Priorità 3 — Fix media (test / coverage)

| ID | File | Descrizione |
|----|------|-------------|
| E16 | `test_error_paths.py` | Due test identici per `test_delete_nonexistent_calendar_event` |
| E11 | `routes.py` (uncommitted) | Ownership check su GET `/athletes` rimosso admin access — breaking change |
| E20 | `routes.py:553` | `athlete_id != current_user["id"]` senza eccezione per admin |
| E17 | `database.py` | `_row_to_athlete` apre connessione dentro funzione — inefficiente |

## Piano di esecuzione

### FASE A — Fix errori critici E1-E4, E10 (15-20 min)
1. `analytics_trends.py` Line ~437: Cambiare `total_dist / len(valid) if valid else 0` in `avg_ride_dist = total_dist / len(valid) if valid else 0`
2. `database.py`: Rimuovere la prima definizione di `_row_to_athlete` (line 116-121) e `get_athlete_by_name` (line 124-129), tenere solo la seconda implementazione
3. `ai_coach.py` Line ~335: Aggiungere `return _generate_fallback_training_advice(kb)` o integrare KB nel fallback
4. `ai_coach.py`: Aggiungere import corretto per `create_speed_chart` / `create_duration_chart` da `..analytics.analytics`
5. `fatigue.py`: Aggiungere guard `if rider_age >= 220: return 0` prima della divisione

### FASE B — Fix sicurezza e integrità E5, E9, E20 (15 min)
6. `database.py` Line 281: Sostituire stringa ORDER BY con index su array whitelist
7. `database.py`: Aggiungere try/except + logging su funzioni CRUD critiche
8. `routes.py:553`: Aggiungere check admin `if current_user.get("is_admin")` per bypassare ownership check

### FASE C — Verifica test (10 min)
9. Eseguire `pytest tests/ -v --tb=short` per verificare che tutti i fix non rompano test esistenti
10. Eseguire `pytest --cov=bike_analyzer --cov-report=term-missing` per verificare coverage

### FASE D — Fix test E16 (5 min)
11. Rimuovere test duplicato in `test_error_paths.py`

### FASE E — Commit
12. `git add` e `git commit` con messaggio dettagliato

## Ordine di esecuzione
A → B → C → D → E

## Note
- I fix sono tutti in-place, no refactoring architetturale
- La migrazione E6 richiede decisione architetturale separata (non corretta in questo piano per evitare distruzione dati)
- I fix E5-E9 sono preparazione per sicurezza produzione, non bloccano funzionalità correnti
