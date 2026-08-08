# BikeMaster — Progetto Miglioramento Visualizzazione Dati

## 1. Visione

Trasformare la visualizzazione dei dati da raccolta di grafici statici a sistema coeso, interattivo e accessibile che permetta all'atleta di comprendere immediatamente il proprio stato, le tendenze e le azioni consigliate.

## 2. Audit Stato Attuale

### Stack
- **Chart.js v4.5** + `chartjs-adapter-date-fns`
- **Leaflet** + `leaflet.heat` per heatmap GPS
- Wrapper custom `BaseChart.vue` + composable `useChart.ts`
- Theme system `chartTheme.ts` (light/dark)

### Componenti esistenti
| Componente | Tipo | Note |
|------------|------|------|
| `BaseChart.vue` | Wrapper generico | Buona base, mancano export/annotazioni |
| `ChartsPanel.vue` | Trend + mensile + confronto | Config duplicata, nessuna drill-down |
| `PerformancePanel.vue` | FTP history + stima | Grafico statico, nessun tooltip avanzato |
| `MetricHistoryChart.vue` | Storico metrica atleta | Rigido (solo line chart) |
| `MetabolicCharts.vue` | TDEE/Intake/Bilancio | 3 linee, nessuna zona/range |
| `Hr24hPanel.vue` | FC 24h | Template duplicato, nessun annotation |
| `FitnessChart.vue` | ATL/CTL/TSB | Base funzionale |
| `HeatmapPanel.vue` | Mappa Leaflet | Separata dal resto |
| `DashboardPanel.vue` | Score rings + barre fitness | Custom SVG/div, non riutilizzabile |

### Problemi identificati
1. **Duplicazione configurazione**: ogni componente ricrea `ChartConfiguration` con opzioni simili
2. **Nessuna interazione avanzata**: mancano zoom, pan, crosshair, annotazioni
3. **Export assente**: impossibile salvare grafici come PNG/CSV
4. **Empty state uniforme**: solo "Nessun dato", nessuna guida
5. **Accessibilità limitata**: ARIA incompleta, nessun keyboard nav su tooltip
6. **Performance**: dataset grandi non ottimizzati (nessun decimation)
7. **Mobile**: touch interaction minima, tooltip piccoli
8. **Nessun sparkline**:卡片 senza mini-grafici
9. **Comparazione limitata**: solo confronto 2 periodi, nessun overlay diretto

## 3. Obiettivi

### O1 — Coerenza e riduzione duplicazione
- [ ] Creare `useChartConfig.ts` con factory functions riutilizzabili
- [ ] Creare componenti specializzati (`LineChart`, `BarChart`, `AreaChart`, `Sparkline`) che estendono `BaseChart`
- [ ] Centralizzare palette, formati data, unità di misura

### O2 — Interattività avanzata
- [ ] Aggiungere plugin Chart.js per zoom/pan (hammerjs o chartjs-plugin-zoom)
- [ ] Crosshair tooltip condiviso tra dataset
- [ ] Annotazioni su eventi chiave (test FTP, gare, infortuni)
- [ ] Click su punto → drill-down a dettaglio uscita

### O3 — Export e condivisione
- [ ] Export PNG via `chartjs-plugin-image`
- [ ] Export CSV dei dati sottostanti
- [ ] Share card (immagine + summary) per social

### O4 — UX mobile
- [ ] Tooltip touch-friendly (più grandi, swipe per navigare)
- [ ] Grafici adattati a viewport strette
- [ ] Pull-to-refresh su pannelli dati

### O5 — Accessibilità
- [ ] ARIA labels su ogni grafico
- [ ] Tab navigation tra punti tooltip
- [ ] Screen reader announcements per trend/key metrics

### O6 — Performance
- [ ] Decimation per dataset > 500 punti
- [ ] Lazy rendering fuori viewport
- [ ] ResizeObserver con debounce

## 4. Fasi di implementazione

### Fase 1 — Fondamento (Settimana 1)
- [ ] `src/components/charts/LineChart.vue`
- [ ] `src/components/charts/BarChart.vue`
- [ ] `src/components/charts/AreaChart.vue`
- [ ] `src/composables/useChartConfig.ts`
- [ ] `src/utils/chartDefaults.ts` (default opzioni, formati)
- [ ] Aggiornare `BaseChart.vue` per supportare nuovi plugin

### Fase 2 — Migrazione componenti (Settimana 2)
- [ ] Migrare `ChartsPanel.vue` → nuovi componenti
- [ ] Migrare `PerformancePanel.vue`
- [ ] Migrare `MetricHistoryChart.vue`
- [ ] Migrare `MetabolicCharts.vue`
- [ ] Migrare `FitnessChart.vue`

### Fase 3 — Interattività (Settimana 3)
- [ ] chartjs-plugin-zoom (pinch + wheel)
- [ ] Custom crosshair plugin
- [ ] Annotation layer per eventi
- [ ] Drill-down handler (emits `point-click`)

### Fase 4 — Export & Mobile (Settimana 4)
- [ ] Export PNG button overlay
- [ ] Export CSV utility
- [ ] Mobile touch tooltip redesign
- [ ] Responsive breakpoints per grafici

### Fase 5 — Polish (Settimana 5)
- [ ] Accessibility audit (ARIA, keyboard, screen reader)
- [ ] Performance profiling (decimation test)
- [ ] Empty state redesign con illustrazioni/mini guide
- [ ] Tests (Vitest) per componenti critici

## 5. Struttura proposta

```
frontend/src/
├── components/
│   ├── charts/
│   │   ├── BaseChart.vue          (esistente, aggiornato)
│   │   ├── LineChart.vue          (nuovo)
│   │   ├── BarChart.vue           (nuovo)
│   │   ├── AreaChart.vue          (nuovo)
│   │   ├── Sparkline.vue          (nuovo)
│   │   ├── ChartExportMenu.vue    (nuovo)
│   │   └── ChartEmptyState.vue    (nuovo)
│   ├── ChartsPanel.vue            (refactorizzato)
│   └── ...
├── composables/
│   ├── useChart.ts                (esistente)
│   ├── useChartConfig.ts          (nuovo)
│   └── useChartExport.ts          (nuovo)
├── utils/
│   ├── chartTheme.ts              (esistente)
│   ├── chartDefaults.ts           (nuovo)
│   ├── chartFormatters.ts         (nuovo)
│   └── chartTypes.ts              (esistente)
└── types/
    └── chart.ts                   (nuovo)
```

## 6. Dipendenze candidate

| Pacchetto | Scopo | Priorità |
|-----------|-------|----------|
| `chartjs-plugin-zoom` | Zoom/pan touch + wheel | Alta |
| `chartjs-plugin-annotation` | Annotazioni eventi | Alta |
| `chartjs-plugin-datalabels` | Etichette su punti chiave | Media |
| `chartjs-plugin-image` | Export PNG | Media |

## 7. Metriche di successo

- **Tempo al primo insight** < 3s (da apertura app a grafico interpretabile)
- **Duplicazione codice** −70% (config Chart.js condivisa)
- **Lighthouse a11y** ≥ 95 su viste dati
- **FPS grafici** ≥ 50 su dataset 10k punti (mobile)

## 8. Rischi e mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Aggiunta plugin pesanti | Lazy load, tree-shaking, benchmark prima/after |
| Breaking change in BaseChart | Refactor incrementale, feature flags |
| Performance chart grandi | Decimation + virtualizzazione progressiva |
