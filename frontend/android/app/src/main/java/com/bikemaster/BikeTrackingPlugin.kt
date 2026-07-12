package com.bikemaster

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import android.content.Intent
import android.content.Context
import android.content.BroadcastReceiver
import android.content.IntentFilter
import androidx.core.content.ContextCompat

    @CapacitorPlugin(
    name = "BikeTracking",
    permissions = [
        Permission(strings = ["android.permission.ACCESS_COARSE_LOCATION"]),
        Permission(strings = ["android.permission.ACCESS_FINE_LOCATION"]),
        Permission(strings = ["android.permission.ACCESS_BACKGROUND_LOCATION"]),
        Permission(strings = ["android.permission.ACTIVITY_RECOGNITION"]),
        Permission(strings = ["android.permission.POST_NOTIFICATIONS"])
    ]
)
class BikeTrackingPlugin : Plugin() {

    fun startTracking(call: PluginCall) {
        if (BikeTrackingService.isServiceActive()) {
            call.resolve()
            return
        }

        val outputPath = call.getString("outputPath", "")
        val authToken = call.getString("authToken", "")
        val apiBaseUrl = call.getString("apiBaseUrl", "")
        val rideName = call.getString("rideName", "")
        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_START
            putExtra(BikeTrackingService.EXTRA_OUTPUT_PATH, outputPath)
            putExtra(BikeTrackingService.EXTRA_AUTH_TOKEN, authToken)
            putExtra(BikeTrackingService.EXTRA_API_BASE_URL, apiBaseUrl)
            putExtra(BikeTrackingService.EXTRA_RIDE_NAME, rideName)
        }
        ContextCompat.startForegroundService(activity, intent)
        call.resolve()
    }

    fun stopTracking(call: PluginCall) {
        val savedCall = call
        val stopReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                val outputPath = intent?.getStringExtra(BikeTrackingService.EXTRA_OUTPUT_PATH)
                val activities = intent?.getStringExtra(BikeTrackingService.EXTRA_ACTIVITIES)
                val uploadStatus = intent?.getStringExtra(BikeTrackingService.EXTRA_UPLOAD_STATUS)
                val rideId = intent?.getLongExtra(BikeTrackingService.EXTRA_RIDE_ID, -1L)
                val result = JSObject().apply {
                    put("gpxPath", outputPath)
                    put("activities", activities ?: "[]")
                    put("uploadStatus", uploadStatus ?: "unknown")
                    put("rideId", if (rideId != null && rideId >= 0) rideId else null)
                }
                savedCall.resolve(result)
            }
        }
        activity.registerReceiver(stopReceiver, IntentFilter(BikeTrackingService.ACTION_STOPPED))

        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_STOP
        }
        ContextCompat.startForegroundService(activity, intent)
    }

    fun pauseTracking(call: PluginCall) {
        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_PAUSE
        }
        ContextCompat.startForegroundService(activity, intent)
        call.resolve()
    }

    fun resumeTracking(call: PluginCall) {
        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_RESUME
        }
        ContextCompat.startForegroundService(activity, intent)
        call.resolve()
    }

    override fun checkPermissions(call: PluginCall) {
        val granted = ContextCompat.checkSelfPermission(
            activity, android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(
            activity, android.Manifest.permission.ACCESS_COARSE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        val result = JSObject().apply { put("granted", granted) }
        call.resolve(result)
    }
}