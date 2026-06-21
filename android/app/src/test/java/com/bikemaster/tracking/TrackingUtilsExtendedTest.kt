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
        assertTrue("Distance should be < 10km", distance < 10.0)
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
}
