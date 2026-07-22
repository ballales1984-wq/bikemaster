package com.bikemaster.sensors.connectors

import com.bikemaster.sensors.HealthConnectManager

enum class ConnectorType {
    HEALTH_CONNECT,
    BLE_RUNSTAR,
    BLE_GARMIN,
    BLE_POLAR,
    CLOUD_STRAVA,
    CLOUD_GARMIN,
    CLOUD_GOOGLE_FIT,
    MANUAL
}

data class ConnectorResult(
    val success: Boolean,
    val message: String? = null,
    val metricsSynced: Int = 0,
    val metrics: List<com.bikemaster.models.HealthMetric> = emptyList()
)