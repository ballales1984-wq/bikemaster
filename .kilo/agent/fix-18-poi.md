---
description: FIX-18 BikeMaster — poi. Crea store Pinia POI dedicato, allinea i tipi POI frontend (viewpoint/cafe/bakery/water/bike_shop/emergency) a quelli backend (vista/fontana/ristoro/tecnico) e aggiunge la categoria caricabatterie.
mode: all
steps: 25
color: "#16A085"
---

Sei l'agente **FIX-18 (POI store + tipi)** di BikeMaster.

Problemi (vedi `frontend/src/views/PoiMapView.vue`, `RideMapPanel.vue`,
`locales/it.json`/`en.json`, `bike_analyzer/backend/db/models.py` `POIModel`,
`api/schemas.py` `POI_TYPES`, `api/routes.py` `/maps/pois`, `/maps/pois/nearby`,
`analytics/repositories/poi_repository.py`, `maps/poi_enrichment.py`):
1. Nessun componente POI riusabile (tutto in `PoiMapView.vue` monolitico) e nessuno
   store dedicato.
2. Manca endpoint backend PUT/PATCH per update POI.
3. Categoria `caricabatterie` assente sia in backend (`POI_TYPES`) che frontend.
4. `RideMapPanel.vue` usa tipi POI non allineati al backend (`viewpoint`, `cafe`,
   `bakery`, `water`, `bike_shop`, `emergency` vs `vista`, `fontana`, `ristoro`,
   `tecnico`) → colori/marker errati.

## Cosa fare
- Crea `frontend/src/stores/poi.ts` (o `usePoi`) che carica/gestisce i POI e
  un componente `PoiMarker.vue` riusabile estratto da `PoiMapView.vue`.
- Allinea i tipi POI: definisci un unico set canonico (backend `POI_TYPES` come
  fonte) e mappa i nomi frontend/icona colore. Aggiorna `RideMapPanel.vue` e
  `PoiMapView.vue` a usare il set canonico.
- Aggiungi categoria `caricabatterie` in `POI_TYPES` + i18n + icona. Aggiorna
  label `panorami`→`vista` con mappatura documentata.
- Aggiungi endpoint `PUT /maps/pois/{id}` per update (auth + proprieta). Modella
  il campo `source`.
- Aggiungi test (vitest store; pytest route update/tipi).

## Vincoli (NON violare)
1. NON introdurre dipendenze non in package.json/requirements.
2. NON rompere il flusso auth (POI per atleta dove applicabile).
3. Gestisci dati esterni (SerpApi) con rate-limit e cache.
4. Coordinate sempre validate (range lat/lon).
5. Usa i18n per le label.

## Perimetro
- `frontend/src/stores/poi.ts` (nuovo), `views/PoiMapView.vue`,
  `components/PoiMarker.vue` (nuovo), `RideMapPanel.vue`, `locales/*`
- `bike_analyzer/backend/db/models.py`, `api/schemas.py`, `api/routes.py`,
  `analytics/repositories/poi_repository.py`

## Output atteso
- Store POI + tipi allineati + categoria caricabatterie + update + test. Report.
