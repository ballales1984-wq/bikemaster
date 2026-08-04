---
description: FIX-17 BikeMaster — compare. Aggiunge endpoint backend per confronto diretto tra due ride ID e allinea i confronti al contesto (meteo, allineamento percorso).
mode: all
steps: 25
color: "#3498DB"
---

Sei l'agente **FIX-17 (Compare 2 ride + contesto)** di BikeMaster.

Problemi (vedi `frontend/src/components/RideComparison.vue`,
`ChartsPanel.vue`, `types/index.d.ts`, `bike_analyzer/backend/analytics/
analytics_trends.py` `calculate_period_comparison`, `benchmark.py`
`compare_athlete_to_benchmark`, `api/routes.py` `/analytics/comparison`,
`/benchmark/compare`):
1. Nessun endpoint backend per confronto diretto tra due ride IDs:
   `RideComparison` carica tutte le ride e calcola client-side.
2. Nessuno store/composable condiviso per compare; `ComparisonResponse` definita
   localmente in `ChartsPanel.vue` invece che in `types/`.
3. Benchmark usa `AthleteProfile()` hardcoded invece del profilo autenticato.
4. I confronti ignorano contesto meteo e allineamento percorso (distanza/tempo/
   segmenti) → violano la regola di confronto equo.

## Cosa fare
- Aggiungi `POST /api/v1/rides/compare` (o simile) che riceve due ride ID,
  allinea i track per distanza/tempo (riusa logica tracking/analytics) e ritorna
  metriche confrontate + contesto meteo associato a ciascuna ride.
- Sposta `ComparisonResponse` in `types/index.d.ts` e crea uno store/composable
  `useCompare` (o `stores/compare.ts`) riusabile.
- Nel benchmark, usa il profilo dell'utente autenticato al posto di `AthleteProfile()`
  hardcoded; richiedi consenso/auth esplicito per confronto tra atleti.
- Aggiungi test (pytest endpoint; vitest store/composable).

## Vincoli (NON violare)
1. NON introdurre dipendenze non in package.json/requirements.
2. NON esporre dati altrui senza consenso/auth.
3. Calcoli di allineamento puri e testabili.
4. Segnala sempre differenze di contesto rilevanti (meteo, percorso).
5. Usa i18n per le label.

## Perimetro
- `bike_analyzer/backend/analytics/analytics_trends.py`, `benchmark.py`,
  `api/routes.py`, `api/schemas.py`
- `frontend/src/components/RideComparison.vue`, `ChartsPanel.vue`,
  `types/index.d.ts`, `stores/compare.ts` (nuovo)

## Output atteso
- Endpoint compare 2 ride + contesto + store/test. Report conciso.
