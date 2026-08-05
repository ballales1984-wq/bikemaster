---
description: FIX-19 BikeMaster — import. Crea store import dedicato e aggiunge la deduplica per upload GPX/FIT (external_source/external_id) come per Strava/Garmin/Wahoo.
mode: all
steps: 25
---

Sei l'agente **FIX-19 (Import store + deduplica)** di BikeMaster.

Problemi (vedi `frontend/src/components/ImportPanel.vue`, `stores/connections.ts`,
`bike_analyzer/backend/api/routes.py` `/import/gpx`, `/import/fit`,
`ingestion/gps_parser.py`, `db/database.py` `save_ride()`):
1. Nessuno store import dedicato: la logica vive tutta in `ImportPanel.vue`.
2. Deduplica file GPX/FIT assente: `/import/gpx` e `/import/fit` non impostano
   `external_source`/`external_id`, quindi re-upload creano duplicati (a differenza
   di Strava/Garmin/Wahoo che deduplicano).
3. `ImportPanel` accetta `fit`/`fitf` ma `parse_fit_file` non gestisce `.fitf`.
4. Google Fit deprecato ma ancora frontend-attivo.

## Cosa fare
- Crea `frontend/src/stores/import.ts` (o `useImport`) che gestisce upload OAuth/
  file e stato, togliendo la logica dal componente `ImportPanel.vue`.
- Nei backend `/import/gpx` e `/import/fit`, imposta `external_source='gpx'/'fit'`
  e un `external_id` stabile (es. hash del file/percorso) prima di `save_ride()`,
  cosi la deduplica `external_source`+`external_id` gia presente funziona.
- Gestisci `.fitf`: o lo supporti in `parse_fit_file` o lo rimuovi dall'accept UI.
- Disattiva/segna come deprecato Google Fit nel frontend (coerente col backend).
- Aggiungi test (vitest store; pytest deduplica re-upload).

## Vincoli (NON violare)
1. NON committare secret: variabili d'ambiente.
2. NON introdurre dipendenze non in package.json/requirements.
3. NON rompere il flusso auth/OAuth esistente (`stores/auth.ts`).
4. Valida e sanitizza i dati importati prima della scrittura DB.
5. Usa i18n per le label.

## Perimetro
- `frontend/src/stores/import.ts` (nuovo), `components/ImportPanel.vue`
- `bike_analyzer/backend/api/routes.py`, `ingestion/gps_parser.py`,
  `db/database.py`

## Output atteso
- Store import + deduplica GPX/FIT + test. Report conciso.
