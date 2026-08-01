package com.bikemaster.sensors.connectors

import android.content.Context
import android.util.Log
import com.bikemaster.network.HealthSyncUploader
import com.bikemaster.sensors.HealthConnectManager
import com.bikemaster.utils.PreferencesManager
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

class ConnectorManager(
    private val healthConnectManager: HealthConnectManager,
    private val context: Context,
) {

    companion object {
        private const val TAG = "ConnectorManager"
    }

    private val connectors = mutableListOf<Connector>()

    fun register(connector: Connector) {
        connectors.add(connector)
    }

    fun unregister(connector: Connector) {
        connectors.remove(connector)
    }

    suspend fun syncAll(): List<ConnectorResult> {
        return coroutineScope {
            connectors.map { connector ->
                async {
                    try {
                        val result = connector.sync()
                        if (result.success && result.metrics.isNotEmpty()) {
                            val athleteId = PreferencesManager.getAthleteId(context)
                            if (athleteId != null) {
                                HealthSyncUploader.uploadMetrics(context, athleteId, result.metrics)
                            }
                        }
                        result
                    } catch (e: Exception) {
                        Log.e(TAG, "Sync fallita per ${connector.type}", e)
                        ConnectorResult(success = false, message = e.message)
                    }
                }
            }.awaitAll()
        }
    }

    suspend fun syncByType(type: ConnectorType): ConnectorResult? {
        val connector = connectors.find { it.type == type }
        return connector?.let {
            try {
                val result = it.sync()
                if (result.success && result.metrics.isNotEmpty()) {
                    val athleteId = PreferencesManager.getAthleteId(context)
                    if (athleteId != null) {
                        HealthSyncUploader.uploadMetrics(context, athleteId, result.metrics)
                    }
                }
                result
            } catch (e: Exception) {
                Log.e(TAG, "Sync fallita per $type", e)
                ConnectorResult(success = false, message = e.message)
            }
        }
    }

    fun getAvailableConnectors(): List<ConnectorType> {
        return connectors.filter { it.isAvailable() }.map { it.type }
    }
}