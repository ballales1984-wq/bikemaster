---
description: FIX-15 BikeMaster — weather. Crea store Pinia weather e aggiunge un backfill del meteo storico sulle uscite/eventi esistenti (colonne weather_* gia presenti).
mode: all
steps: 25
color: "#5DADE2"
---

Sei l'agente **FIX-15 (Weather store + backfill)** di BikeMaster.

Problemi (vedi `bike_analyzer/backend/weather/weather_service.py`,
`api/routes.py` `/weather`, `/weather/forecast`, `db/models.py` `WeatherCache`/
colonne `weather_*` su rides/calendar, `database.py`, `frontend/src/components/
WeatherPanel.vue`, `RideMapPanel.vue`, `SettingsView.vue`):
1. Nessuno store Pinia/Vue dedicato al weather nel frontend (ricerca `useWeather`/
   `weatherStore` negativa).
2. `rides` e `calendar_events` han colonne meteo ma nessun processo di backfill
   per uscite/eventi passati.
3. `RideMapPanel` chiama `/api/v1/weather` in parallelo per ogni uscita senza
   gestione rate-limit UI.
4. `WeatherPanel` espone solo current/forecast; non c'e vista "meteo storico
   uscita".

## Cosa fare
- Crea `frontend/src/stores/weather.ts` (o `useWeather`) che centralizza fetch
  current/forecast e stato, con gestione loading/errore/rate-limit.
- Aggiungi un endpoint/CLI o script backend (`scripts/backfill_weather.py` o route
  admin) che popola `weather_*` sulle rides/calendar mancanti usando
  `weather_service` con cache e rate-limit. Testalo su fixture.
- Usa lo store nei componenti (`WeatherPanel`, `RideMapPanel`) al posto di chiamate
  dirette ripetute; aggiungi vista/section "meteo storico uscita" se semplice.
- Aggiungi test (vitest store; pytest backfill).

## Vincoli (NON violare)
1. NON introdurre dipendenze non in requirements/package.json.
2. NON hardcodare API key: variabili d'ambiente.
3. Gestisci rate-limit/offline con cache; NON bloccare l'UI su chiamate lente.
4. NON rompere il flusso auth.

## Perimetro
- `frontend/src/stores/weather.ts` (nuovo), `components/WeatherPanel.vue`,
  `RideMapPanel.vue`
- `bike_analyzer/backend/weather/weather_service.py`, `api/routes.py`,
  `db/models.py`, `database.py`, script backfill

## Output atteso
- Store weather + backfill + test. Report conciso.
