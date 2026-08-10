# Piano — Monitoraggio H24 Stile Google Fit

## Obiettivo

Trasformare la funzione di tracking da "solo su richiesta esplicita" a **monitoraggio continuo passivo** che si avvia automaticamente quando l'utente entra nella sezione tracking. La logica di acquisizione GPS/calcolo metriche rimane invariata; cambia solo la **presentazione** dei dati: timeline giornaliera, activity rings, riconoscimento automatico delle uscite.

---

## 1. ANALISI ARCHITETTURA ATTUALE

### Componenti esistenti riutilizzabili

| Componente | File | Stato |
|------------|------|-------|
| **trackingStore (Pinia)** | `frontend/src/stores/trackingStore.ts` | ✅ Funzionante — stato centrale GPS |
| **RideTracking.vue** | `frontend/src/views/RideTracking.vue` | ✅ Funzionante — vista tracking attiva |
| **useBatteryEfficientGps** | `frontend/src/composables/useBatteryEfficientGps.ts` | ✅ Funzionante — sampling adattivo |
| **useGpsOutlierFilter** | `frontend/src/composables/useGpsOutlierFilter.ts` | ✅ Funzionante — filtri outlier |
| **useGpsDirectionFilter** | `frontend/src/composables/useGpsDirectionFilter.ts` | ✅ Funzionante — filtri direzione |
| **LiveMap.vue** | `frontend/src/components/LiveMap.vue` | ✅ Funzionante — mappa Leaflet |
| **RideMetricsPanel.vue** | `frontend/src/components/RideMetricsPanel.vue` | ✅ Funzionante — pannello metriche |
| **Backend POST /api/v1/rides** | `bike_analyzer/backend/api/routes.py:2037` | ✅ Funzionante — salvataggio uscita |
| **Google Fit integration** | `bike_analyzer/backend/ingestion/google_fit.py` | ✅ Esistente — import dati esterni |
| **Android Foreground Service** | `android/.../BikeTrackingService.kt` | ✅ Funzionante — tracking background nativo |
| **iOS CLLocationManager** | `frontend/ios/.../BikeTrackingPlugin.swift` | ✅ Funzionante — background iOS |

### Limitazioni attuali per H24

1. **Tracking web solo in foreground**: il GPS polling si interrompe se l'utente cambia tab o chiude il browser
2. **Start manuale obbligatorio**: l'utente deve premere "Start Tracking"
3. **SessionStorage effimero**: i dati persistono solo per il refresh pagina, non per chiusura tab
4. **Nessuna segmentazione automatica**: ogni sessione è un "ride" dichiarato manualmente
5. **Nessuna vista timeline giornaliera**: i dati sono presentati come lista di uscite, non come flusso continuo

### Cosa va aggiunto

| Nuovo componente | Priorità | Descrizione |
|------------------|----------|-------------|
| **ContinuousTracking composable** | P0 | Wrapper che avvia GPS automaticamente al mount |
| **ActivitySegmentation engine** | P0 | Rileva inizio/fine uscita da pattern GPS (velocità, durata) |
| **DailyTimeline component** | P1 | Timeline verticale tipo Google Fit (h24 strip) |
| **ActivityRings component** | P1 | Cerchi concentrici stile Apple Watch (passi, distanza, tempo attivo) |
| **PassiveTrackingStore** | P1 | Store esteso con soglia di rilevamento e stati "in movimento"/"fermo" |
| **BackgroundSyncWorker** | P2 | Service Worker con Background Sync per salvataggio periodico |
| **IndexedDB persistence** | P2 | Persistenza dati tracking oltre sessionStorage |
| **Auto-stop logic** | P2 | Ferma automaticamente sessioni "fantasma" (GPS attivo senza movimento) |

---

## 2. ARCHITETTURA PROPOSTA

```
┌─────────────────────────────────────────────────────────┐
│                   ContinuousTracking                     │
│                   (Composable + Store)                   │
│                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │ GPS Engine│    │ Segmentation │    │ Persistence   │ │
│  │ (esistente│───▶│ Engine       │───▶│ Layer         │ │
│  │ + auto)   │    │ (nuovo)      │    │ (IndexedDB +  │ │
│  └──────────┘    └──────────────┘    │  sessionStorage)│
│       │                  │           └───────────────┘ │
│       ▼                  ▼                  │           │
│  ┌──────────────────────────────────────────┘           │
│  │           PassiveTrackingStore                        │
│  │  isTracking | isMoving | currentSession | segments[]  │
│  └──────────────────────────────────────────────────────┘ │
│                         │                                │
│         ┌───────────────┼───────────────┐                │
│         ▼               ▼               ▼                │
│  ┌──────────┐   ┌──────────────┐  ┌──────────────┐      │
│  │LiveMap    │   │DailyTimeline │  │ActivityRings │      │
│  │(esistente)│   │(nuovo)       │  │(nuovo)       │      │
│  └──────────┘   └──────────────┘  └──────────────┘      │
│                                                         │
│  RideTracking.vue (modificato: auto-start + nuovi view) │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Backend API     │
              │  POST /rides     │
              │  (invariato)     │
              └──────────────────┘
```

---

## 3. IMPLEMENTAZIONE DETTAGLIATA

### 3.1 ContinuousTracking Composable (P0)

**File**: `frontend/src/composables/useContinuousTracking.ts`

**Responsabilità**:
- Avvia automaticamente il GPS quando il composable è montato
- Gestisce l'auto-pause quando l'utente esce dalla pagina (tab background)
- Gestisce l'auto-resume quando l'utente torna
- Coordina con il tracking store esistente

```typescript
// Logica chiave:
// 1. onMounted → startTracking() automatico (dopo check permessi)
// 2. visibilitychange → pause se hidden, resume se visible
// 3. pagehide/beforeunload → persistenza forzata in IndexedDB
// 4. Integrazione con useBatteryEfficientGps esistente
```

### 3.2 ActivitySegmentation Engine (P0)

**File**: `frontend/src/composables/useActivitySegmentation.ts`

**Responsabilità**:
- Rileva automaticamente quando inizia un'attività (velocità > 3 km/h per > 30s)
- Rileva quando finisce (velocità < 1 km/h per > 120s)
- Crea segmenti di attività nel tracking store
- Evita segmenti "fantasma" (pochi punti, distanza minima)

```typescript
interface ActivitySegment {
  id: string;
  startTime: number;
  endTime: number | null;
  points: GpsPoint[];
  distance: number;
  avgSpeed: number;
  type: 'moving' | 'stationary' | 'auto_paused';
}
```

**Regole di segmentazione**:
| Stato | Condizione |
|-------|-----------|
| `auto_paused` | Velocità < 0.5 m/s per > 120s |
| `moving` | Velocità > 3 km/h per > 30s |
| `stationary` | Velocità 0.5–3 km/h |
| Transizione moving→paused | Pausa automatica dopo 120s di fermo |

### 3.3 Tracking Store Esteso (P1)

**File**: `frontend/src/stores/trackingStore.ts` (modifica)

**Aggiunte**:

```typescript
// Nuovi campi reattivi
const segments = ref<ActivitySegment[]>([]);
const currentSegmentId = ref<string | null>(null);
const autoTracking = ref(true);      // default: tracking automatico
const activityRings = ref({           // activity rings stile Google Fit
  move: { current: 0, goal: 500 },   // minuti attivi
  exercise: { current: 0, goal: 30 },// minuti esercizio intenso
  stand: { current: 0, goal: 12 }    // sessioni "in piedi"/fermo
});
const dailyTimeline = ref<DailyEntry[]>([]);

// Nuove azioni
function startSegment(): string;      // crea nuovo segmento
function closeSegment(id: string);    // chiude segmento con statistiche
function updateActivityRings();       // ricalcola rings da segmenti
function buildDailyTimeline();        // costruisce timeline da tutti i segmenti
function getTodaySegments();          // filtra segmenti di oggi
function persistToIndexedDB();        // salvataggio persistente oltre sessionStorage
function restoreFromIndexedDB();      // recupero da IndexedDB
```

### 3.4 DailyTimeline Component (P1)

**File**: `frontend/src/components/DailyTimeline.vue`

**Responsabilità**:
- Visualizza timeline verticale H24 tipo Google Fit
- Mostra segmenti di attività colorati per tipo
- Permette di cliccare su un segmento per vedere dettagli
- Badge per ogni segmento (distanza, durata, velocità media)

```
Timeline H24:
00:00 ──────── ●  ████████ 08:30-09:15 (45min, 12km) [ride]
10:00 ──────── ●  ██ 10:00-10:15 (15min, 1.2km) [walk]
12:00 ──────── ●  ██████████████ 12:00-13:30 (90min) [stationary]
14:00 ──────── ●  ██████ 14:00-14:30 (30min, 8km) [ride]
```

### 3.5 ActivityRings Component (P1)

**File**: `frontend/src/components/ActivityRings.vue`

**Responsabilità**:
- Tre cerchi concentrici SVG stile Apple Watch
- Anelli: Move (minuti attivi), Exercise (esercizio intenso), Stand (sessioni ferme)
- Animazione progressiva durante il giorno
- Click per vedere dettaglio

### 3.6 Modifiche a RideTracking.vue (P0)

**Modifiche necessarie**:

1. **Auto-start**: al mount della vista, avvia tracking automaticamente
   ```typescript
   onMounted(async () => {
     const restored = tracking.restoreState();
     if (!restored) {
       // Auto-start tracking se l'utente ha dato permesso in precedenza
       if (tracking.autoTracking && await hasSavedPermission()) {
         await startTracking();
       }
     }
   });
   ```

2. **Vista ibrida**: mostra sia la mappa live (quando tracking attivo) sia la timeline giornaliera
   ```vue
   <div v-if="tracking.isTracking" class="active-tracking">
     <LiveMap />
     <RideMetricsPanel />
     <ControlsBar />
   </div>
   <div v-else class="daily-summary">
     <ActivityRings :segments="tracking.getTodaySegments()" />
     <DailyTimeline :segments="tracking.getTodaySegments()" />
     <button @click="startTracking">Inizia uscita manuale</button>
   </div>
   ```

3. **Stato "in background"**: se l'utente esce dal tab, mostra indicatori minimali

### 3.7 Backend — Nessuna modifica necessaria (P0)

Il backend esistente già supporta:
- Salvataggio uscite con GPS points (`POST /api/v1/rides`)
- Calcolo automatico statistiche (`process_route()`)
- Stima calorie da HR/speed
- Classificazione attività giornaliera (`/activity/summary`, `/activity/classify`)

**L'integrazione avviene al salvataggio del segmento**: quando un segmento viene chiuso, viene inviato al backend come ride. Il flusso è identico a quello attuale.

### 3.8 Android — Estensione Foreground Service (P1)

**File**: `android/.../BikeTrackingService.kt`

**Aggiunte**:
- Activity Recognition API per auto-detect inizio/fine attività (già presente, da estendere)
- Auto-upload segmenti anche senza interruzione manuale
- Notifica "Uscita rilevata automaticamente" quando viene creato un segmento

### 3.9 iOS — Estensione Background (P1)

**File**: `frontend/ios/.../BikeTrackingPlugin.swift`

**Aggiunte**:
- `allowsBackgroundLocationUpdates = true` (già presente)
- Delegate method per rilevare transizioni significative (start/stop attività)

---

## 4. FLUSSO UTENTE (User Flow)

### Scenario A: Apertura automatica

```
1. Utente apre BikeMaster → naviga a /track
2. ContinuousTracking composable si monta
3. Controlla permessi GPS salvati
4. Se permessi granted → avvia GPS automaticamente
5. Store mostra vista "in movimento" (mappa + metriche)
6. Engine segmentazione rileva attività → crea segmento
7. Se utente si ferma → auto-pause dopo 120s
8. Se utente riprende → auto-resume
9. Utente chiude vista → tracking continua in background (nativo) / si sospende (web)
10. Utente riapre /track → riprende da dove era
```

### Scenario B: Rilevamento automatico uscita

```
1. Utente esce di casa con il telefono → GPS rileva movimento
2. Dopo 30s di velocità > 3 km/h → creato segmento automatico
3. Tracking prosegue in background (Android foreground service)
4. Utente torna a casa → si ferma
5. Dopo 120s di velocità < 0.5 m/s → segmento chiuso
6. Segmento salvato automaticamente come "Uscita del [data]"
7. ActivityRings aggiornati
8. Notifica: "Uscita registrata: 15.2 km in 48min"
```

### Scenario C: Tracking manuale (fallback)

```
1. Utente vuole uscita strutturata → tocca "Inizia uscita"
2. Tracking avviato con flag isOfficial=true
3. Utente controlla mappa live, metriche, voice coach
4. Al stop → upload automatico backend
5. Ride appare in lista uscite
```

---

## 5. DATI E MODELLI

### ActivitySegment (frontend)

```typescript
interface ActivitySegment {
  id: string;                    // UUID
  startTime: number;             // timestamp ms
  endTime: number | null;        // null se in corso
  type: 'moving' | 'stationary' | 'auto_paused';
  gpsPoints: GpsPoint[];
  distanceM: number;
  avgSpeedKmh: number;
  elevationGainM: number;
  autoDetected: boolean;         // true = rilevato automaticamente
}
```

### ActivityRings (frontend)

```typescript
interface ActivityRing {
  label: string;       // 'move' | 'exercise' | 'stand'
  current: number;     // valore attuale
  goal: number;        // obiettivo
  unit: string;        // 'min' | 'count'
  color: string;       // colore anello
}
```

### DailyEntry (frontend)

```typescript
interface DailyEntry {
  date: string;              // YYYY-MM-DD
  segments: ActivitySegment[];
  totalDistanceKm: number;
  totalActiveMinutes: number;
  totalExerciseMinutes: number;
  totalStandSessions: number;
  ringsCompletion: number;   // 0-100%
}
```

---

## 6. PERSISTENZA DATI

### Gerarchia di persistenza

| Livello | Storage | Scopo | Limiti |
|---------|---------|-------|--------|
| 1 | `sessionStorage` | Draft corrente tracking | Perde al close tab |
| 2 | `IndexedDB` | Tracking multi-sessione + segmenti | Illimitato (locale) |
| 3 | Backend SQLite/Postgres | Uscite confermate | Permanente |

### IndexedDB Schema

```typescript
// Database: bikemaster_tracking
// Store: segments
{
  id: string;           // UUID
  date: string;         // YYYY-MM-DD (per indicizzazione)
  startTime: number;
  endTime: number | null;
  type: string;
  gpsPoints: GpsPoint[];
  distanceM: number;
  avgSpeedKmh: number;
  autoDetected: boolean;
  synced: boolean;      // true se salvato su backend
  createdAt: number;
}
```

---

## 7. MIGRAZIONE E COMPATIBILITÀ

### Breaking changes: NESSUNO

- Il tracking store esistente viene **esteso**, non sostituito
- RideTracking.vue viene **modificato** per aggiungere auto-start + vista daily
- Il backend non richiede modifiche
- I test esistenti continuano a funzionare

### Fase 1: Estensione tracking store (no breaking)
1. Aggiungi campi reattivi al tracking store
2. Aggiungi actions per segmentazione e daily timeline
3. Aggiorna test

### Fase 2: ContinuousTracking composable
1. Crea nuovo composable
2. Integra in RideTracking.vue
3. Test auto-start/auto-pause

### Fase 3: Nuovi componenti UI
1. DailyTimeline.vue
2. ActivityRings.vue
3. Integra in RideTracking.vue come vista alternativa

### Fase 4: Ottimizzazioni
1. IndexedDB persistence
2. Background Sync avanzato
3. Android foreground service enhancement

---

## 8. CONFIGURAZIONE UTENTE

### Impostazioni tracking (Settings)

```typescript
interface TrackingSettings {
  autoStart: boolean;           // Avvia tracking automaticamente
  autoDetectActivities: boolean; // Rileva uscite automaticamente
  autoSaveSegments: boolean;     // Salva automaticamente segmenti
  minActivityDuration: number;   // Minuti minimi per salvare (default: 5)
  minActivityDistance: number;   // Km minimi per salvare (default: 0.5)
  autoPauseAfterSeconds: number; // Secondi di fermo per auto-pause (default: 120)
  gpsAccuracy: 'high' | 'balanced' | 'low';
}
```

---

## 9. PERFORMANCE E BATTERIA

### Strategie già implementate
- ✅ `useBatteryEfficientGps` — sampling adattivo (1s-15s)
- ✅ Outlier filtering — riduce elaborazione
- ✅ SessionStorage draft — salvataggio incrementale

### Nuove ottimizzazioni
- **Geofencing**: sospendi tracking quando utente è a casa/lavoro
- **Batch upload**: accumula punti e invia in batch (ogni 60s)
- **Adaptive sampling per segmentazione**: aumenta frequenza durante transizione moving/stationary

---

## 10. TESTING

### Test esistenti da aggiornare
- `trackingStore.test.ts` — aggiungi test per nuovi campi/actions
- `RideTracking.test.js` — aggiorna per auto-start
- `LiveMap.test.js` — invariato

### Nuovi test
- `useActivitySegmentation.test.ts` — test algoritmi segmentazione
- `DailyTimeline.test.ts` — test rendering timeline
- `ActivityRings.test.ts` — test rendering anelli
- `useContinuousTracking.test.ts` — test auto-start/pause/resume

---

## 11. FILE COINVOLTI (riepilogo)

### Nuovi file da creare
| File | Priorità |
|------|----------|
| `frontend/src/composables/useContinuousTracking.ts` | P0 |
| `frontend/src/composables/useActivitySegmentation.ts` | P0 |
| `frontend/src/composables/useIndexedDB.ts` | P2 |
| `frontend/src/components/DailyTimeline.vue` | P1 |
| `frontend/src/components/ActivityRings.vue` | P1 |
| `frontend/src/stores/trackingStore.test.ts` (esteso) | P1 |

### File da modificare
| File | Modifiche |
|------|-----------|
| `frontend/src/stores/trackingStore.ts` | Aggiungi campi reattivi + actions per segmentazione/daily |
| `frontend/src/views/RideTracking.vue` | Auto-start al mount + vista ibrida (tracking/daily) |
| `frontend/src/types/index.d.ts` | Aggiungi `ActivitySegment`, `ActivityRing`, `DailyEntry` |
| `android/.../BikeTrackingService.kt` | Auto-detect attività + notifiche |
| `frontend/ios/.../BikeTrackingPlugin.swift` | Transizioni significative location |

---

## 12. ORDINE DI IMPLEMENTAZIONE

```
Sprint 1 (P0) — Tracking automatico
├── 1.1 useContinuousTracking composable
├── 1.2 useActivitySegmentation engine
├── 1.3 Tracking store estensioni
└── 1.4 RideTracking.vue modifiche (auto-start)

Sprint 2 (P1) — UI Google Fit
├── 2.1 DailyTimeline component
├── 2.2 ActivityRings component
└── 2.3 Vista ibrida in RideTracking.vue

Sprint 3 (P2) — Persistenza e ottimizzazioni
├── 3.1 IndexedDB persistence layer
├── 3.2 BackgroundSync avanzato
├── 3.3 Geofencing
└── 3.4 Settings per configurazione utente
```

---

## 13. NOTE TECNICHE

### La logica NON cambia
- `process_route()` nel backend rimane invariato
- `POST /api/v1/rides` rimane invariato
- GPS sampling adattivo rimane invariato
- Outlier/direction filtering rimane invariato

### Solo la presentazione cambia
- Vista: da "solo mappa live" a "mappa live + timeline + activity rings"
- Avvio: da "pulsante Start" a "auto-start all'apertura"
- Segmentazione: da "una ride = un tracker" a "molti segmenti = giornata"
- Persistenza: da "sessionStorage" a "sessionStorage + IndexedDB"

### Integrazione con Google Fit esistente
- Il backend ha già `POST /api/v1/import/gpx` e integrazione Google Fit
- I segmenti automatici possono essere importati come "strava-like" (external_source: "bikemaster_auto")
- I dati Google Fit possono popolare la daily timeline per giorni storici
