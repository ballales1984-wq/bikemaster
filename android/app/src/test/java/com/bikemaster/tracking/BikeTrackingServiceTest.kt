package com.bikemaster.tracking

import android.location.Location
import org.junit.Test
import org.junit.Assert.*

class TrackingUtilsTest {

    @Test
    fun testDistanceCalculation() {
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
        val distance = results[0] / 1000.0
        assertTrue(distance > 0)
        assertTrue(distance < 2.0)
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
}