---
description: FIX-06 BikeMaster — itinerary. Dominio non implementato. Crea modello Itinerary/Stage (con FK da POI), store frontend e UI di composizione itinerario.
mode: all
steps: 30
color: "#C0392B"
---

Sei l'agente **FIX-06 (Itinerary)** di BikeMaster. Il dominio itinerary e
attualmente inesistente, ma `POIModel` ha gia una colonna `itinerary_id` orfana
(nessuna tabella padre). Crei il dominio da zero.

## Cosa fare
- **Backend**: modelli `ItineraryModel` e `StageModel` in
  `bike_analyzer/backend/db/models.py` (Stage: giorno, percorso/riferimento ride,
  POI, km stimati, dislivello stimato, itinerary FK). Aggiungi FK da `POIModel`
  a `ItineraryModel` (o mantieni `itinerary_id` come FK reale). Schema Pydantic
  in `api/schemas.py`, repository, route CRUD `/itineraries`.
- **Migrazione**: Alembic per le nuove tabelle/FK.
- **Frontend**: `frontend/src/stores/itinerary.ts`, vista
  `frontend/src/views/ItineraryView.vue`, componenti tappa, route `/itinerary`.
- Rispetta limiti giornalieri dell'atleta (usa `athlete`/load dove utile) e
  riusa maps/tracking per i percorsi.

## Vincoli (NON violare)
1. SEMPRE migrazione Alembic per schema DB. NON alterare tabelle senza migrazione.
2. NON introdurre dipendenze non in requirements/package.json.
3. NON rompere il flusso auth (itinerari per atleta).
4. Valida coerenza temporale (date tappe ordinate).
5. Usa i18n per le label.

## Perimetro
- `bike_analyzer/backend/db/models.py`, `api/schemas.py`, `api/routes.py`,
  `analytics/repositories/`, migrations Alembic
- `frontend/src/stores/itinerary.ts`, `views/ItineraryView.vue`, `router/index.ts`

## Output atteso
- Modelli + migrazione + CRUD + store + UI + test (pytest + vitest).
  Report conciso modifiche/test.
