# Frontend

## Architecture

- **Vue 3** Composition API with `<script setup>`
- **TypeScript** strict mode
- **Pinia** for state management
- **Vue Router 4** with auth guards
- **Vite 5** build tool
- **Tauri 2** desktop wrapper (primario) — il frontend Vue gira dentro un WebView nativo
- **PWA** via vite-plugin-pwa + custom `sw.js` (secondario, per web-only users)

Il frontend è progettato per girare in due contesti:
1. **Tauri 2 desktop app** (primario): Vue in WebView, comunica con backend embedded via `localhost`
2. **Browser web** (secondario): PWA installabile, backend cloud opzionale

## Key Stores

- `auth.ts` — JWT, user, token validation, login/logout
- `ui.ts` — theme, language, oauthLoading
- `trackingStore.ts` — live GPS tracking state

## Components

Key components in `frontend/src/components/`:

- `LoginForm.vue`, `HeaderTabs.vue`, `RidesPanel.vue`, `ImportPanel.vue`
- `AthletePanel.vue`, `CoachPanel.vue`, `KnowledgePanel.vue`
- `DashboardPanel.vue`, `ChartsPanel.vue`, `StatsSummary.vue`
- `RideMapPanel.vue`, `SpeedMap.vue`, `HeatmapPanel.vue`
- `CalendarPanel.vue`, `GranfondoPlanner.vue`, `BadgesPanel.vue`
- `WeatherPanel.vue`, `AdminPanel.vue`, `LiveMap.vue`
- `ErrorBoundary.vue`, `ConfirmModal.vue`, `ToastContainer.vue`
- `PWAInstallPrompt.vue`, `LanguageSwitcher.vue`, `ControlsBar.vue`
- `RideDetail.vue`, `RideComparison.vue`, `RideMetricsPanel.vue`
- `Bm2Panel.vue`

## Composables

- `useRides.ts` — ride list, create, delete
- `useToast.ts` — toast notifications
- `usePWA.ts` — install prompt, offline detection
- `useI18n.ts` — internationalization (IT + EN)
- `useChart.ts` — Chart.js wrappers

## Client-side Data Storage

BikeMaster segue un approccio *local-first*: il database primario è SQLite
locale sul device dell'utente. Token in `localStorage`, cache
shell/API/immagini e coda upload ride offline via Service Worker
(`BackgroundSyncPlugin`). Vedi [local-data-storage.md](./local-data-storage.md).

Su desktop (Tauri), il backend embedded gestisce direttamente SQLite senza
dipendere da servizi cloud.

## Native Mobile

- **Android**: Kotlin foreground service (`BikeTrackingService.kt`) + Capacitor plugin
- **iOS**: Swift plugin (`BikeTrackingPlugin.swift`) + Capacitor config

## Voice Commands

BikeMaster includes an Italian voice command system powered by the Web Speech API. The registry in `frontend/src/services/voiceCommands.ts` exposes **35+ commands** organized by domain:

- **Navigation**: `Apri vista` (open dashboard, rides, calendar, etc.)
- **Athlete profile**: `Aggiorna peso`, `Aggiorna altezza`, `Aggiorna FTP`, `Aggiorna FC max`
- **Calendar**: `Aggiungi evento calendario`
- **Rides**: `Aggiungi uscita`, `Analizza uscita`, `Esporta uscite`, `Resetta filtri uscite`
- **Nutrition**: `Registra pasto` — auto-estimates kcal from description keywords and auto-creates a calendar event, then triggers `metabolism/recalculate` returning intake/balance summary.
- **Tracking**: `Avvia tracciamento`, `Ferma tracciamento`, `Pausa tracciamento`, `Riprendi tracciamento`
- **UI**: `Cambia tema`, `Mostra/nascondi sidebar`, `Mostra calorie`, `Mostra meteo`
- **Integrations**: `Connetti Strava`, `Sincronizza Strava`, `Connetti Google Fit`, `Carica file GPX`
- **BM2**: `Simula gara`, `Valida piano`, `Genera piano granfondo`
- **Knowledge**: `Cerca conoscenza`
- **Sync**: `Sync locale`, `Sync cloud`, `Aggiorna sync`, `Esporta dati`, `Importa dati`

Each command supports multiple trigger phrases and structured parameter extraction (numbers, dates, booleans).

## New Components

- `VoiceAssistant.vue` — floating FAB with audio stop behavior fixed
- `TrackingToolsPanel.vue` — map style selector, POI toggle, center-map, save-as-itinerary
- `LiveMap.vue` — enhanced live tracking map layer
- `RideTracking.vue` — expanded ride tracking view

## Build (Frontend)

```bash
cd frontend
npm install
npm run dev          # vite dev server
npm run build        # vite build (with retry wrapper on Windows)
npm run typecheck    # vue-tsc --noEmit --incremental
npm run lint         # eslint --fix
npm run test         # vitest unit
npm run e2e          # playwright test
npm run tauri build  # build desktop app (.exe/.dmg/.AppImage)
npm run tauri dev    # dev mode con backend embedded
```

Per dettagli sulla configurazione Tauri, vedere `src-tauri/` e
[deployment-plan.md](./deployment-plan.md).
