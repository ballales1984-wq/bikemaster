package com.bikemaster.network

import android.util.Log
import com.bikemaster.models.HealthMetric

object HealthSyncUploader {

    private const val TAG = "HealthSyncUploader"

    suspend fun uploadMetrics(context: android.content.Context, athleteId: Int, metrics: List<HealthMetric>): Boolean {
        return try {
            val api = ApiClient.getApi(context)
            val body = metrics.map { m ->
                mapOf(
                    "metric_type" to m.metric_type,
                    "value" to m.value,
                    "unit" to m.unit,
                    "source" to m.source,
                    "recorded_at" to m.recorded_at
                )
            }
            val response = api.addHealthMetrics(athleteId, body)
            val ok = response["saved"] != null
            if (ok) {
                Log.i(TAG, "Upload completato: ${(response["saved"] as? List<*>)?.size ?: 0} metriche")
            } else {
                Log.w(TAG, "Upload fallito: $response")
            }
            ok
        } catch (e: Exception) {
            Log.e(TAG, "Errore upload metriche salute", e)
            false
        }
    }
}