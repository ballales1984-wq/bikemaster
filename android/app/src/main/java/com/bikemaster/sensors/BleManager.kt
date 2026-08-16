package com.bikemaster.sensors

import android.Manifest
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.content.pm.PackageManager
import android.os.ParcelUuid
import android.util.Log
import androidx.core.content.ContextCompat
import com.bikemaster.sensors.decoders.RunstarDecoder
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.*

class BleManager(private val context: Context) {

    companion object {
        private const val TAG = "BleManager"
        val WEIGHT_SCALE_SERVICE_UUID: UUID = UUID.fromString("0000181d-0000-1000-8000-00805f9b34fb")
        val HEART_RATE_SERVICE_UUID: UUID = UUID.fromString("0000180d-0000-1000-8000-00805f9b34fb")
        val CYCLING_SPEED_CADENCE_UUID: UUID = UUID.fromString("00001816-0000-1000-8000-00805f9b34fb")
    }

    private val bluetoothManager: BluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager.adapter
    private var bluetoothLeScanner: BluetoothLeScanner? = null
    private var scanCallback: ScanCallback? = null
    private val gattConnections = mutableMapOf<String, BluetoothGatt>()
    private val _scanResults = MutableStateFlow<List<ScanResult>>(emptyList())
    val scanResults: Flow<List<ScanResult>> = _scanResults.asStateFlow()

    private val _connectionState = MutableStateFlow<Map<String, Int>>(emptyMap())
    val connectionState: Flow<Map<String, Int>> = _connectionState.asStateFlow()

    fun hasBluetoothPermissions(): Boolean {
        val fineLocation = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val scan = ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_SCAN)
        val connect = ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT)
        return fineLocation == PackageManager.PERMISSION_GRANTED &&
               scan == PackageManager.PERMISSION_GRANTED &&
               connect == PackageManager.PERMISSION_GRANTED
    }

    fun isBluetoothEnabled(): Boolean {
        return bluetoothAdapter?.isEnabled ?: false
    }

    fun initialize() {
        bluetoothLeScanner = bluetoothAdapter?.bluetoothLeScanner
    }

    fun startScan(filters: List<ScanFilter>? = null): Flow<List<ScanResult>> {
        val results = mutableListOf<ScanResult>()
        val flow = kotlinx.coroutines.flow.callbackFlow {
            scanCallback = object : ScanCallback() {
                override fun onScanResult(callbackType: Int, result: ScanResult) {
                    results.add(result)
                    _scanResults.value = results.toList()
                    trySend(results.toList())
                }

                override fun onBatchScanResults(scanResults: List<ScanResult>) {
                    scanResults.forEach { results.add(it) }
                    _scanResults.value = results.toList()
                    trySend(results.toList())
                }

                override fun onScanFailed(errorCode: Int) {
                    Log.e(TAG, "Scan failed: $errorCode")
                    close(Throwable("Scan failed: $errorCode"))
                }
            }

            val settings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build()

            bluetoothLeScanner?.startScan(filters, settings, scanCallback)
        }
        return flow
    }

    fun stopScan() {
        val callback = scanCallback
        if (callback != null) {
            bluetoothLeScanner?.stopScan(callback)
            scanCallback = null
        }
    }

    fun connect(address: String): BluetoothGatt? {
        val device = bluetoothAdapter?.getRemoteDevice(address) ?: return null
        val gatt = device.connectGatt(context, false, gattCallback)
        gattConnections[address] = gatt
        _connectionState.value = _connectionState.value + (address to BluetoothProfile.STATE_CONNECTING)
        return gatt
    }

    fun disconnect(address: String) {
        gattConnections[address]?.close()
        gattConnections.remove(address)
        _connectionState.value = _connectionState.value - address
    }

    fun discoverServices(address: String): BluetoothGatt? {
        return gattConnections[address]?.also { gatt ->
            gatt.discoverServices()
        }
    }

    fun getService(address: String, uuid: UUID): BluetoothGattService? {
        return gattConnections[address]?.getService(uuid)
    }

    fun readCharacteristic(address: String, characteristic: BluetoothGattCharacteristic): ByteArray? {
        val gatt = gattConnections[address] ?: return null
        return if (gatt.readCharacteristic(characteristic)) {
            characteristic.value
        } else {
            null
        }
    }

    fun setCharacteristicNotification(address: String, characteristic: BluetoothGattCharacteristic, enable: Boolean) {
        val gatt = gattConnections[address] ?: return
        gatt.setCharacteristicNotification(characteristic, enable)
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            val address = gatt.device.address
            _connectionState.value = _connectionState.value + (address to newState)
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                Log.i(TAG, "Connesso a $address")
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                Log.i(TAG, "Disconnesso da $address")
                gattConnections.remove(address)
                gatt.close()
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            Log.i(TAG, "Servizi scoperti per ${gatt.device.address}: ${gatt.services.size}")
        }

        override fun onCharacteristicRead(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d(TAG, "Letta caratteristica: ${characteristic.uuid} -> ${characteristic.value?.toHexString()}")
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            Log.d(TAG, "Notifica caratteristica: ${characteristic.uuid} -> ${characteristic.value?.toHexString()}")
            val decoded = RunstarDecoder.decode(characteristic.value)
            Log.i(TAG, "Dati decodificati: $decoded")
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            Log.d(TAG, "Scrittura caratteristica ${characteristic.uuid}: $status")
        }
    }

    fun shutdown() {
        stopScan()
        gattConnections.values.forEach { it.close() }
        gattConnections.clear()
    }
}

fun ByteArray.toHexString(): String = joinToString("") { "%02x".format(it) }