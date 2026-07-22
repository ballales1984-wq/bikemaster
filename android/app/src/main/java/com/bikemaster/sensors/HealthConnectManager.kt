package com.bikemaster.sensors

import android.util.Log
import androidx.activity.result.ActivityResultLauncher
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.response.ReadRecordsResponse
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import java.time.Instant
import java.time.ZoneOffset

class HealthConnectManager(private val context: android.content.Context) {

    companion object {
        private const val TAG = "HealthConnectManager"
        val PERMISSIONS = setOf(
            HealthPermission.getReadPermission(WeightRecord::class),
            HealthPermission.getWritePermission(WeightRecord::class),
            HealthPermission.getReadPermission(HeartRateRecord::class),
            HealthPermission.getWritePermission(HeartRateRecord::class),
            HealthPermission.getReadPermission(StepsRecord::class),
            HealthPermission.getWritePermission(StepsRecord::class),
            HealthPermission.getReadPermission(ExerciseSessionRecord::class),
            HealthPermission.getWritePermission(ExerciseSessionRecord::class),
            HealthPermission.getReadPermission(HeightRecord::class),
            HealthPermission.getWritePermission(HeightRecord::class),
            HealthPermission.getReadPermission(BodyFatRecord::class),
            HealthPermission.getWritePermission(BodyFatRecord::class)
        )
    }

    private val healthConnectClient: HealthConnectClient = HealthConnectClient.getOrCreate(context)

    enum class Availability {
        AVAILABLE,
        NOT_INSTALLED,
        NOT_SUPPORTED
    }

    fun checkAvailability(): Availability {
        return try {
            val sdkStatus = HealthConnectClient.getSdkStatus(context)
            when (sdkStatus) {
                HealthConnectClient.SDK_AVAILABLE -> Availability.AVAILABLE
                HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> Availability.NOT_INSTALLED
                else -> Availability.NOT_SUPPORTED
            }
        } catch (e: Exception) {
            Log.e(TAG, "Health Connect non supportato", e)
            Availability.NOT_SUPPORTED
        }
    }

    fun hasPermissions(): Boolean {
        val granted = healthConnectClient.permissionController.getGrantedPermissions()
        return granted.containsAll(PERMISSIONS)
    }

    fun requestPermissions(launcher: ActivityResultLauncher<Set<HealthPermission>>): Boolean {
        return try {
            val granted = healthConnectClient.permissionController.getGrantedPermissions()
            val missing = PERMISSIONS - granted
            if (missing.isEmpty()) return true
            launcher.launch(missing)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Errore richiesta permessi", e)
            false
        }
    }

    fun readWeight(): Flow<List<WeightRecord>> = callbackFlow {
        try {
            val request = ReadRecordsRequest(recordType = WeightRecord::class)
            val response: ReadRecordsResponse<WeightRecord> = healthConnectClient.readRecords(request)
            trySend(response.records)
        } catch (e: Exception) {
            Log.e(TAG, "Errore lettura peso", e)
            trySend(emptyList())
        }
        close()
    }

    suspend fun writeWeight(weightKg: Double, time: Instant = Instant.now()) {
        try {
            val record = WeightRecord(
                weight = Mass.kilograms(weightKg),
                time = time,
                zoneOffset = ZoneOffset.UTC
            )
            healthConnectClient.insertRecords(listOf(record))
            Log.i(TAG, "Peso scritto: $weightKg kg")
        } catch (e: Exception) {
            Log.e(TAG, "Errore scrittura peso", e)
        }
    }

    fun readHeartRate(): Flow<List<HeartRateRecord>> = callbackFlow {
        try {
            val request = ReadRecordsRequest(recordType = HeartRateRecord::class)
            val response: ReadRecordsResponse<HeartRateRecord> = healthConnectClient.readRecords(request)
            trySend(response.records)
        } catch (e: Exception) {
            Log.e(TAG, "Errore lettura battito", e)
            trySend(emptyList())
        }
        close()
    }

    suspend fun writeHeartRate(bpm: Long, time: Instant = Instant.now()) {
        try {
            val record = HeartRateRecord(
                time = time,
                zoneOffset = ZoneOffset.UTC,
                samples = listOf(HeartRateRecord.Sample(time = time, beatsPerMinute = bpm))
            )
            healthConnectClient.insertRecords(listOf(record))
        } catch (e: Exception) {
            Log.e(TAG, "Errore scrittura battito", e)
        }
    }

    fun readSteps(): Flow<List<StepsRecord>> = callbackFlow {
        try {
            val request = ReadRecordsRequest(recordType = StepsRecord::class)
            val response: ReadRecordsResponse<StepsRecord> = healthConnectClient.readRecords(request)
            trySend(response.records)
        } catch (e: Exception) {
            Log.e(TAG, "Errore lettura passi", e)
            trySend(emptyList())
        }
        close()
    }

    suspend fun writeSteps(count: Long, startTime: Instant = Instant.now().minusSeconds(86400), endTime: Instant = Instant.now()) {
        try {
            val record = StepsRecord(
                startTime = startTime,
                endTime = endTime,
                startZoneOffset = ZoneOffset.UTC,
                endZoneOffset = ZoneOffset.UTC,
                count = count
            )
            healthConnectClient.insertRecords(listOf(record))
        } catch (e: Exception) {
            Log.e(TAG, "Errore scrittura passi", e)
        }
    }

    fun readExercise(): Flow<List<ExerciseSessionRecord>> = callbackFlow {
        try {
            val request = ReadRecordsRequest(recordType = ExerciseSessionRecord::class)
            val response: ReadRecordsResponse<ExerciseSessionRecord> = healthConnectClient.readRecords(request)
            trySend(response.records)
        } catch (e: Exception) {
            Log.e(TAG, "Errore lettura esercizi", e)
            trySend(emptyList())
        }
        close()
    }

    suspend fun writeExercise(title: String, startTime: Instant, endTime: Instant) {
        try {
            val record = ExerciseSessionRecord(
                title = title,
                startTime = startTime,
                startZoneOffset = ZoneOffset.UTC,
                endTime = endTime,
                endZoneOffset = ZoneOffset.UTC,
                exerciseType = ExerciseSessionRecord.EXERCISE_TYPE_CYCLING
            )
            healthConnectClient.insertRecords(listOf(record))
        } catch (e: Exception) {
            Log.e(TAG, "Errore scrittura esercizio", e)
        }
    }

    fun readHeight(): Flow<List<HeightRecord>> = callbackFlow {
        try {
            val request = ReadRecordsRequest(recordType = HeightRecord::class)
            val response: ReadRecordsResponse<HeightRecord> = healthConnectClient.readRecords(request)
            trySend(response.records)
        } catch (e: Exception) {
            Log.e(TAG, "Errore lettura altezza", e)
            trySend(emptyList())
        }
        close()
    }

    suspend fun writeHeight(heightMeters: Double, time: Instant = Instant.now()) {
        try {
            val record = HeightRecord(
                height = HeightRecord.Height(heightMeters),
                time = time,
                zoneOffset = ZoneOffset.UTC
            )
            healthConnectClient.insertRecords(listOf(record))
        } catch (e: Exception) {
            Log.e(TAG, "Errore scrittura altezza", e)
        }
    }

    fun readBodyFat(): Flow<List<BodyFatRecord>> = callbackFlow {
        try {
            val request = ReadRecordsRequest(recordType = BodyFatRecord::class)
            val response: ReadRecordsResponse<BodyFatRecord> = healthConnectClient.readRecords(request)
            trySend(response.records)
        } catch (e: Exception) {
            Log.e(TAG, "Errore lettura massa grassa", e)
            trySend(emptyList())
        }
        close()
    }

    suspend fun writeBodyFat(percentage: Double, time: Instant = Instant.now()) {
        try {
            val record = BodyFatRecord(
                percentage = BodyFatRecord.BodyFatPercentage(percentage),
                time = time,
                zoneOffset = ZoneOffset.UTC
            )
            healthConnectClient.insertRecords(listOf(record))
        } catch (e: Exception) {
            Log.e(TAG, "Errore scrittura massa grassa", e)
        }
    }
}