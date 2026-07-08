package com.bikemaster

import com.google.android.gms.location.DetectedActivity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for ride mapping: activity recognition buckets (#224) and GPX extension building
 * used to persist detected activities inside the ride data (#227).
 */
class RideMappingTest {

    @Test
    fun fromGoogleTypeMapsKnownActivities() {
        assertEquals(DetectedActivityType.STILL, DetectedActivityType.fromGoogleType(DetectedActivity.STILL))
        assertEquals(DetectedActivityType.CYCLING, DetectedActivityType.fromGoogleType(DetectedActivity.ON_BICYCLE))
        assertEquals(DetectedActivityType.WALKING, DetectedActivityType.fromGoogleType(DetectedActivity.ON_FOOT))
        assertEquals(DetectedActivityType.WALKING, DetectedActivityType.fromGoogleType(DetectedActivity.WALKING))
        assertEquals(DetectedActivityType.RUNNING, DetectedActivityType.fromGoogleType(DetectedActivity.RUNNING))
        assertEquals(DetectedActivityType.IN_VEHICLE, DetectedActivityType.fromGoogleType(DetectedActivity.IN_VEHICLE))
        assertEquals(DetectedActivityType.UNKNOWN, DetectedActivityType.fromGoogleType(DetectedActivity.UNKNOWN))
    }

    @Test
    fun fromSpeedHeuristicBuckets() {
        assertEquals(DetectedActivityType.STILL, DetectedActivityType.fromSpeed(0.0f))
        assertEquals(DetectedActivityType.STILL, DetectedActivityType.fromSpeed(0.4f))
        assertEquals(DetectedActivityType.WALKING, DetectedActivityType.fromSpeed(1.5f))
        assertEquals(DetectedActivityType.RUNNING, DetectedActivityType.fromSpeed(4.0f))
        assertEquals(DetectedActivityType.CYCLING, DetectedActivityType.fromSpeed(8.0f))
    }

    @Test
    fun activityExtensionXmlRendersSegments() {
        val segments = listOf(
            ActivitySegment(DetectedActivityType.CYCLING, 1000L, 5000L, "play_services"),
            ActivitySegment(DetectedActivityType.STILL, 5000L, 6000L, "speed_heuristic")
        )
        val xml = GpxExtensions.buildActivityExtensionsXml(segments)
        assertTrue(xml.contains("<bikemaster:activities>"))
        assertTrue(xml.contains("type=\"cycling\""))
        assertTrue(xml.contains("type=\"still\""))
        assertTrue(xml.contains("source=\"play_services\""))
        assertTrue(xml.contains("source=\"speed_heuristic\""))
    }

    @Test
    fun activityExtensionXmlEmptyForNoSegments() {
        assertEquals("", GpxExtensions.buildActivityExtensionsXml(emptyList()))
    }

    @Test
    fun segmentsToJsonSerializesAllFields() {
        val segments = listOf(
            ActivitySegment(DetectedActivityType.WALKING, 1000L, 2000L, "play_services")
        )
        val json = GpxExtensions.segmentsToJson(segments)
        assertTrue(json.contains("\"type\":\"walking\""))
        assertTrue(json.contains("\"start\":1000"))
        assertTrue(json.contains("\"end\":2000"))
        assertTrue(json.contains("\"source\":\"play_services\""))
    }
}
