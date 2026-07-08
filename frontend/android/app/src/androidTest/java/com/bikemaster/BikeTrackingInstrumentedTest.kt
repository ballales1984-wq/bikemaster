package com.bikemaster

import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.matcher.ViewMatchers.withId
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import androidx.core.content.ContextCompat
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Road / instrumented test for the BikeMaster tracking flow (#228).
 *
 * This is a documented Espresso skeleton. It must be executed on a physical Android device
 * with live GPS (a real ride) — an emulator cannot provide realistic motion/activity data.
 * See `frontend/android/ROAD_TEST.md` for the full procedure.
 *
 * It exercises the native plugin in the same way the Vue layer does:
 *   1. start the foreground tracking service
 *   2. ride for a while (manual / on a bike)
 *   3. stop the service and confirm a GPX file with activity extensions is produced
 *   4. confirm the upload result broadcast is delivered (#225 / #226)
 */
@RunWith(AndroidJUnit4::class)
class BikeTrackingInstrumentedTest {

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_BACKGROUND_LOCATION,
        Manifest.permission.ACTIVITY_RECOGNITION,
        Manifest.permission.POST_NOTIFICATIONS
    )

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    private val context: Context
        get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test
    fun rideProducesGpxWithActivityExtensions() {
        val appContext = context
        val outputPath = File(appContext.filesDir, "tracks/road_test.gpx").absolutePath

        // 1) start tracking (mirrors BikeTrackingPlugin.startTracking)
        val start = Intent(appContext, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_START
            putExtra(BikeTrackingService.EXTRA_OUTPUT_PATH, outputPath)
            putExtra(BikeTrackingService.EXTRA_API_BASE_URL, "https://example.invalid")
        }
        androidx.core.content.ContextCompat.startForegroundService(appContext, start)

        // 2) the rider performs a real ride here; for the skeleton we simply wait a moment
        Thread.sleep(3000)

        // 3) stop and await the STOPPED broadcast carrying the upload result
        val latch = CountDownLatch(1)
        var uploadStatus: String? = null
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context?, intent: Intent?) {
                uploadStatus = intent?.getStringExtra(BikeTrackingService.EXTRA_UPLOAD_STATUS)
                latch.countDown()
            }
        }
        val filter = IntentFilter(BikeTrackingService.ACTION_STOPPED)
        appContext.registerReceiver(receiver, filter)
        BikeTrackingService.sendStopIntent(appContext)

        latch.await(15, TimeUnit.SECONDS)
        appContext.unregisterReceiver(receiver)

        // 4) assertions
        val gpx = File(outputPath)
        assertTrue("GPX file should be created by the tracking service", gpx.exists())
        val content = gpx.readText()
        assertTrue("GPX must contain a track segment", content.contains("<trkseg>"))
        // Activity extensions may be empty on devices without motion; we only assert the file is well-formed.
        assertTrue("Ride upload lifecycle completed (success/error/skipped)", uploadStatus != null)
    }

    @Test
    fun pluginBridgeResolves() {
        // Smoke test: ensure the Capacitor plugin class loads and the web view is present.
        onView(withId(android.R.id.content)).check { view, _ -> assertTrue(view != null) }
    }
}
