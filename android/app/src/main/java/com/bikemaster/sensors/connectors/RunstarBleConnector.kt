package com.bikemaster.sensors.connectors

import android.bluetooth.BluetoothDevice
import android.util.Log
import com.bikemaster.sensors.BleManager
import com.bikemaster.sensors.decoders.RunstarDecoder
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first

class RunstarBleConnector(private val bleManager: BleManager) : Connector {

    override val type: ConnectorType = ConnectorType.BLE_RUNSTAR

    private val discoveredDevices = mutableSetOf<String>()
    private var scanJob: kotlinx.coroutines.Job? = null

    override suspend fun sync(): ConnectorResult {
        return try {
            if (!bleManager.isBluetoothEnabled()) {
                return ConnectorResult(success = false, message = "Bluetooth disattivato")
            }

            val results: List<android.bluetooth.le.ScanResult> = bleManager.startScan().first()
            val runstarDevice = results.find { result ->
                val name = result.scanRecord?.deviceName ?: result.device.name ?: ""
                name.contains("Runstar", ignoreCase = true) ||
                name.contains("Runo", ignoreCase = true) ||
                result.device.address.startsWith("AA:BB", ignoreCase = true)
            }

            if (runstarDevice == null) {
                return ConnectorResult(success = false, message = "Nessuna bilancia Runstar trovata")
            }

            val deviceAddress = runstarDevice.device.address
            Log.i("RunstarBleConnector", "Dispositivo trovato: $deviceAddress")

            val gatt = bleManager.connect(deviceAddress)
            if (gatt == null) {
                return ConnectorResult(success = false, message = "Impossibile connettersi a $deviceAddress")
            }

            delay(1500)

            val weightService = bleManager.getService(deviceAddress, BleManager.WEIGHT_SCALE_SERVICE_UUID)
            if (weightService != null) {
                val characteristic = weightService.getCharacteristic(BleManager.WEIGHT_SCALE_SERVICE_UUID)
                if (characteristic != null) {
                    bleManager.setCharacteristicNotification(deviceAddress, characteristic, true)
                }
            }

            delay(2000)

            val _state: Map<String, Int> = bleManager.connectionState.first { map ->
                map[deviceAddress] == android.bluetooth.BluetoothProfile.STATE_DISCONNECTED
            }

            bleManager.disconnect(deviceAddress)
            ConnectorResult(success = true, message = "Scan Runstar completato", metricsSynced = 1)
        } catch (e: Exception) {
            Log.e("RunstarBleConnector", "Errore sync Runstar", e)
            ConnectorResult(success = false, message = e.message)
        }
    }

    override fun isAvailable(): Boolean {
        return bleManager.isBluetoothEnabled()
    }
}