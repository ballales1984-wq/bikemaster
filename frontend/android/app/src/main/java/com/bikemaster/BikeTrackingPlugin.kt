package com.bikemaster

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PluginMethod
import android.content.Intent
import android.content.Context
import android.content.BroadcastReceiver
import android.content.IntentFilter

@CapacitorPlugin(
    name = "BikeTracking",
    permissions = [
        Permission(strings = ["android.permission.ACCESS_COARSE_LOCATION"], description = "GPS location for tracking rides"),
        Permission(strings = ["android.permission.ACCESS_FINE_LOCATION"], description = "Precise GPS location for ride tracking"),
        Permission(strings = ["android.permission.ACCESS_BACKGROUND_LOCATION"], description = "Background GPS for continuous tracking")
    ]
)
class BikeTrackingPlugin : Plugin() {

    @PluginMethod
    fun startTracking(call: PluginCall) {
        if (BikeTrackingService.isServiceActive()) {
            call.resolve()
            return
        }

        val outputPath = call.getString("outputPath", "")
        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_START
            putExtra(BikeTrackingService.EXTRA_OUTPUT_PATH, outputPath)
        }
        android.content.ContextCompat.startForegroundService(activity, intent)
        call.resolve()
    }

    @PluginMethod
    fun stopTracking(call: PluginCall) {
        val savedCall = call
        val stopReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                val outputPath = intent?.getStringExtra(BikeTrackingService.EXTRA_OUTPUT_PATH)
                val result = JSObject().apply { put("gpxPath", outputPath) }
                savedCall.resolve(result)
            }
        }
        activity.registerReceiver(stopReceiver, IntentFilter(BikeTrackingService.ACTION_STOPPED))

        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_STOP
        }
        android.content.ContextCompat.startForegroundService(activity, intent)
    }

    @PluginMethod
    fun pauseTracking(call: PluginCall) {
        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_PAUSE
        }
        android.content.ContextCompat.startForegroundService(activity, intent)
        call.resolve()
    }

    @PluginMethod
    fun resumeTracking(call: PluginCall) {
        val intent = Intent(activity, BikeTrackingService::class.java).apply {
            action = BikeTrackingService.ACTION_RESUME
        }
        android.content.ContextCompat.startForegroundService(activity, intent)
        call.resolve()
    }

    @PluginMethod
    fun checkPermissions(call: PluginCall) {
        val granted = android.content.ContextCompat.checkSelfPermission(
            activity, android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED ||
        android.content.ContextCompat.checkSelfPermission(
            activity, android.Manifest.permission.ACCESS_COARSE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        val result = JSObject().apply { put("granted", granted) }
        call.resolve(result)
    }
}