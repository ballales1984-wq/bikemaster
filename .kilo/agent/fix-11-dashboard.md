---
description: FIX-11 BikeMaster — dashboard. Crea store Pinia di sintesi e fa usare gli store esistenti (rides/athlete/athleteState) invece di chiamate API dirette duplicate.
mode: all
steps: 25
color: "#9B59B6"
---

Sei l'agente **FIX-11 (Dashboard store)** di BikeMaster.

Problemi (vedi `frontend/src/components/DashboardPanel.vue`, widget sparsi
`StatsSummary.vue`/`ChartsPanel.vue`/`BaseChart.vue`/`AthleteStatePanel.vue`/
`ZonesPanel.vue`, `composables/useChart.ts`, `frontend/src/stores/*`):
1. `DashboardPanel.vue` chiama direttamente `apiGet("/api/v1/dashboard")` senza
   store Pinia dedicato → duplicazione fetch con altri store.
2. I widget non sono in `components/dashboard/` (struttura non conforme).
3. KPI incompleti: mancano TSS settimanale e readiness espliciti.
4. `StatsSummary.vue` non e integrato in `DashboardPanel.vue` (replica statistiche).

## Cosa fare
- Crea `frontend/src/stores/dashboard.ts` che aggreghi/derivi i KPI dagli store
  esistenti (`rides`, `athlete`, `athleteState`) o da un endpoint sintesi.
- Rendi `DashboardPanel.vue` consumatore dello store (rimuovi fetch diretti doppi).
- Sposta/i widget in `components/dashboard/` mantenendo i test.
- Aggiungi KPI TSS settimanale e readiness (se i dati esistono negli store/backend).
- Integra `StatsSummary.vue` invece di duplicare.

## Vincoli (NON violare)
1. NON introdurre dipendenze non in package.json.
2. NON rompere il flusso auth.
3. Rispetta il tema/design system esistente.
4. Mantieni responsive (mobile + Tauri WebView).
5. Usa i18n per le label.

## Perimetro
- `frontend/src/stores/dashboard.ts` (nuovo), `components/DashboardPanel.vue`,
  `components/dashboard/*`, `stores/rides.ts`, `stores/athlete.ts`,
  `stores/athleteState.ts`

## Output atteso
- Store dashboard + widget organizzati + KPI completi + test. Report conciso.
