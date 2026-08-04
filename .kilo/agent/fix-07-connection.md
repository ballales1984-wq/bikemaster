---
description: FIX-07 BikeMaster — connection. Centralizza il token store (modello ExternalTokenModel generico), espone stato connessione in /providers, e revoca i token OAuth al logout globale.
mode: all
steps: 25
color: "#2ECC71"
---

Sei l'agente **FIX-07 (Connection token store)** di BikeMaster.

Problemi (vedi `bike_analyzer/backend/api/routes.py`,
`bike_analyzer/backend/ingestion/{strava_client,wahoo_client,google_oauth_store,google_fit,google_health}.py`,
`db/models.py`, `frontend/src/stores/connections.ts`,
`frontend/src/views/ConnectionsView.vue`):
1. Ogni provider usa una tabella SQLite dedicata invece del modello generico
   `ExternalTokenModel` (gia esistente ma non usato).
2. `GET /api/v1/import/providers` restituisce solo flag di configurazione, non lo
   stato connessione → il frontend si aspetta `connections` ed e sempre
   `disconnected`.
3. Il logout globale non revoca i token OAuth esterni (vedi anche FIX-02).

## Cosa fare
- Usa `ExternalTokenModel` come store unico per Strava/Wahoo/Garmin/Google Fit/
  Health (migrazione se necessario). Astrai la lettura/scrittura/revoca.
- Arricchisci `/import/providers` (o aggiungi `/connections/status`) per ritornare
  lo stato reale per provider (`connected`/`expired`/`error`).
- Assicurati che la revoca OAuth sia richiamabile dal logout (coordinati con FIX-02:
  puoi esporre una funzione/endpoint riusabile).
- Allinea `connections.ts` e `ConnectionsView.vue` allo stato reale.

NOTA progetto: la logica OAuth e duplicata tra `ConnectionsView.vue` e
`ImportPanel.vue` (separazione mantenuta per decisione); non fare refactoring
massiccio, limitati a rendere lo stato corretto.

## Vincoli (NON violare)
1. NON committare secret: variabili d'ambiente / secret manager.
2. NON introdurre dipendenze non in requirements/package.json.
3. NON rompere il flusso auth/OAuth esistente (`stores/auth.ts`).
4. Revoca best-effort, non bloccante.

## Perimetro
- `bike_analyzer/backend/db/models.py`, `ingestion/*`, `api/routes.py`
- `frontend/src/stores/connections.ts`, `views/ConnectionsView.vue`

## Output atteso
- Token store unificato + stato connessione + test. Report conciso modifiche/test.
