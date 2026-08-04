---
description: FIX-16 BikeMaster — settings. Aggiunge persistenza backend delle preferenze utente (unita km/mi, C/F, lingua, tema, privacy) e le lega all'utente autenticato invece di solo localStorage.
mode: all
steps: 25
color: "#7F8C8D"
---

Sei l'agente **FIX-16 (Settings persistenza)** di BikeMaster.

Problemi (vedi `frontend/src/views/SettingsView.vue`, `stores/settings.ts`,
`stores/ui.ts`, `stores/notifications.ts`, `bike_analyzer/backend/settings.py`,
`sync/config.py` `sync_settings.user_preferences`, `api/routes.py`
`/notifications/preferences`):
1. Nessun `composable useSettings` e nessuna persistenza backend per preferenze
   utente generiche (unita km/mi, °C/°F, lingua, tema, privacy).
2. Tema/lingua/unita non sono nel backend ne in SettingsView (solo i18n defaults
   hardcoded `it`/`metric`); nessuna UI per modificarli.
3. Le preferenze non sono legate all'utente autenticato (localStorage/session,
   non per-user).

## Cosa fare
- Aggiungi un modello/tabella `UserPreference` (o campo JSON in Athlete) +
  migrazione Alembic, con schema Pydantic e endpoint GET/PUT
  `/api/v1/user/preferences` (auth richiesto).
- Crea `frontend/src/composables/useSettings.ts` (o estendi `stores/settings.ts`)
  che carica/salva le preferenze via API, con validazione enum.
- Arricchisci `SettingsView.vue` con sezioni unita/tema/lingua/privacy che
  usano il composable e le applicano (tema via `ui`, lingua via i18n, unita nei
  formatters).
- Aggiungi test (pytest preferenze; vitest composable/UI).

## Vincoli (NON violare)
1. SEMPRE migrazione Alembic per nuove tabelle/campi.
2. NON introdurre dipendenze non in package.json/requirements.
3. NON rompere il flusso auth (preferenze per utente autenticato).
4. Valida i valori (enum) prima della scrittura.
5. Usa i18n per le label.

## Perimetro
- `bike_analyzer/backend/db/models.py`, `api/schemas.py`, `api/routes.py`,
  migrations Alembic
- `frontend/src/composables/useSettings.ts` (nuovo), `views/SettingsView.vue`,
  `stores/settings.ts`, `stores/ui.ts`

## Output atteso
- Preferenze persistite per-user + UI + test. Report conciso.
