# Test strada — Phone GPS Tracking

Questa guida documenta le procedure di test on-device per il modulo Phone GPS Tracking, coprendo le verifiche richieste dalla Fase 22 (#224-228).

## Prerequisiti

- Dispositivo Android con GPS attivo.
- Permessi di localizzazione concessi a BikeMaster.
- App installata in debug (`./gradlew assembleDebug` + `adb install`).
- Backend in locale o deploy con `/api/v1/import/gpx` funzionante.

## Checklist test strada

### 1. Auto-upload GPX a fine registrazione
1. Avvia la registrazione GPS e percorri un tratto breve (>500m).
2. Interrompi la registrazione.
3. Conferma che il file GPX venga inviato automaticamente dal frontend e che il backend restituisca 200.
4. Verifica che il punto sia visibile in `RidesPanel`.

### 2. Notifica push di completamento
1. Avvia una registrazione.
2. Metti l'app in background.
3. Interrompi la registrazione.
4. Verifica la notifica locale "BikeMaster — Tracciamento completato".
5. Tocca la notifica: l'app deve riaprire `MainActivity` con il percorso caricato.

### 3. Activity Recognition e auto-pause intelligente
1. Avvia la registrazione e cammina lento (<3km/h).
2. Dopo pochi secondi l'app deve mettersi in pausa automaticamente.
3. Riprendi il movimento in bicicletta (o a passo svelto se su smartphone in tasca).
4. L'app deve riprendere la registrazione automaticamente.
5. Conferma che il pausing manuale funziona ancora.

## Esecuzione test unitari

```bash
# Android unit test (JVM)
cd android && ./gradlew test

# Frontend tracking store
cd frontend && npm run test
```

## Note

- L'activity recognition richiede Google Play Services attivi.
- Su emulatori, simulare attività con `adb shell cmd activity ...` oppure usare il WearOS companion.
