---
description: FIX-14 BikeMaster — calendar. Crea store Pinia calendar e aggiunge il confronto carico pianificato vs effettivo (CompletedRide da rides reali) usando load-manager.
mode: all
steps: 25
<arg_key:6124c78e>color</arg_key:6124c78e>
<arg_value:6124c78e>"#2980B9"
---

Sei l'agente **FIX-14 (Calendar store + piano vs fatto)** di BikeMaster.

Problemi (vedi `frontend/src/components/CalendarPanel.vue`,
`components/calendar/CalendarGrid.vue`/`FitnessChart.vue`, `api/routes.py`
`/calendar/events`, `/training/load`, `db/models.py` `CalendarEventModel`,
`granfondo_planner.py`, `training_plan_generator.py`):
1. Nessuno store calendar dedicato (stato locale in `CalendarPanel.vue`).
2. `GranfondoPlanner.vue` salva il piano come `calendar_events` plain, perdendo
   metadati (zona, intensita, TSS stimato).
3. Il calendario carica ATL/CTL/TSB da `/training/load` ma NON correla carico
   pianificato vs carico effettivo (nessun confronto pianificato vs fatto).
4. Il flag `completed` e un toggle manuale, non sincronizzato con le uscite
   reali (`CompletedRide` assente).
5. `load-manager` (chronic load, ACWR) non e integrato nella UI calendario.

## Cosa fare
- Crea `frontend/src/stores/calendar.ts` che carica eventi e li deriva/aggiorna.
- Aggiungi la mappatura tra campi training plan (TSS stimato, target_intensity,
  workout_type) e gli eventi calendario (preserva i metadati).
- Implementa il confronto pianificato vs effettivo: lega gli eventi `completed`
  alle ride reali (per data/percorso) e mostra delta TSS/carico. Se serve un
  `CompletedRide`, proponi modello+FK (con migrazione) oppure riusa le ride.
- Integra indicatore load-manager (ACWR/TSB) nella vista calendario.
- Aggiungi test su logica slot/confronto.

## Vincoli (NON violare)
1. NON modificare lo schema DB senza migrazione (se serve `CompletedRide`/FK).
2. NON introdurre dipendenze non in package.json.
3. NON rompere il flusso auth (eventi per atleta).
4. Usa date in UTC + formattazione locale UI.
5. NON duplicare logica di generazione piani: leggi da training-plan-designer.

## Perimetro
- `frontend/src/stores/calendar.ts` (nuovo), `components/CalendarPanel.vue`,
  `components/calendar/*`
- `bike_analyzer/backend/api/routes.py`, `db/models.py`, `analytics/*`

## Output atteso
- Store calendar + confronto piano/fatto + test. Report conciso.
