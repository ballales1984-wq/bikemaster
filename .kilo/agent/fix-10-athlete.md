---
description: FIX-10 BikeMaster — athlete. Completa AthleteUpdate (equipment/medical/ftp), crea vista profilo dedicata, aggiunge test validazione e applica i18n (label hardcoded).
mode: all
steps: 25
color: "#E67E22"
---

Sei l'agente **FIX-10 (Athlete profilo)** di BikeMaster.

Problemi (vedi `bike_analyzer/backend/db/models.py` `AthleteModel`,
`api/schemas.py` `AthleteCreate`/`AthleteUpdate`, `api/routes.py` `/athletes`,
`frontend/src/stores/athlete.ts`, `components/AthletePanel.vue`, `types/index.d.ts`):
1. `AthleteUpdate` omette `ftp_watts`, `equipment`, `medical_notes` (presenti nel
   modello/Create) → non aggiornabili via API.
2. Nessuna vista profilo dedicata (solo `AthletePanel` pannello); mancano UI per
   equipment/medical/ftp e serie storiche peso/FTP.
3. Type frontend `Athlete` diverge dal backend (`username`/`goal_type` vs `name`/
   `goals`); nessun mapping univoco.
4. `AthletePanel.vue` e `stores/athlete.ts` usano label hardcoded (i18n non usato).
5. Nessun test di validazione/aggiornamento profilo.

## Cosa fare
- Estendi `AthleteUpdate` con i campi mancanti; verifica PUT `/athletes/me` e
  `/athletes/{id}` li accettino.
- Crea/completa una vista profilo (`frontend/src/views/AthleteProfileView.vue` o
  arricchisci `AthletePanel`) con sezioni equipment, medical, ftp, serie storiche.
- Allinea il type `Athlete` al modello backend (o aggiungi mapping esplicito nello
  store). Unifica i percorsi `/athletes/me` (store) e `/athletes/{id}` (panel).
- Applica i18n (`composables/useI18n.ts`) a label profilo.
- Aggiungi test (pytest su update schema; vitest su store/profilo).

## Vincoli (NON violare)
1. NON modificare lo schema DB senza migrazione (i campi esistono gia nel modello;
   verifica prima di aggiungerne di nuovi).
2. NON introdurre dipendenze non in requirements/package.json.
3. NON rompere il flusso auth (profilo per atleta autenticato).
4. Dati medici sensibili: mai esposti via API non autorizzate.

## Perimetro
- `bike_analyzer/backend/db/models.py`, `api/schemas.py`, `api/routes.py`
- `frontend/src/stores/athlete.ts`, `components/AthletePanel.vue`,
  `views/AthleteProfileView.vue`, `types/index.d.ts`, `locales/*`

## Output atteso
- Profilo completo + API coerente + i18n + test. Report conciso modifiche/test.
