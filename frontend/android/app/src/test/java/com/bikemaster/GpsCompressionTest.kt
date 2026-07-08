package com.bikemaster

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for GPS compression (Douglas-Peucker), distance and ride mapping (#227).
 * Mirrors the backend algorithm in `bike_analyzer/backend/ingestion/gps_parser.py`.
 */
class GpsCompressionTest {

    @Test
    fun douglasPeuckerKeepsEndpoints() {
        val points = listOf(
            GpsPoint(45.0, 9.0),
            GpsPoint(45.0001, 9.0001),
            GpsPoint(45.0002, 9.0002),
            GpsPoint(45.001, 9.001)
        )
        val simplified = GpsCompression.douglasPeucker(points)
        assertEquals(points.first(), simplified.first())
        assertEquals(points.last(), simplified.last())
    }

    @Test
    fun douglasPeuckerRemovesCollinearPoints() {
        // All points lie on the same line -> only endpoints survive above tolerance.
        val points = (0..100).map { i -> GpsPoint(45.0 + i * 0.00001, 9.0 + i * 0.00001) }
        val simplified = GpsCompression.douglasPeucker(points, tolerance = 0.00005)
        // Endpoints plus a few near the far end, but far fewer than 101.
        assertTrue(simplified.size < points.size / 2)
        assertEquals(2, simplified.size.coerceAtLeast(2))
        assertEquals(points.first(), simplified.first())
        assertEquals(points.last(), simplified.last())
    }

    @Test
    fun douglasPeuckerReturnsSmallInputsUnchanged() {
        val one = listOf(GpsPoint(45.0, 9.0))
        val two = listOf(GpsPoint(45.0, 9.0), GpsPoint(45.001, 9.001))
        assertEquals(1, GpsCompression.douglasPeucker(one).size)
        assertEquals(2, GpsCompression.douglasPeucker(two).size)
    }

    @Test
    fun perpendicularDistanceOfPointOnSegmentIsZero() {
        val start = GpsPoint(0.0, 0.0)
        val end = GpsPoint(0.0, 10.0)
        val mid = GpsPoint(0.0, 5.0)
        assertEquals(0.0, GpsCompression.perpendicularDistance(mid, start, end), 1e-12)
    }

    @Test
    fun haversineOneDegreeLatitudeIsAbout111km() {
        val meters = GpsCompression.haversineMeters(0.0, 0.0, 1.0, 0.0)
        assertEquals(111_195.0, meters, 200.0)
    }

    @Test
    fun pathLengthOfTwoPointsMatchesHaversine() {
        val a = GpsPoint(45.0, 9.0)
        val b = GpsPoint(45.001, 9.0)
        val expected = GpsCompression.haversineMeters(a.lat, a.lon, b.lat, b.lon)
        assertEquals(expected, GpsCompression.pathLengthMeters(listOf(a, b)), 1e-6)
    }

    @Test
    fun pathLengthEmptyOrSingleIsZero() {
        assertEquals(0.0, GpsCompression.pathLengthMeters(emptyList()), 0.0)
        assertEquals(0.0, GpsCompression.pathLengthMeters(listOf(GpsPoint(45.0, 9.0))), 0.0)
    }
}
