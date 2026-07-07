package com.bikemaster.tracking

object AutoPausePolicy {

    fun shouldPause(currentSpeedKmh: Double, activityType: Int, isPaused: Boolean): Boolean {
        return if (isPaused) {
            !(activityType in setOf(0, 7, 8) && currentSpeedKmh >= 3.0)
        } else {
            activityType == 3 && currentSpeedKmh < 3.0
        }
    }
}
