# BikeMaster Android — Road Test (#228)

This document describes how to run the instrumented (on-device) test for the Phone GPS
tracking flow: activity recognition (#224), automatic upload (#225) and completion
notification (#226).

## Prerequisites

- Android SDK (API 34) + `local.properties` with `sdk.dir=...`
- A **physical Android device** (API 24+) with live GPS. An emulator cannot produce
  realistic motion/activity data, so the assertions about activity recognition are only
  meaningful on a real ride.
- Google Play services installed on the device (for `ActivityRecognitionClient`; the
  speed-heuristic fallback covers AOSP builds without it).
- Capacitor native project synced: `npm install && npx cap sync android` (run from
  `frontend/`). This generates `settings.gradle`, the Gradle wrapper and `local.properties`.
- A debug build: `./gradlew :app:assembleDebug` then install, or run via Android Studio.

## What is covered

`app/src/androidTest/java/com/bikemaster/BikeTrackingInstrumentedTest.kt`

| Test | Verifies |
| --- | --- |
| `rideProducesGpxWithActivityExtensions` | Starts `BikeTrackingService` (like the Vue layer), waits, stops it, and asserts a well-formed GPX file is produced and the upload lifecycle broadcast (`uploadStatus`) is delivered. |
| `pluginBridgeResolves` | Smoke test that the Capacitor bridge / WebView launches. |

The test grants `ACCESS_FINE_LOCATION`, `ACCESS_BACKGROUND_LOCATION`,
`ACTIVITY_RECOGNITION` and `POST_NOTIFICATIONS` via `GrantPermissionRule`.

## Run

From the generated Android project (`frontend/android`, after `cap sync`):

```bash
./gradlew :app:connectedAndroidTest \
  -Pandroid.testInstrumentationRunner=androidx.test.runner.AndroidJUnitRunner
```

Or in Android Studio: right-click `BikeTrackingInstrumentedTest` → *Run*.

## Road procedure

1. Build & install the debug APK on the phone.
2. Enable GPS and grant location/activity/notification permissions.
3. Start a tracking session from the app's Ride Tracking page, then go for a short bike ride.
4. Stop the session. Confirm:
   - a GPX file is written under the app's `filesDir/tracks/`,
   - the GPX contains `<bikemaster:activities>` with `cycling` segments (activity recognition),
   - an upload completion notification appears (success or queued-for-offline),
   - the ride shows up in the backend after upload to `POST /api/v1/import/gpx`.

## Notes

- The skeleton points `apiBaseUrl` at `https://example.invalid` so it exercises the offline
  path (retry + queue, #225) without a backend. Replace with a real base URL for a full run.
- Unit tests (pure Kotlin, no device needed) live in `app/src/test/` — run them with
  `./gradlew :app:testDebugUnitTest`.
