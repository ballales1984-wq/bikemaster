package com.bikemaster.tracking

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import androidx.core.content.ContextCompat
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "BikeTracking")
class BikeTrackingPlugin : Plugin() {

    private var stateReceiver: BroadcastReceiver? = null

    override fun load() {
        registerStateReceiver()
    }

    private fun registerStateReceiver() {
        val filter = IntentFilter().apply {
            addAction(BikeTrackingService.ACTION_STATE)
            addAction(BikeTrackingService.ACTION_STOPPED)
        }
        stateReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                when (intent.action) {
                    BikeTrackingService.ACTION_STATE -> {
                        val state = intent.getSerializableExtra("state") as? TrackingState
                        state?.let {
                            val data = JSObject().apply {
                                put("distance", it.distance)
                                put("currentSpeed", it.currentSpeed)
                                put("avgSpeed", it.avgSpeed)
                                put("elapsedTime", it.elapsedTime)
                                put("elevation", it.elevation)
                                put("points", it.points)
                                put("isPaused", it.isPaused)
                                put("lastLatitude", it.lastLatitude)
                                put("lastLongitude", it.lastLongitude)
                                put("heartRate", it.heartRate ?: JSObject.Null)
                                put("cadence", it.cadence ?: JSObject.Null)
                                put("power", it.power ?: JSObject.Null)
                            }
                            notifyListeners("trackingState", data)
                        }
                    }
                    BikeTrackingService.ACTION_STOPPED -> {
                        val outputPath = intent.getStringExtra(BikeTrackingService.EXTRA_OUTPUT_PATH)
                        val error = intent.getStringExtra(BikeTrackingService.EXTRA_ERROR)
                        val data = JSObject().apply {
                            put("gpxPath", outputPath ?: JSObject.Null)
                            put("error", error ?: JSObject.Null)
                        }
                        notifyListeners("trackingStopped", data)
                    }
                }
            }
        }

        ContextCompat.registerReceiver(
            context.applicationContext,
            stateReceiver,
            filter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
    }

    override fun protectedOnDestroy() {
        stateReceiver?.let {
            context.applicationContext.unregisterReceiver(it)
        }
        stateReceiver = null
        super.protectedOnDestroy()
    }

    @PluginMethod
    fun startTracking(call: PluginCall) {
        val outputPath = call.getString("outputPath") ?: ""
        BikeTrackingService.startService(context, outputPath)
        call.resolve()
    }

    @PluginMethod
    fun stopTracking(call: PluginCall) {
        BikeTrackingService.sendStopIntent(context)
        call.resolve()
    }

    @PluginMethod
    fun pauseTracking(call: PluginCall) {
        BikeTrackingService.sendActionIntent(context, BikeTrackingService.ACTION_PAUSE)
        call.resolve()
    }

    @PluginMethod
    fun resumeTracking(call: PluginCall) {
        BikeTrackingService.sendActionIntent(context, BikeTrackingService.ACTION_RESUME)
        call.resolve()
    }

    @PluginMethod
    fun checkPermissions(call: PluginCall) {
        val fineLocation = ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_FINE_LOCATION)
        val backgroundLocation = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_BACKGROUND_LOCATION)
        } else {
            android.content.pm.PackageManager.PERMISSION_GRANTED
        }

        val data = JSObject().apply {
            put("fineLocation", fineLocation == android.content.pm.PackageManager.PERMISSION_GRANTED)
            put("backgroundLocation", backgroundLocation == android.content.pm.PackageManager.PERMISSION_GRANTED)
            put("granted", fineLocation == android.content.pm.PackageManager.PERMISSION_GRANTED)
        }
        call.resolve(data)
    }
}
