package com.bikemaster.tracking

import android.content.Context
import android.location.Location
import org.junit.Assert.*
import org.junit.Test
import java.io.File

class TrackingServiceUtilsTest {

    @Test
    fun testDistanceCalculationInMeters() {
        val loc1 = Location("test").apply {
            latitude = 45.4642
            longitude = 9.19
        }
        val loc2 = Location("test").apply {
            latitude = 45.4652
            longitude = 9.20
        }
        val results = FloatArray(1)
        Location.distanceBetween(
            loc1.latitude, loc1.longitude,
            loc2.latitude, loc2.longitude,
            results
        )
        val distance = results[0]
        assertTrue("Distance should be > 0", distance > 0)
        assertTrue("Distance should be < 2000m", distance < 2000)
    }

    @Test
    fun testDistanceCalculationSamePoint() {
        val loc = Location("test").apply {
            latitude = 45.4642
            longitude = 9.19
        }
        val results = FloatArray(1)
        Location.distanceBetween(
            loc.latitude, loc.longitude,
            loc.latitude, loc.longitude,
            results
        )
        val distance = results[0]
        assertEquals("Same point distance should be 0", 0.0f, distance, 0.1f)
    }

    @Test
    fun trackingState_initializesWithZeros() {
        val state = TrackingState()
        assertEquals(0.0, state.distance, 0.0)
        assertEquals(0.0, state.currentSpeed, 0.0)
        assertEquals(0, state.points)
    }

    @Test
    fun trackingState_withParameters_setsCorrectly() {
        val state = TrackingState(
            distance = 10000.0,
            currentSpeed = 25.5,
            avgSpeed = 22.0,
            elapsedTime = 3600L,
            points = 100
        )
        assertEquals(10000.0, state.distance, 0.0)
        assertEquals(25.5, state.currentSpeed, 0.1)
        assertEquals(100, state.points)
    }

    @Test
    fun autoPausePolicy_pausesWhenStillBelowThreshold() {
        assertTrue(AutoPausePolicy.shouldPause(0.5, 3, false))
    }

    @Test
    fun autoPausePolicy_keepsTrackingWhenMovingFastAndStill() {
        assertFalse(AutoPausePolicy.shouldPause(15.0, 3, false))
    }

    @Test
    fun autoPausePolicy_resumesWhenOnBikeAndFast() {
        assertFalse(AutoPausePolicy.shouldPause(10.0, 7, true))
    }

    @Test
    fun autoPausePolicy_staysPausedWhenStillAndSlow() {
        assertTrue(AutoPausePolicy.shouldPause(0.5, 3, true))
    }

    @Test
    fun testTrackingStateSerializable() {
        val state = TrackingState(
            distance = 15000.0,
            currentSpeed = 30.0,
            avgSpeed = 25.0,
            elapsedTime = 1800L,
            elevation = 320.0,
            points = 500,
            isPaused = false,
            lastLatitude = 45.4642,
            lastLongitude = 9.19,
            heartRate = 160,
            cadence = 95,
            power = 250
        )
        assertTrue(state is java.io.Serializable)
    }

    @Test
    fun testGpxOutputPathGeneration() {
        val tracksDir = File("test_tracks").apply { mkdirs() }
        val path = File(tracksDir, "track_${System.currentTimeMillis()}.gpx").absolutePath
        assertTrue(path.endsWith(".gpx"))
        assertTrue(path.contains("track_"))
    }

    @Test
    fun testActivityRecognitionIntentCreation() {
        val intent = android.content.Intent(android.content.ContextWrapper(null), BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_ACTIVITY
        }
        assertEquals(BikeTrackingService.ACTION_ACTIVITY, intent.action)
    }

    @Test
    fun testLocationCallbackNotNullAfterCreation() {
        val service = BikeTrackingService()
        assertNotNull(service)
    }

    @Test
    fun testSaveTrackingState() {
        val context = android.content.ContextWrapper(null)
        val prefs = context.getSharedPreferences("tracking_state", Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
        BikeTrackingService::class.java.getDeclaredMethod("saveTrackingState", Boolean::class.java, String::class.java).apply {
            isAccessible = true
            invoke(BikeTrackingService(), true, "/test/path.gpx")
        }
        val saved = prefs.getBoolean("is_tracking", false)
        val path = prefs.getString("output_path", null)
        assertTrue(saved)
        assertEquals("/test/path.gpx", path)
    }

    @Test
    fun testHasActiveTracking() {
        val context = android.content.ContextWrapper(null)
        val prefs = context.getSharedPreferences("tracking_state", Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
        assertFalse(BikeTrackingService.hasActiveTracking(context))
        prefs.edit().putBoolean("is_tracking", true).apply()
        assertTrue(BikeTrackingService.hasActiveTracking(context))
    }

    @Test
    fun testGetActiveTrackingPath() {
        val context = android.content.ContextWrapper(null)
        val prefs = context.getSharedPreferences("tracking_state", Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
        assertNull(BikeTrackingService.getActiveTrackingPath(context))
        prefs.edit().putString("output_path", "/test/track.gpx").apply()
        assertEquals("/test/track.gpx", BikeTrackingService.getActiveTrackingPath(context))
    }
}
