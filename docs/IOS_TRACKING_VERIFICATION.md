# iOS Tracking Verification Report

## Stato Preparazione

| Componente | Stato | Note |
|---|---|---|
| `BikeTrackingPlugin.swift` | ✅ Pronto | Plugin Capacitor 5 completo |
| `AppDelegate.swift` | ✅ Pronto | Delegate minimale per Capacitor 5 |
| `Info.plist` | ✅ Pronto | Permessi + background modes |
| `Podfile` | ✅ Creato | Configurato per iOS 16.0 |
| `capacitor.config.json` | ✅ Allineato | Config iOS presente |
| Web assets (`dist/`) | ✅ Build riuscita | 129 moduli trasformati |

## File Chiave

```
frontend/
├── capacitor.config.json          # Config app + plugin tracking
├── ios/
│   ├── App/
│   │   ├── AppDelegate.swift       # Entry point iOS
│   │   ├── Info.plist              # Permessi location/bluetooth/motion
│   │   ├── BikeTracking/
│   │   │   └── BikeTrackingPlugin.swift  # Plugin Capacitor 5
│   │   └── Podfile                 # Dipendenze CocoaPods
│   └── App.xcworkspace/            # Generato da cap sync (mancante su Windows)
```

## Problemi Riscontrati su Windows

1. **CocoaPods non installato**: `npx cap sync ios` salta `pod install` e non genera `.xcodeproj`/`.xcworkspace`.
2. **Xcode non disponibile**: impossibile validare compile e firma.

## Procedura di Verifica su macOS

```bash
# 1. Prerequisiti
xcode-select --install
sudo gem install cocoapods

# 2. Build web e sync iOS
cd frontend
npm run build
npx cap sync ios

# 3. Installa pods
cd ios/App
pod install
cd ../..

# 4. Apri Xcode
open ios/App.xcworkspace
```

## Controlli in Xcode

1. **Target → Signing & Capabilities**
   - Team selezionato
   - Bundle ID: `com.bikemaster`
   - Deployment Target: iOS 16.0

2. **Target → Info → Custom iOS Target Properties**
   - Verificare `UIBackgroundModes` contenga `location`
   - Verificare `NSLocationWhenInUseUsageDescription`
   - Verificare `NSLocationAlwaysAndWhenInUseUsageDescription`

3. **Build Settings → Framework Search Paths**
   - Deve includere `$(inherited)` e i path di Capacitor

4. **Build Phase → Copy Bundle Resources**
   - Verificare che `BikeTrackingPlugin.swift` sia incluso

5. **Run su dispositivo fisico** (il simulatore non ha GPS reale)
   - Consentire permessi location
   - Verificare tracking in background
   - Verificare scrittura GPX

## Note Tecniche

- Il plugin iOS usa `UIBackgroundTaskIdentifier` per continuare il tracking in background.
- La velocità è convertita da m/s a km/h per coerenza con Android/web.
- Il filtro accuratezza scarta punti con `horizontalAccuracy > 20m`.
- Lo stato tracking è persistito in `UserDefaults` per recovery dopo chiusura app.
