# AGENTS_TEAM.md — BikeMaster

## Obiettivo
Garantire la persistenza totale dei dati critici su Render (PostgreSQL) senza perdite al resume del container, mantenendo il fallback SQLite per l'uso offline (Tauri/PWA).

## Ruoli coinvolti
| Ruolo | Responsabilità |
|---|---|
| **DATABASE** | Progetta e applica le migrazioni PostgreSQL; allinea schemi SQLite/PostgreSQL; implementa i moduli `postgres_*.py` con dispatch guard in `database.py`. |
| **TESTER** | Verifica che ogni funzione migrata mantenga la stessa interfaccia e comportamento del fallback SQLite; esegue test di integrazione su PostgreSQL. |
| **DEBUGGER** | Indaga e risolve discrepancy tra SQLite e PostgreSQL (es. drift di schema, tipi NULL, constraint mancanti). |
| **REVIEWER** | Verifica correttezza delle guard `has_postgres()`, coerenza delle colonne, assenza di regressioni nei moduli SQLite. |
| **VERIFIER** | Giudica PASS/FAIL per ogni dominio migrato con evidenza (query DB, test passanti, log). |

## Stato attuale

### ✅ Migrato (persistenza su Render garantita)
| Dominio | Modulo PostgreSQL | Funzioni |
|---|---|---|
| Athlete profile / history / metric log | `postgres_athlete.py` | `get_athlete`, `save_athlete`, `update_athlete`, `log_athlete_metric`, `get_athlete_metric_log`, `save_athlete_snapshot`, `get_athlete_history`, lookup/delete |
| Rides / metrics | `postgres_rides.py` | `save_ride`, `get_ride`, `get_rides_by_athlete`, `get_all_rides`, `delete_ride`, `update_ride`, `save_metric` |
| Training stress days | `postgres_rides.py` | `upsert_training_stress_day`, `get_training_stress_days`, `get_latest_training_stress` |
| Itineraries / stages | `postgres_itineraries.py` | `save_itinerary`, `get_itinerary`, `list_itineraries`, `update_itinerary`, `delete_itinerary`, `save_stage`, `list_stages`, `get_stage`, `update_stage`, `delete_stage`, `reorder_stages` |
| Training goals | `postgres_db.py` (SQLAlchemy) | `save_training_goal`, `get_training_goals` |

### ⏳ Pending (SQLite-only, dati persi al resume su Render)
| Dominio | Funzioni principali |
|---|---|
| POI | `save_poi`, `get_poi`, `list_pois`, `get_nearby_pois`, `delete_poi` |
| HR 24h | `log_hr_sample`, `log_hr_samples`, `get_hr_24h_samples`, `get_hr_daily_summary`, `get_hr_settings`, `upsert_hr_settings` |
| Metabolic / food logs | `save_metabolic_profile`, `get_metabolic_profile`, `save_food_log`, `get_food_logs_by_athlete_date`, `update_food_log`, `get_food_log`, `delete_food_log`, `save_metabolic_daily_summary`, `get_metabolic_daily_summaries`, `get_metabolic_daily_summary`, `upsert_metabolic_reference_value`, `get_metabolic_reference_value`, `get_all_metabolic_reference_values`, `save_metabolic_adaptive_weights`, `get_metabolic_adaptive_weights` |
| Chat history | `save_chat_message`, `get_chat_history`, `clear_chat_history`, `prune_chat_history` |
| Calendar events | `save_calendar_event`, `get_calendar_event`, `get_events_by_athlete`, `get_events_by_date_range`, `get_events_by_month`, `update_calendar_event`, `delete_calendar_event` |
| Weather cache | `save_weather_cache`, `get_weather_cache` |
| Road incidents / route safety | `save_road_incident`, `save_route_safety_score`, `get_route_safety_score` |
| Fitness states | `get_fitness_states_by_athlete` |
| Nutrition / Beck / BLE / Users / Consent / Sensor | Vedere `database.py` per elenco completo |

## Piano di migrazione (prossimi passi)

1. **POI** — creare `postgres_pois.py` seguendo il pattern di `postgres_itineraries.py`; aggiungere guard in `database.py` per `save_poi`/`get_poi`/`list_pois`/`get_nearby_pois`/`delete_poi`.
2. **HR 24h + Metabolic + Food logs** — creare `postgres_health.py` (o moduli separati `postgres_hr.py`, `postgres_metabolic.py`); priorità: `save_metabolic_profile` e `save_food_log` (dati nutrizionali sensibili).
3. **Chat + Calendar** — creare `postgres_chat.py` e `postgres_calendar.py`; priorità: `save_calendar_event` (dati di pianificazione).
4. **Weather / Road incidents / Route safety** — creare `postgres_weather.py` e `postgres_terrain.py`; dati cache/calcolati, priorità bassa.
5. **Fitness states / Beck / BLE / Users / Consent / Sensor** — creare moduli dedicati secondo priorità di dominio; valutare se alcuni domini (es. BLE, sensor raw) debbano restare SQLite-only per natura locale.
6. **Training goals (completamento)** — estendere `postgres_db.py` con `save_planned_workout`/`get_planned_workouts` e aggiungi fallback SQLite in `database.py` se necessario.
7. **Validazione finale** — TESTER: suite di integrazione che confronta risultati SQLite vs PostgreSQL per ogni dominio migrato; VERIFIER: PASS/FAIL con evidenza.

## Note
- Il dispatch usa `has_postgres()` (bool su `DATABASE_URL`); offline/Tauri usa sempre SQLite.
- La migrazione deve preservare la firma delle funzioni in `database.py` per non rompere le route esistenti.
