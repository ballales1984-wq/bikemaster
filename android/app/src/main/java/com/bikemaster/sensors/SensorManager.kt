package com.bikemaster.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager as AndroidSensorManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class SensorManager(private val context: Context) : SensorEventListener {
    
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as AndroidSensorManager
    
    private val _heartRate = MutableStateFlow(0f)
    val heartRate: StateFlow<Float> = _heartRate
    
    private val _acceleration = MutableStateFlow(SensorData(0f, 0f, 0f))
    val acceleration: StateFlow<SensorData> = _acceleration
    
    private val _rotation = MutableStateFlow(SensorData(0f, 0f, 0f))
    val rotation: StateFlow<SensorData> = _rotation
    
    data class SensorData(val x: Float, val y: Float, val z: Float)
    
    fun startSensors() {
        val heartRateSensor = sensorManager.getDefaultSensor(Sensor.TYPE_HEART_RATE)
        if (heartRateSensor != null) {
            sensorManager.registerListener(this, heartRateSensor, AndroidSensorManager.SENSOR_DELAY_NORMAL)
        }
        
        val accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        sensorManager.registerListener(this, accelSensor, AndroidSensorManager.SENSOR_DELAY_NORMAL)
        
        val gyroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        sensorManager.registerListener(this, gyroSensor, AndroidSensorManager.SENSOR_DELAY_NORMAL)
    }
    
    fun stopSensors() {
        sensorManager.unregisterListener(this)
    }
    
    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_HEART_RATE -> _heartRate.value = event.values[0]
            Sensor.TYPE_ACCELEROMETER -> _acceleration.value = SensorData(
                event.values[0], event.values[1], event.values[2]
            )
            Sensor.TYPE_GYROSCOPE -> _rotation.value = SensorData(
                event.values[0], event.values[1], event.values[2]
            )
        }
    }
    
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}