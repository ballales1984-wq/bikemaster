package com.bikemaster.sensors.connectors

interface Connector {
    val type: ConnectorType
    suspend fun sync(): ConnectorResult
    fun isAvailable(): Boolean
}