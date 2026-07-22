package com.bikemaster.sensors.connectors

import android.util.Log
import com.bikemaster.network.ApiClient
import com.bikemaster.sensors.HealthConnectManager
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

class ConnectorManager(private val healthConnectManager: HealthConnectManager) {

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
                        connector.sync()
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
                it.sync()
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