package com.bikemaster.health

import android.content.Context
import android.content.pm.PackageManager
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Instant

object HealthConnectHelper {
    private var healthConnectClient: HealthConnectClient? = null

    fun initialize(context: Context): Boolean {
        return try {
            val pm = context.packageManager
            val intent = pm.getPackageInfo("com.google.android.apps.healthdata", PackageManager.GET_ACTIVITIES)
            healthConnectClient = HealthConnectClient.getOrCreate(context)
            true
        } catch (e: Exception) {
            false
        }
    }

    fun isAvailable(context: Context): Boolean {
        return try {
            val pm = context.packageManager
            pm.getPackageInfo("com.google.android.apps.healthdata", PackageManager.GET_ACTIVITIES)
            HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE
        } catch (e: Exception) {
            false
        }
    }

    fun readMetrics(): Map<String, Any?> {
        val client = healthConnectClient ?: return emptyMap()
        val now = Instant.now()
        val start = now.minusSeconds(86400)
        val metrics = mutableMapOf<String, Any?>()

        try {
            val stepsRequest = ReadRecordsRequest(
                recordType = StepsRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, now)
            )
            val stepsResponse = client.readRecords(stepsRequest)
            val totalSteps = stepsResponse.records.sumOf { it.count }
            metrics["steps"] = totalSteps
        } catch (e: Exception) {
            metrics["steps"] = null
        }

        try {
            val hrRequest = ReadRecordsRequest(
                recordType = HeartRateRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, now)
            )
            val hrResponse = client.readRecords(hrRequest)
            val avgHr = hrResponse.records.flatMap { it.samples }.map { it.beatsPerMinute }.average()
            metrics["heart_rate_bpm"] = if (avgHr.isNaN()) null else avgHr
        } catch (e: Exception) {
            metrics["heart_rate_bpm"] = null
        }

        try {
            val weightRequest = ReadRecordsRequest(
                recordType = WeightRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, now)
            )
            val weightResponse = client.readRecords(weightRequest)
            val latestWeight = weightResponse.records.maxByOrNull { it.time }
            metrics["weight_kg"] = latestWeight?.weight?.kilograms
        } catch (e: Exception) {
            metrics["weight_kg"] = null
        }

        return metrics
    }
}
