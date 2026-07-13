# BikeMaster 2.0 — Schema Database

**Versione:** Bozza 1.0
**Riferimento:** discende da `bikemaster-architettura-tecnica.md`, sezione 5 (Dominio dei dati)

---

## 1. Approccio

Lo schema è relazionale per le entità anagrafiche/strutturali (atleta, bici, sessioni) e ottimizzato per serie temporali per la telemetria (`movement_points`). In produzione, `movement_points` è candidato a un database a serie temporali (es. TimescaleDB, InfluxDB) piuttosto che una tabella relazionale pura, ma qui è descritto in forma relazionale per chiarezza concettuale.

Convenzioni:
- `id` = chiave primaria, intero o UUID
- `*_id` = chiave esterna (FK)
- `json` = campo strutturato quando la cardinalità interna non giustifica una tabella dedicata

---

## 2. Tabelle

### 2.1 `athletes`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| name | string | |
| birth_date | date | usato per età |
| height_cm | number | |
| sex | enum | |
| experience_level | enum | principiante/intermedio/avanzato |
| goals | json | dimagrimento, performance, salute, gara |
| ftp_watts | number, nullable | |
| vo2max_estimated | number, nullable | |
| created_at | timestamp | |

### 2.2 `body_composition_logs`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| date | date | |
| weight_kg | number | |
| fat_mass_pct | number, nullable | |
| muscle_mass_pct | number, nullable | |
| circumferences | json, nullable | |
| hydration_pct | number, nullable | |

### 2.3 `daily_status`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| date | date | |
| sleep_hours | number | |
| sleep_quality | enum/number | |
| hrv | number | |
| resting_hr | number | |
| perceived_stress | number | scala 1-10 |
| pain_flags | json, nullable | zona, intensità |

### 2.4 `bikes`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| name | string | |
| type | enum | gravel/corsa/mtb/ecc. |
| weight_kg | number | |
| gear_ratios | json | |
| wheels | string | |
| tires | string | |
| created_at | timestamp | |

### 2.5 `bike_components`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| bike_id | FK → bikes | |
| component_type | enum | catena, gomme, freni, ecc. |
| install_date | date | |
| distance_km | number | km percorsi dal componente |
| maintenance_notes | text, nullable | |

### 2.6 `sessions`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| bike_id | FK → bikes, nullable | |
| source | enum | strava/gpx/fit/manuale/live |
| start_time | timestamp | |
| end_time | timestamp | |
| duration_moving_s | number | |
| duration_paused_s | number | |
| distance_total_km | number | |
| elevation_gain_m | number | |
| elevation_loss_m | number | |
| avg_speed_kmh | number | |
| max_speed_kmh | number | |
| avg_hr | number, nullable | |
| max_hr | number, nullable | |
| avg_power_w | number, nullable | |
| calories_kcal | number, nullable | |

### 2.7 `movement_points`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| session_id | FK → sessions | |
| timestamp | timestamp | |
| latitude | number | |
| longitude | number | |
| altitude_m | number | |
| speed_ms | number | |
| acceleration_ms2 | number, nullable | |
| direction_deg | number, nullable | |
| heart_rate | number, nullable | |
| power_w | number, nullable | |
| cadence_rpm | number, nullable | |

Indice consigliato: `(session_id, timestamp)`.

### 2.8 `territory_segments`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| type | enum | terreno/strada/montagna |
| geometry_type | enum | punto/linea/superficie/volume |
| geometry_data | json (GeoJSON) | |
| slope_pct | number, nullable | |
| surface_type | enum, nullable | asfalto/sterrato/ecc. |
| traffic_level | enum, nullable | |
| exposure | enum, nullable | per montagna: versante/esposizione |
| difficulty_score | number, nullable | calcolato da Territory Engine |

### 2.9 `session_territory_map`
| Campo | Tipo | Note |
|---|---|---|
| session_id | FK → sessions | |
| territory_segment_id | FK → territory_segments | |
| entry_time | timestamp | |
| exit_time | timestamp | |

Chiave primaria composta: `(session_id, territory_segment_id, entry_time)`.

### 2.10 `environment_readings`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| session_id | FK → sessions | |
| timestamp | timestamp | |
| temperature_c | number | |
| wind_speed_kmh | number, nullable | |
| wind_direction_deg | number, nullable | |
| humidity_pct | number, nullable | |
| pressure_hpa | number, nullable | |
| weather_condition | enum, nullable | |
| daylight | boolean, nullable | |
| air_quality_index | number, nullable | |

### 2.11 `knowledge_states`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| date | date | |
| fitness_state | json | vedi documento algoritmi |
| fatigue_state | json | |
| recovery_state | json | |
| performance_prediction | json, nullable | |
| generated_at | timestamp | |

### 2.12 `historical_aggregates`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| period_type | enum | settimana/mese/anno |
| period_start | date | |
| total_km | number | |
| total_hours | number | |
| total_elevation_m | number | |
| num_sessions | number | |
| personal_records | json, nullable | |

### 2.13 `imports`
| Campo | Tipo | Note |
|---|---|---|
| id | PK | |
| athlete_id | FK → athletes | |
| source_type | enum | strava/gpx/fit/altro |
| file_reference | string | |
| import_date | timestamp | |
| status | enum | in_corso/completato/errore |
| session_id | FK → sessions, nullable | valorizzato a import completato |

---

## 3. Relazioni principali (ER sintetico)

```
athletes 1—N body_composition_logs
athletes 1—N daily_status
athletes 1—N bikes
athletes 1—N sessions
athletes 1—N knowledge_states
athletes 1—N historical_aggregates
athletes 1—N imports

bikes 1—N bike_components
bikes 1—N sessions

sessions 1—N movement_points
sessions 1—N environment_readings
sessions N—N territory_segments (tramite session_territory_map)

imports 1—1 sessions (quando completato)
```

---

## 4. Note di implementazione

- `movement_points` cresce rapidamente (decine di righe al minuto per sessione live). Valutare partizionamento per `session_id` o migrazione a store a serie temporali quando il volume lo richiede.
- `territory_segments` è pensato per essere riutilizzabile tra sessioni diverse (stesso tratto di strada percorso da atleti/uscite diverse): non duplicare geometrie, collegare tramite `session_territory_map`.
- `knowledge_states` non deve mai essere scritto direttamente da Import/Tracking/Measurement Engine: è responsabilità esclusiva del Knowledge Layer, come definito nel documento di architettura.
