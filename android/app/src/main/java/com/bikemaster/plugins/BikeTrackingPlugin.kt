package com.bikemaster.plugins

import com.bikemaster.tracking.BikeTrackingService
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission

@CapacitorPlugin(
    name = "BikeTracking",
    permissions = [
        Permission(strings = ["android.permission.ACCESS_FINE_LOCATION"], description = "GPS location for ride tracking"),
        Permission(strings = ["android.permission.ACCESS_BACKGROUND_LOCATION"], description = "Background location for continuous tracking"),
        Permission(strings = ["android.permission.ACTIVITY_RECOGNITION"], description = "Activity recognition for auto-pause")
    ]
)
class BikeTrackingPlugin : Plugin() {

    private var outputPath: String? = null

    @PluginMethod
    fun startTracking(call: PluginCall) {
        val context = activity
        outputPath = call.getString("outputPath")
        BikeTrackingService.startService(context, outputPath ?: "")
        call.resolve()
    }

    @PluginMethod
    fun stopTracking(call: PluginCall) {
        val context = activity
        BikeTrackingService.sendStopIntent(context)
        call.resolve()
    }

    @PluginMethod
    fun pauseTracking(call: PluginCall) {
        sendAction(call, BikeTrackingService.ACTION_PAUSE)
    }

    @PluginMethod
    fun resumeTracking(call: PluginCall) {
        sendAction(call, BikeTrackingService.ACTION_RESUME)
    }

    @PluginMethod
    fun checkPermissions(call: PluginCall) {
        val fineLocation = android.content.pm.PackageManager.PERMISSION_GRANTED
        call.resolve(
            JSObject().apply {
                put("granted", fineLocation == android.content.pm.PackageManager.PERMISSION_GRANTED)
            }
        )
    }

    private fun sendAction(call: PluginCall, action: String) {
        val context = activity
        BikeTrackingService.sendActionIntent(context, action)
        call.resolve()
    }
}
