# Piano di Miglioramento Frontend e UX - BikeMaster

## Executive Summary

Il frontend BikeMaster è un'applicazione Vue 3 SPA con styling CSS personalizzato. Attualmente presenta:
- **Punti di forza**: Architettura modulare con componenti, skeleton loading, toast notifications, responsive design
- **Aree di miglioramento**: Nessuna libreria UI, CSS monolitico, nessun routing, nessun TypeScript, integrazione API parziale

---

## FASE 1: Miglioramenti Critici (2-3 settimane)

### 1.1 Routing con Vue Router
- **Motivazione**: Deep linking, navigazione browser, migliore esperienza utente
- **Task**:
  - Installare `vue-router`
  - Creare route per ogni tab (rides, import, coach, calendar, etc.)
  - Aggiornare App.vue per usare `<router-view>`
  - Aggiungere route guards per autenticazione

### 1.2 TypeScript Migration
- **Motivazione**: Type safety, migliore manutenibilità, riduzione errori
- **Task**:
  - Configurare `tsconfig.json`
  - Rinominare `.js` → `.ts` in `src/`
  - Aggiungere interfacce per API response (Ride, Athlete, Coach, etc.)
  - Tipizzare component props e emits

### 1.3 State Management con Pinia
- **Motivazione**: Stato globale coerente, persistenza, debuggability
- **Task**:
  - Creare store `auth` per token/user
  - Creare store `rides` per rides/statistics
  - Creare store `athlete` per profile data
  - Sostituire ref locali con store Pinia

---

## FASE 2: Miglioramenti UI/UX (3-4 settimane)

### 2.1 Libreria Componenti
- **Opzione A - Naive UI** (consigliato per Vue 3)
  - Installazione leggera, buona integrazione con Vue 3
  - Componenti: NCard, NButton, NInput, NSelect, NModal
- **Opzione B - PrimeVue**
  - Più completo, tema scuro integrato
  - Componenti avanzati: Calendar, Chart, DataTable

### 2.2 Design System
- **Task**:
  - Rimuovere duplicazioni in `index.css`
  - Creare file CSS modulare (`styles/variables.css`, `styles/components.css`, `styles/utilities.css`)
  - Unificare variabili CSS (`--radius`, `--shadow`, colori)
  - Aggiungere dark/light theme toggle

### 2.3 Accessibilità (a11y)
- **Task**:
  - Aggiungere `aria-label` e attributi ARIA
  - Gestire focus trap nei modal
  - Scansione con tastiera (keyboard navigation)
  - Contrast ratio check (WCAG 2.1 AA)

---

## FASE 3: Feature Completeness (4-5 settimane)

### 3.1 Integrazione Backend Completa
| Component | API Mancanti | Priorità |
|-----------|--------------|----------|
| AthletePanel | Update profilo (PUT /athletes/me) | Alta |
| CalendarPanel | Creazione eventi, filtri avanzati | Alta |
| GranfondoPlanner | Salvataggio itinerari, export GPX | Media |
| WeatherPanel | Integrazione API meteo reale | Media |
| BadgesPanel | Notifiche badge sbloccati | Bassa |

### 3.2 Nuove Features UX
- **Progressive Onboarding**: Tour guidato per nuovi utenti
- **Empty States Illustrativi**: Icone/illustrazioni quando non ci sono dati
- **Pull-to-refresh**: Per mobile (Capacitor)
- **Offline Support**: Cache strategica con Workbox
- **Search & Filter**: Ricerca globale rides/athlete

---

## FASE 4: Performance & Testing (2-3 settimane)

### 4.1 Performance
- **Bundle Optimization**:
  - Code splitting per route (lazy loading)
  - Tree shaking per Chart.js/Leaflet
  - Analisi bundle con `rollup-plugin-visualizer`
- **PWA Enhancement**:
  - Aggiornare `vite-plugin-pwa` config
  - Cache API offline con strategia stale-while-revalidate

### 4.2 Testing
- **Task**:
  - Estendere test unitari Vitest (copertura >80%)
  - Aggiungere test E2E con Playwright
  - Test componenti critici (Login, CoachPanel, Calendar)

---

## ROADMAP PRIORITIZZATA

| Sprint | Durata | Obiettivi | Deliverable |
|--------|--------|-----------|-------------|
| Sprint 1 | 1 settimana | Vue Router + struttura route | **COMPLETATO** - Router configurato, App.vue aggiornato |
| Sprint 2 | 1 settimana | TypeScript base | In corso - tsconfig.json creato, tipi definiti |
| Sprint 3 | 2 settimane | Pinia store + libreria UI | State management coerente |
| Sprint 4 | 2 settimane | Accessibilità + responsive | WCAG compliant |
| Sprint 5 | 2 settimane | Feature API mancanti | Backend integrato |
| Sprint 6 | 1 settimana | Testing + performance | Test coverage >80% |

---

## MILESTONES

1. **M1**: Routing funzionante con deep linking (fine Sprint 1)
2. **M2**: Codice TypeScript compilato senza errori (fine Sprint 2)
3. **M3**: Store Pinia con persistenza funzionante (fine Sprint 3)
4. **M4**: UI libreria integrata, design system stabile (fine Sprint 4)
5. **M5**: Tutte le API integrate, feature complete (fine Sprint 5)
6. **M6**: Test automatizzati, bundle ottimizzato (fine Sprint 6)

---

## RISORSE CONSIGLIATE

- **Vue Router**: `npm install vue-router`
- **TypeScript**: Vue 3 + Vite TS docs
- **Naive UI**: `npm install naive-ui` (leggero, dark theme)
- **VitePWA**: Aggiornare a v0.21+ per Vue 3
- **Icons**: `npm install @iconify/vue` per icone moderne

---

## METRICHE DI SUCCESSO

- [ ] Lighthouse Performance >90
- [ ] Lighthouse Accessibility >90
- [ ] Bundle size <300KB gzipped
- [ ] Test coverage >80%
- [ ] Pagina caricata <1.5s 3G
- [ ] WCAG 2.1 AA compliant