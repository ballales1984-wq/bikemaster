# BikeMaster Android

App mobile Android per il tracciamento e analisi delle attività ciclistiche.

## Configurazione

1. Apri Android Studio
2. Apri la cartella `android` come progetto esistente
3. Configura l'URL backend in Settings dell'app o in `PreferencesManager.kt`
4. Aggiungi la tua Google Maps API Key in `AndroidManifest.xml`

## Struttura Progetto

```
app/src/main/java/com/bikemaster/
├── MainActivity.kt                    # Schermata principale con navigazione
├── models/
│   └── Ride.kt                        # Data class per Ride, Athlete, CalendarEvent
├── network/
│   ├── ApiClient.kt                   # Retrofit client singleton
│   └── BikeMasterApi.kt               # Interfaccia API
├── plugins/
│   └── BikeTrackingPlugin.kt            # Capacitor plugin per GPS tracking
├── tracking/
│   └── BikeTrackingService.kt           # Foreground service GPS persistente
├── ui/
│   ├── auth/
│   │   ├── LoginActivity.kt           # Login
│   │   └── RegisterActivity.kt        # Registrazione
│   ├── settings/
│   │   └── SettingsActivity.kt          # Configurazione backend URL
│   ├── tracking/
│   │   └── TrackingActivity.kt          # GPS tracking in tempo reale
│   ├── stats/
│   │   └── StatsActivity.kt              # Statistiche con grafici
│   ├── coach/
│   │   └── CoachActivity.kt           # AI Coach
│   ├── calendar/
│   │   ├── CalendarActivity.kt
│   │   └── CalendarAdapter.kt
│   ├── athlete/
│   │   └── AthleteProfileActivity.kt  # Profilo atleta
│   └── rides/
│       ├── RideListActivity.kt        # Lista attività
│       ├── RideAdapter.kt
│       ├── RideDetailActivity.kt      # Dettaglio attività con mappa
│       └── AddRideDialog.kt
└── utils/
    ├── LocationTracker.kt             # GPS tracking utility
    └── PreferencesManager.kt            # Gestione preferenze
```

## Phone GPS Tracking

### Componenti
- **BikeTrackingService** - Foreground service per tracciamento in background
- **BikeTrackingPlugin** - Bridge Capacitor per metodo JS
- **trackingStore.ts** - Store Pinia (frontend Vue)

### Permessi Richiesti
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
<uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```

### Utilizzo Capacitor
```typescript
import { BikeTracking } from '@/plugins/bikeTracking'

// Avvia tracking
await BikeTracking.startTracking()

// Pausa
await BikeTracking.pauseTracking()

// Stop e ottieni GPX
const result = await BikeTracking.stopTracking()
console.log(result.gpxPath)
```

---

## Dipendenze Principali

- Retrofit + Gson (API calls)
- Google Play Services Maps
- MPAndroidChart (grafici)
- Kotlin Coroutines
- Material Design Components
- androidx.preference (settings)

## Funzionalità Implementate

1. **Settings** - Configurazione URL backend personalizzabile
2. **Login/Register** - Autenticazione utente
3. **GPS Tracking** - Tracciamento attività in tempo reale con mappa
4. **Statistiche** - Grafici distanza e velocità (MPAndroidChart)
5. **Lista Rides** - Visualizzazione attività
6. **AI Coach** - Consigli allenamento personalizzati
7. **Calendario** - Eventi allenamenti

## API Supportate

- `/auth/login`, `/auth/register` - Autenticazione
- `/rides` - Lista e dettaglio attività
- `/athletes` - Gestione profilo atleta  
- `/coach/*` - AI Coach recommendations
- `/calendar/events` - Calendario allenamenti
- `/training/load` - Training load metrics (ATL/CTL/TSB)
- `/import/gpx`, `/import/fit` - Import file GPS

## Backend su Render

L'app è configurata per `https://bikemaster-api.onrender.com/api/v1/`. Modifica l'URL in Settings se necessario.