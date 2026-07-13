# Frontend — Riferimento

SPA Vue 3 + Vite 5 + TypeScript + Pinia + Vue Router 4, con PWA e app Android via Capacitor. Sorgente: `frontend/`. Derivato dal codice reale.

Per la guida narrativa completa vedi anche [../frontend.md](../frontend.md).

---

## 1. Stack

| Aspetto | Tecnologia |
|---|---|
| Framework | Vue 3 (Composition API) |
| Build | Vite 5 |
| Linguaggio | TypeScript |
| State | Pinia |
| Routing | Vue Router 4 (con auth guard) |
| Grafici | Chart.js (via `useChart`) |
| Mappe | Leaflet (+ heatmap) |
| i18n | composable `useI18n` + `locales/` |
| Mobile | Capacitor (Android) + `vite-plugin-pwa` (PWA) |
| Test | Vitest (unit) + Playwright (E2E) |

---

## 2. Struttura `frontend/src/`

```
src/
├── main.ts              # bootstrap app
├── App.vue              # root component
├── router/index.ts      # 23 route + guard
├── stores/              # Pinia (auth, tracking, ui)
├── components/          # componenti/pannelli UI
├── components/calendar/ # CalendarGrid, FitnessChart
├── views/              # pagine di primo livello
├── composables/         # logica riusabile (use*)
├── services/            # authSync, oauth
├── utils/               # api client, storage, validazione, mappe
├── plugins/             # bridge nativo Capacitor
├── data/                # dati statici
├── locales/             # traduzioni i18n
├── styles/              # CSS
├── types/               # tipi TS condivisi
└── test/                # setup test
```

---

## 3. Routing (`router/index.ts`)

23 route:

| Path | Scopo |
|---|---|
| `/` | Home/dashboard |
| `/rides` | Elenco e dettaglio ride |
| `/import` | Import file/provider |
| `/athlete` | Profilo atleta |
| `/coach` | AI Coach |
| `/knowledge` | Knowledge base |
| `/bm2` | Pannello simulazione BM2 |
| `/calendar` | Calendario allenamenti |
| `/granfondo` | Pianificatore granfondo |
| `/map` | Mappa ride |
| `/pois` | Point of Interest |
| `/aethermap` | AetherMap (R&D) |
| `/comparison` | Confronto ride |
| `/heatmap` | Heatmap percorsi |
| `/badges` | Badge/riconoscimenti |
| `/weather` | Meteo |
| `/admin` | Pannello admin |
| `/track` | Tracking GPS live |
| `/privacy`, `/terms`, `/cookies`, `/about`, `/contact` | Pagine legali/info |

Le route protette usano un guard basato sullo store `auth`.

---

## 4. State management (Pinia, `stores/`)

| Store | Responsabilità |
|---|---|
| `auth.ts` | Sessione utente, token JWT, login/logout, guard |
| `trackingStore.ts` | Stato reattivo del tracking GPS live |
| `ui.ts` | Stato UI (tab, tema, preferenze, AetherMap) |

---

## 5. Composables (`composables/`)

| Composable | Scopo |
|---|---|
| `useRides.ts` | Caricamento/gestione ride |
| `useChart.ts` | Wrapper Chart.js |
| `useToast.ts` | Notifiche toast |
| `usePWA.ts` | Install prompt e stato PWA |
| `useI18n.ts` | Internazionalizzazione |
| `useBm2.ts` | Chiamate all'engine BM2 |
| `useAetherMap.ts` | Integrazione AetherMap |
| `useBatteryEfficientGps.ts` | Acquisizione GPS a basso consumo |

---

## 6. Componenti principali (`components/`)

Pannelli funzionali:
- **Ride:** `RidesPanel`, `RideDetail`, `RideComparison`, `RideMetricsPanel`, `RideMapPanel`, `SpeedMap`, `LiveMap`
- **Import/Athlete:** `ImportPanel`, `AthletePanel`
- **Coaching/Knowledge:** `CoachPanel`, `KnowledgePanel`
- **Simulazione:** `Bm2Panel`
- **Pianificazione:** `CalendarPanel`, `GranfondoPlanner`, `calendar/CalendarGrid`, `calendar/FitnessChart`
- **Analytics:** `DashboardPanel`, `ChartsPanel`, `StatsSummary`, `HeatmapPanel`, `BadgesPanel`, `WeatherPanel`
- **Mappe/POI:** `AetherMapViewer`
- **Admin:** `AdminPanel`
- **UI/sistema:** `HeaderTabs`, `ControlsBar`, `LoginForm`, `LanguageSwitcher`, `ToastContainer`, `ConfirmModal`, `ErrorBoundary`, `ErrorState`, `PWAInstallPrompt`

---

## 7. API client & utilities (`utils/`)

| File | Scopo |
|---|---|
| `api.ts` | Client HTTP: `apiGet`, `apiPost`, `apiPut`, `apiDelete`, `apiUpload` (gestione JWT + errori) |
| `auth-storage.ts` | Persistenza token |
| `validation.ts` | Validazione input |
| `routeMap.ts`, `rideMapEnrichment.ts` | Elaborazione/arricchimento tracce mappa |

**Services** (`services/`): `oauth.ts` (flussi OAuth), `authSync.ts` (sincronizzazione sessione).

---

## 8. Mobile & PWA

- **Android (Capacitor):** `plugins/bikeTracking.ts` è il bridge JS verso il plugin nativo `BikeTrackingPlugin.kt` / `BikeTrackingService.kt` (foreground service GPS persistente). UI in `views/RideTracking.vue` + `trackingStore.ts`.
- **Funzionalità tracking:** scrittura GPX incrementale in background, auto-pausa < 3 km/h, sensori BLE (HR/Cadenza/Potenza), GPS a basso consumo (`useBatteryEfficientGps`).
- **PWA:** `vite-plugin-pwa`, install prompt (`PWAInstallPrompt.vue` + `usePWA`), supporto safe-area mobile.

Dettagli: [../PHONE_TRACKING.md](../PHONE_TRACKING.md).

---

## 9. Comandi

```bash
cd frontend
npm install
npm run dev          # dev server (http://localhost:5173)
npm run build        # build di produzione
npm run typecheck    # vue-tsc --noEmit
npm run lint         # eslint --fix
npm run test         # Vitest
npm run e2e          # Playwright
```

### Nota build su Windows

`vite build` può fallire con `EPERM` per lock di Windows Defender: mitigato da wrapper con retry (`frontend/scripts/build.mjs`) ed eventuale esclusione della cartella da Defender. Vedi `AGENTS.md`.

---

## Riferimenti

- Architettura: [architecture.md](./architecture.md)
- API consumate: [api-reference.md](./api-reference.md)
- Configurazione: [configuration.md](./configuration.md)
