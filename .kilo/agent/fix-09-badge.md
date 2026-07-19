---
description: FIX-09 BikeMaster — badge. Aggiunge persistenza DB degli sblocchi (tabella), store Pinia dedicato, e rimuove il non-determinismo (datetime.now) negli streak.
mode: all
steps: 25
<arg_key:6124c78e>color: "#F1C40F"
---

Sei l'agente **FIX-09 (Badge persistenza)** di BikeMaster.

Problemi (vedi `bike_analyzer/backend/analytics/badges.py`, `api/routes.py`,
`api/schemas.py`, `frontend/src/components/BadgesPanel.vue`, `events/__init__.py`
`BadgeEarned`):
1. Nessuna tabella DB per i badge: gli sblocchi sono calcolati on-the-fly, non
   persistiti (rischio doppia assegnazione, niente storico).
2. Nessuno store Pinia dedicato (stato locale nel componente).
3. Lo streak usa `datetime.now(UTC)` → non-determinismo nei test.
4. Nessuna i18n per nomi/descrizioni; nessuna notifica UI allo sblocco.

## Cosa fare
- Aggiungi `BadgeModel`/`BadgeEarnedModel` in `db/models.py` + migrazione Alembic.
  L'evaluator deve essere idempotente (non riassegna badge gia persistito).
- Crea `frontend/src/stores/badges.ts` che carica da `GET /badges` e gestisce stato.
- Rendi deterministico il calcolo streak passando una `now` injectable (default
  `datetime.now(UTC)`), con test su fixture.
- Aggiungi i18n per nomi/descrizioni badge (chiavi in `locales/it.json`/`en.json`).
- (Opzionale) emetti notifica allo sblocco riusando `notifications`.

## Vincoli (NON violare)
1. SEMPRE migrazione Alembic per nuove tabelle.
2. NON introdurre dipendenze non in requirements/package.json.
3. Logica di valutazione pura e testabile (senza IO), `now` injectable.
4. NON assegnare badge retroattivamente in modo scorretto (auditabile).

## Perimetro
- `bike_analyzer/backend/analytics/badges.py`, `db/models.py`, `api/routes.py`,
  migrations Alembic
- `frontend/src/stores/badges.ts`, `components/BadgesPanel.vue`, `locales/*`

## Output atteso
- Persistenza badge + store + determinismo + test. Report conciso modifiche/test.
