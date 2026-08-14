# Phone GPS Tracking - Testing Guide

## Test Unitari

### Android (Kotlin)
```bash
# Esegui test unitari
./gradlew test

# Test specifico per tracking
./gradlew test --tests "com.bikemaster.tracking.*"
```

**File:** `android/app/src/test/java/com/bikemaster/tracking/BikeTrackingServiceTest.kt`
- Test calcolo distanza GPS
- Test inizializzazione TrackingState
- Test aggiornamento metriche

### Frontend (Vue + Vitest)
```bash
# Esegui test frontend
npm run test -- --pool=threads

# Coverage
npm run test:coverage
```

**File:** `frontend/src/stores/trackingStore.test.ts`
- Test stato iniziale
- Test start/pause/resume/stop
- Test aggiornamento metriche
- Test formattazione tempo/distanza

## Test Instrumented (Android)

```bash
# Test su dispositivo/emulatore
./gradlew connectedAndroidTest
```

### Casi di Test
1. **Permessi GPS** - Richiesta permessi in sequenza
2. **Foreground Service** - Avvio/fermata service in background
3. **GPX Writing** - Verifica scrittura file corretto
4. **Auto-Pause** - Rilevamento velocità < 3 km/h
5. **Battery Optimization** - Richiesta esenzione

## Test Strada

### Device Matrix
| Device | Android Version | Note |
|--------|-----------------|------|
| Pixel 7 | 14 | Emulatore |
| Samsung S23 | 13 | Device reale |
| Xiaomi Redmi | 12 | Device economico |
| Emulator API 31 | 12 | Pixel 4 |

### Scenario Test
1. Tracking 30 minuti in città
2. Tracking 2 ore in natura
3. App uccisa durante tracking → resume
4. Batteria < 10%
5. GPS perso in tunnel
6. Modalità background
7. Notifica foreground service
8. Sensori BLE (se disponibili)

## Test Backend Integration

```bash
# Test import GPX
python -m pytest tests/test_import.py -v

# Scenario end-to-end
curl -X POST -F "file=@track.gpx" http://localhost:8001/api/v1/import/gpx
```

## Coverage Target

| Modulo | Target |
|--------|--------|
| BikeTrackingService.kt | ≥ 80% |
| BikeTrackingPlugin.kt | ≥ 75% |
| trackingStore.ts | ≥ 90% |
| RideTracking.vue | ≥ 70% |

## CI Pipeline

Aggiunto in `.github/workflows/ci.yml`:
- Job `frontend` per build/test Vue
- Job `android-release.yml` per build APK