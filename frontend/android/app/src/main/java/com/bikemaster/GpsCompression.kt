package com.bikemaster

import kotlin.math.abs
import kotlin.math.hypot

/**
 * Pure GPS math utilities, kept free of Android framework dependencies so they can be
 * unit-tested with plain JUnit (#227) and reused by [BikeTrackingService].
 *
 * The Douglas-Peucker implementation mirrors `bike_analyzer/backend/ingestion/gps_parser.py`
 * (`douglas_peucker`, tolerance 0.00005 by default) so the mobile compression matches the
 * backend decimation used by `POST /api/v1/import/gpx`.
 */
object GpsCompression {

    const val DEFAULT_TOLERANCE = 0.00005

    /** Perpendicular distance of [point] from the segment [start]-[end]. */
    fun perpendicularDistance(point: GpsPoint, start: GpsPoint, end: GpsPoint): Double {
        val dx = end.lon - start.lon
        val dy = end.lat - start.lat
        if (dx == 0.0 && dy == 0.0) {
            return hypot(point.lat - start.lat, point.lon - start.lon)
        }
        val num = abs(dy * point.lon - dx * point.lat + end.lon * start.lat - end.lat * start.lon)
        val den = hypot(dx, dy)
        return if (den == 0.0) 0.0 else num / den
    }

    /** Ramer-Douglas-Peucker simplification of a polyline. */
    fun douglasPeucker(points: List<GpsPoint>, tolerance: Double = DEFAULT_TOLERANCE): List<GpsPoint> {
        if (points.size <= 2) return points.toList()
        val start = points.first()
        val end = points.last()
        var maxDist = 0.0
        var index = 0
        for (i in 1 until points.size - 1) {
            val d = perpendicularDistance(points[i], start, end)
            if (d > maxDist) {
                maxDist = d
                index = i
            }
        }
        return if (maxDist > tolerance) {
            val left = douglasPeucker(points.subList(0, index + 1), tolerance)
            val right = douglasPeucker(points.subList(index, points.size), tolerance)
            left.dropLast(1) + right
        } else {
            listOf(start, end)
        }
    }

    /** Great-circle distance in metres between two coordinates (haversine). */
    fun haversineMeters(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = kotlin.math.sin(dLat / 2).pow(2.0) +
            kotlin.math.cos(Math.toRadians(lat1)) * kotlin.math.cos(Math.toRadians(lat2)) *
            kotlin.math.sin(dLon / 2).pow(2.0)
        return r * 2 * kotlin.math.atan2(kotlin.math.sqrt(a), kotlin.math.sqrt(1 - a))
    }

    /** Total length in metres of a polyline. */
    fun pathLengthMeters(points: List<GpsPoint>): Double {
        if (points.size < 2) return 0.0
        var total = 0.0
        for (i in 1 until points.size) {
            total += haversineMeters(
                points[i - 1].lat, points[i - 1].lon, points[i].lat, points[i].lon
            )
        }
        return total
    }
}
