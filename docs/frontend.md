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
