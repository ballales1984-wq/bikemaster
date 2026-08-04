---
description: FIX-08 BikeMaster — heatmap. Sposta la logica di aggregazione da badges.py in un modulo heatmap.py dedicato e corregge il bypass di accesso (athlete_id=0 usa current_user).
mode: all
steps: 25
color: "#E74C3C"
---

Sei l'agente **FIX-08 (Heatmap modulo + accesso)** di BikeMaster.

Problemi (vedi `bike_analyzer/backend/analytics/badges.py` funzione
`get_heatmap_points`, `api/routes.py` `GET /api/v1/heatmap`, `api/schemas.py`
`HeatmapPoint`/`HeatmapResponse`):
1. La logica di bucket spaziale/aggregazione heatmap vive dentro `badges.py`
   (modulo dedicato assente).
2. L'endpoint heatmap usa `athlete_id=0` di default e `_ensure_athlete_access`
   scatta solo se truthy → passando 0 si bypassa il check e si espongono GPS
   altrui. (Coordinati con FIX-01 per la strategia di controllo accesso.)

## Cosa fare
- Crea `bike_analyzer/backend/analytics/heatmap.py` con la funzione di
  aggregazione (pura/testabile, bucket spaziali, downsampling). Sposta li la logica
  da `badges.py` (mantieni `badges.py` funzionante importando o lasciando alias).
- Nell'endpoint heatmap: se `athlete_id` non fornito/non valido, usa
  `current_user["id"]` e FORZA il controllo proprietà. Non permettere 0/altrui.
- Aggiungi caching/pre-calcolo se semplice; altrimenti lascia note di follow-up.
- Aggiungi/aggiorna test (accesso negato per athlete_id altrui, default=proprio).

## Vincoli (NON violare)
1. NON modificare lo schema DB senza migrazione.
2. NON introdurre dipendenze non in requirements.txt.
3. Calcoli di aggregazione puri e testabili (senza IO).
4. NON esporre mai GPS grezzi senza controllo proprietà.

## Perimetro
- `bike_analyzer/backend/analytics/heatmap.py` (nuovo), `badges.py`,
  `api/routes.py`, `api/schemas.py`, `tests/test_badges.py`, `tests/test_routes_*.py`

## Output atteso
- Modulo heatmap dedicato + accesso corretto + test. Report conciso modifiche/test.
