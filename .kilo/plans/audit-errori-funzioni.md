# Piano Audit BikeMaster — Controllo Funzioni e Errori

## Data
2026-06-11

## Obiettivo
Controllare tutte le funzioni del programma, identificare e correggere errori, bug e problemi di codice.

## Stato esecuzione

### ✅ Completati
| ID | File | Descrizione |
|----|------|-------------|
| E1 | `analytics_trends.py:437` | **NOT A BUG** - `avg_ride_duration_min` è già nel return (line 458) |
| E2 | `ai_coach.py:365` | ✅ Fixato - KB ora usata nel fallback recovery advice |
| E3 | `routes.py:536-544` | ✅ Fixato - Aggiunto `/api/v1/admin/athletes` per lista atleti |
| E4 | `vite.config.js:28-37` | ⏳ Da verificare - Workbox 404 ancora potrebbe verificarsi in build |
| E5 | `database.py:260-277` | ✅ Fixato - ORDER BY ora usa f-string con whitelist sicura |
| E6 | `test_coverage_gaps.py:255,262` | ✅ Fixato - Rimosso test duplicato, rimosso metodo orfano |
| E7 | `database.py:350-358` | ✅ Fixato - Rimosso apertura connessione inutile in `_row_to_athlete` |

### ✅ Verifiche preliminare
- `fatigue.py:13` - ✅ Già ha guard `if rider_age < 220 else 0.5`
- `ai_coach.py:13` - ✅ Import già presente per `create_speed_chart`, `create_duration_chart`

## Risultato test
```
396 passed, 50637 warnings in 60.0s
```
