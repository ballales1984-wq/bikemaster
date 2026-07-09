package com.bikemaster.tracking

import android.location.Location
import com.bikemaster.models.GPSPoint
import com.bikemaster.utils.LocationTracker
import org.junit.Assert.*
import org.junit.Test

class TrackingUtilsExtendedTest {

    @Test
    fun testDistanceCalculationLargeDistance() {
        val loc1 = Location("test").apply {
            latitude = 45.0
            longitude = 9.0
        }
        val loc2 = Location("test").apply {
            latitude = 46.0
            longitude = 10.0
        }
        val results = FloatArray(1)
        Location.distanceBetween(
            loc1.latitude, loc1.longitude,
            loc2.latitude, loc2.longitude,
            results
        )
        val distance = results[0] / 1000.0
        assertTrue("Distance should be > 100km", distance > 100)
        assertTrue("Distance should be < 200km", distance < 200)
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
    fun testCalculateDistanceFromGPSPoints() {
        val tracker = LocationTracker(null)
        val points = listOf(
            GPSPoint(45.0, 9.0, 0.0, null),
            GPSPoint(45.01, 9.01, 0.0, null),
            GPSPoint(45.02, 9.02, 0.0, null),
        )
        val distance = tracker.calculateDistance(points)
        assertTrue("Distance should be > 0", distance > 0.0)
        assertTrue("Distance should be < 10000m", distance < 10000.0)
    }

    @Test
    fun testCalculateDistanceEmptyList() {
        val tracker = LocationTracker(null)
        val distance = tracker.calculateDistance(emptyList())
        assertEquals("Empty list distance should be 0", 0.0, distance, 0.0)
    }

    @Test
    fun testCalculateDistanceSinglePoint() {
        val tracker = LocationTracker(null)
        val points = listOf(
            GPSPoint(45.0, 9.0, 0.0, null)
        )
        val distance = tracker.calculateDistance(points)
        assertEquals("Single point distance should be 0", 0.0, distance, 0.0)
    }

    @Test
    fun testCalculateDistanceTwoIdenticalPoints() {
        val tracker = LocationTracker(null)
        val points = listOf(
            GPSPoint(45.0, 9.0, 0.0, null),
            GPSPoint(45.0, 9.0, 0.0, null),
        )
        val distance = tracker.calculateDistance(points)
        assertEquals("Identical points distance should be ~0", 0.0, distance, 0.1)
    }

    @Test
    fun testTrackingStateDefaultValues() {
        val state = TrackingState()
        assertEquals(0.0, state.distance, 0.0)
        assertEquals(0.0, state.currentSpeed, 0.0)
        assertEquals(0.0, state.avgSpeed, 0.0)
        assertEquals(0L, state.elapsedTime)
        assertEquals(0.0, state.elevation, 0.0)
        assertEquals(0, state.points)
        assertFalse(state.isPaused)
        assertNull(state.lastLatitude)
        assertNull(state.lastLongitude)
        assertNull(state.heartRate)
        assertNull(state.cadence)
        assertNull(state.power)
    }

    @Test
    fun testTrackingStateWithValues() {
        val state = TrackingState(
            distance = 25000.0,
            currentSpeed = 28.5,
            avgSpeed = 24.2,
            elapsedTime = 5400L,
            elevation = 450.0,
            points = 1200,
            isPaused = true,
            lastLatitude = 45.4642,
            lastLongitude = 9.19,
            heartRate = 155,
            cadence = 90,
            power = 220
        )
        assertEquals(25000.0, state.distance, 0.0)
        assertEquals(28.5, state.currentSpeed, 0.1)
        assertEquals(24.2, state.avgSpeed, 0.1)
        assertEquals(5400L, state.elapsedTime)
        assertEquals(450.0, state.elevation, 0.0)
        assertEquals(1200, state.points)
        assertTrue(state.isPaused)
        assertEquals(45.4642, state.lastLatitude!!, 0.0001)
        assertEquals(9.19, state.lastLongitude!!, 0.0001)
        assertEquals(155, state.heartRate)
        assertEquals(90, state.cadence)
        assertEquals(220, state.power)
    }

    @Test
    fun testAutoPausePolicy_pausesWhenStillBelowThreshold() {
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
    fun autoPausePolicy_doesNotPauseWhenWalkingAndPaused() {
        assertFalse(AutoPausePolicy.shouldPause(4.0, 8, true))
    }

    @Test
    fun testDistanceCalculationNearbyPoints() {
        val loc1 = Location("test").apply {
            latitude = 45.4642
            longitude = 9.19
        }
        val loc2 = Location("test").apply {
            latitude = 45.4643
            longitude = 9.1901
        }
        val results = FloatArray(1)
        Location.distanceBetween(
            loc1.latitude, loc1.longitude,
            loc2.latitude, loc2.longitude,
            results
        )
        val distance = results[0]
        assertTrue("Nearby points should be < 100m", distance < 100)
        assertTrue("Nearby points should be > 0m", distance > 0)
    }
}
