package com.bikemaster

import android.os.Parcelable
import com.google.android.gms.location.DetectedActivity
import kotlinx.parcelize.Parcelize

/**
 * Activity types detected during a ride. Names match the semantic buckets used by the
 * backend `parse_gpx_file` extension block and by the ride summary.
 */
enum class DetectedActivityType(val label: String) {
    STILL("still"),
    WALKING("walking"),
    RUNNING("running"),
    CYCLING("cycling"),
    IN_VEHICLE("in_vehicle"),
    UNKNOWN("unknown");

    companion object {
        /** Map a Google Play [DetectedActivity] type constant to our semantic bucket. */
        fun fromGoogleType(type: Int): DetectedActivityType = when (type) {
            DetectedActivity.STILL -> STILL
            DetectedActivity.WALKING -> WALKING
            DetectedActivity.RUNNING -> RUNNING
            DetectedActivity.ON_BICYCLE -> CYCLING
            DetectedActivity.ON_FOOT -> WALKING
            DetectedActivity.IN_VEHICLE -> IN_VEHICLE
            else -> UNKNOWN
        }

        /**
         * Heuristic fallback (no Google Play dependency required) based on GPS speed in m/s.
         * Below ~0.5 m/s the rider is effectively still, walking up to ~2.8 m/s (~10 km/h),
         * running up to ~5.5 m/s (~20 km/h) and cycling beyond that.
         */
        fun fromSpeed(speedMps: Float): DetectedActivityType = when {
            speedMps < 0.5f -> STILL
            speedMps < 2.8f -> WALKING
            speedMps < 5.5f -> RUNNING
            else -> CYCLING
        }
    }
}

/**
 * A contiguous span of a detected activity during a ride.
 * Recorded into the GPX `<extensions>` block so it travels with the ride data (#224).
 */
@Parcelize
data class ActivitySegment(
    val activity: DetectedActivityType,
    val startMs: Long,
    val endMs: Long = startMs,
    val source: String = "play_services"
) : Parcelable
