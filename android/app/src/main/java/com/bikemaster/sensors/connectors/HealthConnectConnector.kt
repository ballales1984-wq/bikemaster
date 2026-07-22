package com.bikemaster.sensors.connectors

import android.util.Log
import com.bikemaster.sensors.HealthConnectManager
import kotlinx.coroutines.flow.first

class HealthConnectConnector(private val healthConnectManager: HealthConnectManager) : Connector {

    override val type: ConnectorType = ConnectorType.HEALTH_CONNECT

    override suspend fun sync(): ConnectorResult {
        return try {
            if (healthConnectManager.checkAvailability() != HealthConnectManager.Availability.AVAILABLE) {
                return ConnectorResult(success = false, message = "Health Connect non disponibile")
            }

            if (!healthConnectManager.hasPermissions()) {
                return ConnectorResult(success = false, message = "Permessi Health Connect mancanti")
            }

            val weightRecords = healthConnectManager.readWeight().first()
            val heartRateRecords = healthConnectManager.readHeartRate().first()
            val stepsRecords = healthConnectManager.readSteps().first()
            val caloriesRecords = healthConnectManager.readCalories().first()
            val exerciseRecords = healthConnectManager.readExercise().first()

            val healthMetrics = mutableListOf<com.bikemaster.models.HealthMetric>()

            weightRecords.forEach { r ->
                healthMetrics.add(com.bikemaster.models.HealthMetric(
                    metric_type = "weight_kg",
                    value = r.weight.inKilograms,
                    unit = "kg",
                    source = "health_connect",
                    recorded_at = r.time.toString()
                ))
            }

            heartRateRecords.forEach { r ->
                val bpm = r.samples.firstOrNull()?.beatsPerMinute ?: 0L
                healthMetrics.add(com.bikemaster.models.HealthMetric(
                    metric_type = "heart_rate_bpm",
                    value = bpm.toDouble(),
                    unit = "bpm",
                    source = "health_connect",
                    recorded_at = r.startTime.toString()
                ))
            }

            stepsRecords.forEach { r ->
                healthMetrics.add(com.bikemaster.models.HealthMetric(
                    metric_type = "steps_count",
                    value = r.count.toDouble(),
                    unit = "count",
                    source = "health_connect",
                    recorded_at = r.startTime.toString()
                ))
            }

            caloriesRecords.forEach { r ->
                healthMetrics.add(com.bikemaster.models.HealthMetric(
                    metric_type = "calories_kcal",
                    value = r.energy.inKilocalories,
                    unit = "kcal",
                    source = "health_connect",
                    recorded_at = r.startTime.toString()
                ))
            }

            exerciseRecords.forEach { r ->
                healthMetrics.add(com.bikemaster.models.HealthMetric(
                    metric_type = "exercise_session",
                    value = 1.0,
                    unit = "session",
                    source = "health_connect",
                    recorded_at = r.startTime.toString()
                ))
            }

            Log.i("HealthConnectConnector", "Sincronizzati ${healthMetrics.size} metriche Health Connect")
            ConnectorResult(success = true, message = "Sincronizzati ${healthMetrics.size} record", metricsSynced = healthMetrics.size, metrics = healthMetrics)
        } catch (e: Exception) {
            Log.e("HealthConnectConnector", "Errore sync Health Connect", e)
            ConnectorResult(success = false, message = e.message)
        }
    }

    override fun isAvailable(): Boolean {
        return healthConnectManager.checkAvailability() == HealthConnectManager.Availability.AVAILABLE
    }
}