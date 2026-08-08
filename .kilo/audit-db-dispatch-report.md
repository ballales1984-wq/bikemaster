# Audit dispatch DB — `bike_analyzer/backend/db/database.py`

**Metodo**: `Select-String -Pattern "has_postgres"` (32 guard `if has_postgres():`)
intersecato con `Select-String -Pattern "^def "` (147 def top-level). Per ogni
`def` senza guardia nel proprio intervallo di riga è stato catturata la prima
istruzione SQL (`INSERT/SELECT/UPDATE/DELETE … FROM/INTO <table>`).

## Funzioni MIGRATED (32 — hanno dispatch `has_postgres`)
Athlete: `save_athlete`, `get_athlete`, `update_athlete`, `get_athlete_by_email`,
`get_athletes_by_user`, `get_athlete_count_by_user`, `delete_athlete`,
`save_athlete_snapshot`, `get_athlete_history`, `log_athlete_metric`,
`get_athlete_metric_log`.
Rides/metrics/stress: `save_ride`, `get_ride`, `get_rides_by_athlete`,
`get_all_rides`, `delete_ride`, `update_ride`, `save_metric`,
`upsert_training_stress_day`, `get_training_stress_days`,
`get_latest_training_stress`.
Itinerari/stages: `save_itinerary`, `get_itinerary`, `list_itineraries`,
`save_stage`, `list_stages`, `get_stage`, `update_itinerary`,
`delete_itinerary`, `update_stage`, `delete_stage`, `reorder_stages`.

## Funzioni SQLITE-ONLY (115 — nessun dispatch)
Gruppate per tabella; operazione = (I)NSERT / (S)ELECT / (U)PDATE / (D)ELETE.
- `users`: save_user(I), get_user_by_username(S), get_user_by_id(S),
  get_all_users(S), update_user(U), delete_user(D)
- `user_oauth_credentials`: get_user_oauth_credentials(S),
  get_all_user_oauth_credentials(S), save_user_oauth_credentials(I),
  delete_user_oauth_credentials(D)  [+ _ensure* / lock helpers]
- `oauth_locks`: release_oauth_sqlite_lock(D)
- `athletes`: get_athlete_by_name(S), get_all_athletes(S)
- `rides`: _find_existing_external_ride(S)
- `metrics`: get_metrics_by_athlete(S)
- `hr_24h_samples`: log_hr_sample(I), log_hr_samples(I), delete_hr_samples(D)
- `hr_monitoring_settings`: get_hr_settings(S), upsert_hr_settings(I),
  delete_hr_settings(D)  [+ get_hr_24h_samples / get_hr_daily_summary]
- `sensor_data`: log_sensor_data(I)  [+ classify_day(I daily_activity_classification),
  get_activity_*]
- `metabolic_profiles`: save_metabolic_profile(I), get_metabolic_profile(S)
- `food_logs`: save_food_log(I), get_food_logs_by_athlete_date(S),
  update_food_log(U), get_food_log(S), delete_food_log(D),
  get_food_logs_by_athlete(S)
- `metabolic_daily_summaries`: save_metabolic_daily_summary(I),
  get_metabolic_daily_summaries(S), get_metabolic_daily_summary(S)
- `metabolic_reference_values`: upsert_metabolic_reference_value(I),
  get_metabolic_reference_value(S), get_all_metabolic_reference_values(S)
- `metabolic_adaptive_weights`: save_metabolic_adaptive_weights(I),
  get_metabolic_adaptive_weights(S)
- `chat_history`: save_chat_message(I), get_chat_history(S),
  clear_chat_history(D), prune_chat_history(D)
- `calendar_events`: save_calendar_event(I), get_calendar_event(S),
  get_events_by_athlete(S), get_events_by_date_range(S),
  update_calendar_event(U), delete_calendar_event(D)
- `weather_cache`: get_weather_cache(S), save_weather_cache(I)
- `training_stress` (ricorsione): recalculate_training_stress_for_athlete
- `road_incidents`: save_road_incident(I/[INSERT])
- `route_safety_scores`: save_route_safety_score(I), get_route_safety_score(S)
- `pois`: save_poi(I), get_poi(S), get_nearby_pois(S), list_pois(S),
  delete_poi(D)
- `itinerary/stage` (helpers): _row_to_itinerary, _row_to_stage
- `nutrition_food_items`: seed_nutrition_food_items,
  search_nutrition_food_items(S), get_nutrition_food_item(S),
  list_nutrition_categories(S), save_nutrition_food_item(I),
  update_nutrition_food_item(U), delete_nutrition_food_item(D)
- `beck_assessments`: save_beck_assessment(I), get_beck_assessment(S),
  get_beck_assessments_by_athlete(S), get_latest_beck_assessment(S)
- `ble_devices`: register_ble_device(I), get_ble_devices(S), get_ble_device(S),
  update_ble_device(U), unregister_ble_device(D), mark_ble_device_connected(U),
  mark_ble_device_synced(U)
- `user_consent`: save_consent(I), get_consent(S), get_consents_by_athlete(S)
- `legal_acceptances`: save_legal_acceptance(I),
  get_legal_acceptances_by_athlete(S), has_accepted_version(S)
- `ai_audit_log`: save_ai_audit_log(I), get_ai_audit_logs_by_athlete(S)
- `fitness_states`: get_fitness_states_by_athlete(S)
- infra: get_db_connection, init_db, _ensure_sync_tables,
  _ensure_external_identity_index, create_indices, backup_database,
  get_backup_dir, rotate_backups, scheduled_backup, _row_to_sync_entity_state,
  _row_to_ride, _row_to_athlete, _row_to_calendar_event, get_athlete_by_query,
  _beck_severity

## Conclusione
- Totale def: 147
- MIGRATED (con dispatch `has_postgres`): **32**   ← (AGENTS.md citava "24":
  l'analisi reale ne trova 32: 10 atleta + 10 rides/stress + 11 itinerari)
- SQLITE-ONLY (nessun dispatch): **115**
- **115 funzioni mancano del dispatch `has_postgres`** → continueranno a leggere/
  scrivere solo su SQLite (dati persi al resume su Render), incluse auth
  (`users`), OAuth credenziali, HR, sensor, metabolic, food, chat, calendar,
  weather cache, road incidents, route safety, POI, nutrition, BLE, consent,
  legal, audit, fitness_states.
