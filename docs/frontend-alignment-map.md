# Frontend Alignment Map — PC (source of truth) → Mobile (Android)

Questa mappa è la fonte di verità per l'agente di allineamento frontend.
Il **frontend PC** (`frontend/`, Vue 3 + Tauri 2) è il *source of truth*: ogni
nuova feature/fix arriva prima lì. L'agente propaga le modifiche rilevanti al
**frontend mobile** (`android/`, Kotlin nativo) seguendo questa mappa 1:1.

Convenzioni di stato:
- `aligned`     — presente e coerente su entrambi i frontend
- `pc-only`     — esiste solo su PC, da valutare se portare su mobile
- `drift`       — esiste su entrambi ma divergente (richiede allineamento)
- `mobile-only` — presente solo su mobile (raro; es. GPS tracking nativo)

## Feature map

| PC route / componente            | PC file                                              | Mobile equivalente (Android)                         | Stato    | Note                                                              |
|----------------------------------|------------------------------------------------------|------------------------------------------------------|---------|-------------------------------------------------------------------|
| Home / Welcome                   | views/WelcomePage.vue, router `/welcome`             | MainActivity.kt                                      | aligned  | Schermata di ingresso/navigazione                                |
| Auth: login                      | stores/auth, services/auth*                          | ui/auth/LoginActivity.kt                             | aligned  | `POST auth/login`                                                 |
| Auth: register                   | stores/auth                                          | ui/auth/RegisterActivity.kt                          | aligned  | `POST auth/register`                                              |
| Rides (lista + dettaglio)        | views/RidesView.vue                                   | ui/rides/RideListActivity.kt, RideDetailActivity.kt  | aligned  | `GET /rides`, `GET /rides/{id}`                                   |
| Ride import (GPX/FIT)            | components/ImportPanel.vue                            | ui/imports/ImportActivity.kt                       | aligned  | Upload GPX/FIT via API                                           |
| Athlete profile                  | components/AthletePanel.vue                          | ui/athlete/AthleteProfileActivity.kt                 | aligned  | `GET/PUT /athletes/{id}`                                          |
| AI Coach                         | components/CoachPanel.vue                            | ui/coach/CoachActivity.kt                            | aligned  | `GET coach/workout`, `GET coach/full`                            |
| Calendar                         | components/CalendarPanel.vue                         | ui/calendar/CalendarActivity.kt                      | aligned  | `GET/POST /calendar/events`                                       |
| Route maps                       | components/RideMapPanel.vue                          | ui/maps/MapsActivity.kt                            | aligned  | Google Map con tracce GPS                                        |
| Tracking GPS (tempo reale)       | views/RideTracking.vue                               | ui/tracking/TrackingActivity.kt + BikeTrackingService| mobile-only | Su mobile è foreground service nativo; sul PC è tracking leggero |
| Settings / backend mode           | views/SettingsView.vue                               | ui/settings/SettingsActivity.kt                      | aligned  | Backend URL fissato a build-time; solo fallover Render configurabile                                  |
| Training load (ATL/CTL/TSB)      | components/ZonesPanel? / stats                       | StatsActivity.kt / ui/zones/ZonesActivity.kt       | aligned  | Zone potenza e FC da /analytics/zones                            |
| Knowledge Base                   | components/KnowledgePanel.vue                        | ui/knowledge/KnowledgeActivity.kt                 | aligned  | Ricerca knowledge base                                           |
| BikeMaster 2.0 (sim)             | components/Bm2Panel.vue                              | —                                                    | pc-only  | Simulatore, prob. non per mobile                                  |
| Granfondo Planner                | components/GranfondoPlanner.vue                      | —                                                    | pc-only  | Endpoint backend mancanti                                        |
| Ride comparison                  | components/RideComparison.vue                        | ui/comparison/ComparisonActivity.kt               | aligned  | Confronto periodi via /analytics/comparison                       |
| Heatmap                          | components/HeatmapPanel.vue                          | ui/heatmap/HeatmapActivity.kt                      | aligned  | Heatmap punti GPS per atleta                                      |
| Badges                           | components/BadgesPanel.vue                           | ui/badges/BadgesActivity.kt                       | aligned  | Sistema badge per categoria                                      |
| Weather                          | components/WeatherPanel.vue                          | ui/weather/WeatherActivity.kt                     | aligned  | Meteo per coordinate                                             |
| Zones di allenamento             | components/ZonesPanel.vue                            | ui/zones/ZonesActivity.kt                          | aligned  | Distribuzione tempo per zona                                     |
| Admin                            | components/AdminPanel.vue, AdminUserManagement.vue   | —                                                    | pc-only  | Solo desktop                                                     |
| Client area                      | views/ClientDashboard.vue                            | —                                                    | pc-only  | Solo desktop                                                     |
| POI / Itinerari                  | views/PoiMapView.vue                                 | ui/itineraries/ItinerariesActivity.kt             | aligned  | Lista itinerari                                                  |
| Performance                      | components/PerformancePanel.vue                      | ui/performance/PerformanceActivity.kt             | aligned  | Metriche FTP/NP/IF/TSS                                           |
| AetherMap                        | views/AetherMapView.vue                              | —                                                    | pc-only  | R&D, non per mobile                                              |
| Legal (privacy/terms/cookies)    | views/PrivacyPolicy.vue, TermsOfService.vue, CookiePolicy.vue | —                                           | pc-only  | Solo web/desktop                                                 |
| About / Contact                  | views/AboutUs.vue, ContactUs.vue                     | —                                                    | pc-only  | Solo web/desktop                                                 |

## Regole di allineamento (usate dallo script e dall'agente)

1. Il PC è sempre la sorgente: ogni modifica a una route/feature `aligned` o `drift`
   del PC deve essere propagata al corrispondente mobile se lo stato è `aligned` o `drift`.
2. Le feature `pc-only` NON sono propagate automaticamente; l'agente le segnala come
   "candidate al porting" e chiede conferma prima di creare codice mobile.
3. Le feature `mobile-only` (es. GPS tracking nativo) non hanno controparte PC e non
   devono essere rimosse dal mobile.
4. API contract: se il backend cambia un endpoint usato da una voce `aligned`/`drift`,
   aggiornare sia `BikeMasterApi.kt` (mobile) sia i servizi PC.
5. Versioning: lo script confronta `frontend/src` (tree + hash) con l'ultimo snapshot
   in `docs/frontend-alignment-snapshot.json` per rilevare il drift tra versioni.
