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
| Ride import (GPX/FIT)            | components/ImportPanel.vue                            | (API pronta: importGpx/importFit)                    | drift    | Su mobile l'import file non ha ancora UI; API presente            |
| Athlete profile                  | components/AthletePanel.vue                          | ui/athlete/AthleteProfileActivity.kt                 | aligned  | `GET/PUT /athletes/{id}`                                          |
| AI Coach                         | components/CoachPanel.vue                            | ui/coach/CoachActivity.kt                            | aligned  | `GET coach/workout`, `GET coach/full`                            |
| Calendar                         | components/CalendarPanel.vue                         | ui/calendar/CalendarActivity.kt                      | aligned  | `GET/POST /calendar/events`                                       |
| Route maps                       | components/RideMapPanel.vue                          | ui/rides/RideDetailActivity.kt (mappa)               | drift    | Mobile mostra mappa solo nel dettaglio, non vista lista mappe     |
| Tracking GPS (tempo reale)       | views/RideTracking.vue                               | ui/tracking/TrackingActivity.kt + BikeTrackingService| mobile-only | Su mobile è foreground service nativo; sul PC è tracking leggero |
| Settings / backend mode           | views/SettingsView.vue                               | ui/settings/SettingsActivity.kt                      | aligned  | Backend URL fissato a build-time; solo fallover Render configurabile                                  |
| Training load (ATL/CTL/TSB)      | components/ZonesPanel? / stats                       | StatsActivity.kt                                     | drift    | `GET /training/load` usato su mobile; PC lo mostra in più punti   |
| Knowledge Base                   | components/KnowledgePanel.vue                        | —                                                    | pc-only  | Da valutare porting su mobile                                     |
| BikeMaster 2.0 (sim)             | components/Bm2Panel.vue                              | —                                                    | pc-only  | Simulatore, prob. non per mobile                                  |
| Granfondo Planner                | components/GranfondoPlanner.vue                      | —                                                    | pc-only  | Valutare                                                         |
| Ride comparison                  | components/RideComparison.vue                        | —                                                    | pc-only  | Valutare                                                         |
| Heatmap                          | components/HeatmapPanel.vue                          | —                                                    | pc-only  | Valutare                                                         |
| Badges                           | components/BadgesPanel.vue                           | —                                                    | pc-only  | Valutare                                                         |
| Weather                          | components/WeatherPanel.vue                          | —                                                    | pc-only  | Valutare                                                         |
| Zones di allenamento             | components/ZonesPanel.vue                            | —                                                    | pc-only  | Valutare                                                         |
| Admin                            | components/AdminPanel.vue, AdminUserManagement.vue   | —                                                    | pc-only  | Solo desktop                                                     |
| Client area                      | views/ClientDashboard.vue                            | —                                                    | pc-only  | Solo desktop                                                     |
| POI / Itinerari                  | views/PoiMapView.vue                                 | —                                                    | pc-only  | Valutare                                                         |
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
