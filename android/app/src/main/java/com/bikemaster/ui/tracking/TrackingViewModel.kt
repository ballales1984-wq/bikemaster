package com.bikemaster.ui.tracking

import android.app.Activity
import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bikemaster.sensors.SensorManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class TrackingViewModel(activity: Activity) : ViewModel() {
    
    private val sensorManager = SensorManager(activity)
    
    private val _currentHeartRate = MutableStateFlow(0f)
    val currentHeartRate = _currentHeartRate.asStateFlow()
    
    private val _cadence = MutableStateFlow(0)
    val cadence = _cadence.asStateFlow()
    
    private val _power = MutableStateFlow(0.0)
    val power = _power.asStateFlow()
    
    fun startSensors() {
        viewModelScope.launch {
            sensorManager.heartRate.collect { rate ->
                _currentHeartRate.value = rate
            }
        }
    }
    
    fun calculateCadence(acceleration: SensorManager.SensorData): Int {
        val magnitude = kotlin.math.sqrt(
            acceleration.x * acceleration.x + 
            acceleration.y * acceleration.y + 
            acceleration.z * acceleration.z
        )
        return if (magnitude > 15) ((magnitude - 15) * 10).toInt() else 0
    }
    
    fun estimatePower(heartRate: Float, weightKg: Float = 75f): Double {
        if (heartRate <= 0) return 0.0
        return (heartRate / 100f * weightKg * 4).toDouble()
    }
}