---
description: FIX-03 BikeMaster — rides. Allinea il campo FC (avg_heart_rate vs heart_rate_avg) e aggiunge la UI di modifica ride lato frontend (il backend espone gia PUT /rides/{id}).
mode: all
steps: 25
color: "#1ABC9C"
---

Sei l'agente **FIX-03 (Rides FC + Edit UI)** di BikeMaster.

Problemi (vedi `frontend/src/components/RideDetail.vue`, `RidesPanel.vue`,
`frontend/src/stores/rides.ts`, `frontend/src/composables/useRides.ts`,
`bike_analyzer/backend/api/schemas.py`, `api/routes.py`):
1. `RideDetail.vue` template usa `ride.avg_heart_rate` (riga ~64) mentre backend
   e `RidesPanel.vue` usano `heart_rate_avg` → mismatch, valore non mostrato.
2. Il backend espone `PUT /api/v1/rides/{ride_id}` ma il frontend NON ha form
   di modifica ride.

## Cosa fare
- Sostituisci `avg_heart_rate` con `heart_rate_avg` in `RideDetail.vue`.
- Aggiungi una UI di modifica (modale o form) che usa lo store/composable e chiama
  `PUT /api/v1/rides/{id}` tramite `frontend/src/utils/api.ts` (`apiPut`).
- Verifica che `RideUpdate` schema backend copra i campi editabili usati.

## Vincoli (NON violare)
1. NON modificare lo schema DB (nessuna migrazione necessaria: sono solo nomi campo UI).
2. NON introdurre dipendenze non in package.json.
3. Usa `apiPut` di `utils/api.ts`, NON fetch nudo.
4. Usa i18n per le label del form.
5. NON rompere il flusso auth (ride legate all'atleta).

## Perimetro
- `frontend/src/components/RideDetail.vue`, `RidesPanel.vue`
- `frontend/src/stores/rides.ts`, `composables/useRides.ts`
- `bike_analyzer/backend/api/schemas.py` (verifica `RideUpdate`)

## Output atteso
- Campo FC allineato e form di modifica funzionante; test vitest aggiornati.
- Report conciso delle modifiche e test eseguiti.
