package com.bikemaster

import android.app.Application
import android.content.Context
import com.bikemaster.sensors.HealthConnectManager
import com.bikemaster.sensors.connectors.ConnectorManager
import com.bikemaster.sensors.connectors.HealthConnectConnector
import com.bikemaster.utils.PreferencesManager

class BikeMasterApp : Application() {

    lateinit var connectorManager: ConnectorManager
        private set

    override fun onCreate() {
        super.onCreate()
        val healthConnectManager = HealthConnectManager(this)
        connectorManager = ConnectorManager(healthConnectManager, this)
        connectorManager.register(HealthConnectConnector(healthConnectManager))
    }
}