package com.bikemaster

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean

class BikeTrackingService : Service(), LocationListener {
    companion object {
        const val CHANNEL_ID = "bikemaster_tracking"
        const val NOTIFICATION_ID = 101
        const val ACTION_START = "com.bikemaster.action.START_TRACKING"
        const val ACTION_PAUSE = "com.bikemaster.action.PAUSE_TRACKING"
        const val ACTION_RESUME = "com.bikemaster.action.RESUME_TRACKING"
        const val ACTION_STOP = "com.bikemaster.action.STOP_TRACKING"
        const val ACTION_STATE = "com.bikemaster.action.TRACKING_STATE"
        const val ACTION_STOPPED = "com.bikemaster.action.TRACKING_STOPPED"
        const val EXTRA_OUTPUT_PATH = "output_path"
        const val EXTRA_ERROR = "error"

        @JvmStatic
        fun startService(context: Context, outputPath: String) {
            val intent = Intent(context, BikeTrackingService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_OUTPUT_PATH, outputPath)
            }
            ContextCompat.startForegroundService(context, intent)
        }

        @JvmStatic
        fun sendActionIntent(context: Context, action: String) {
            val intent = Intent(context, BikeTrackingService::class.java).apply {
                this.action = action
            }
            ContextCompat.startForegroundService(context, intent)
        }

        @JvmStatic
        fun sendStopIntent(context: Context) {
            sendActionIntent(context, ACTION_STOP)
        }

        @JvmStatic
        fun isServiceActive(): Boolean = isTracking.get()
    }

    private val isTracking = AtomicBoolean(false)
    private val isPaused = AtomicBoolean(false)
    private var startTime = 0L
    private var totalDistance = 0.0
    private var gpxFile: File? = null
    private var gpxWriter: FileWriter? = null
    private val trackingPoints = mutableListOf<Location>()
    private lateinit var locationManager: LocationManager

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "BikeMaster Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "GPS tracking for rides"
            }
            (getSystemService(NotificationManager::class.java)).createNotificationChannel(channel)
        }
    }

    private fun createNotification(content: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("BikeMaster")
        .setContentText(content)
        .setSmallIcon(R.drawable.ic_bike_icon)
        .setOngoing(true)
        .build()

    private fun getDefaultFilePath(): String {
        return File(filesDir, "tracks").apply { mkdirs() }.let {
            File(it, "track_${System.currentTimeMillis()}.gpx").absolutePath
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startTracking(intent.getStringExtra(EXTRA_OUTPUT_PATH) ?: getDefaultFilePath())
            ACTION_PAUSE -> pauseTracking()
            ACTION_RESUME -> resumeTracking()
            ACTION_STOP -> stopTrackingAndSave()
        }
        return START_STICKY
    }

    private fun startTracking(outputPath: String) {
        if (isTracking.get()) return

        isTracking.set(true)
        isPaused.set(false)
        startTime = System.currentTimeMillis()
        totalDistance = 0.0
        trackingPoints.clear()

        val file = File(outputPath)
        gpxFile = file
        gpxFile?.parentFile?.mkdirs()
        gpxWriter = FileWriter(file).apply {
            append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            append("<gpx version=\"1.1\" creator=\"BikeMaster-Mobile\" xmlns=\"http://www.topografix.com/GPX/1/1/\">\n")
            append("  <trk>\n")
            append("    <trkseg>\n")
            flush()
        }

        try {
            startForeground(NOTIFICATION_ID, createNotification("Tracking in corso..."))
        } catch (e: Exception) {
            broadcastError(e.message ?: "Impossibile avviare il foreground service")
            stopTrackingAndSave()
            return
        }

        startLocationUpdates()
        broadcastState()
    }

    private fun pauseTracking() {
        if (!isTracking.get()) {
            stopSelf()
            return
        }
        isPaused.set(true)
        updateNotification("Tracking in pausa")
        broadcastState()
    }

    private fun resumeTracking() {
        if (!isTracking.get()) {
            stopSelf()
            return
        }
        isPaused.set(false)
        updateNotification("Tracking in corso...")
        broadcastState()
    }

    private fun stopTrackingAndSave() {
        if (!isTracking.get()) {
            stopSelf()
            return
        }

        isTracking.set(false)
        isPaused.set(false)
        locationManager.removeUpdates(this)

        val outputPath = gpxFile?.absolutePath
        gpxWriter?.let {
            it.append("    </trkseg>\n")
            it.append("  </trk>\n")
            it.append("</gpx>\n")
            it.flush()
            it.close()
        }
        gpxWriter = null

        stopForeground(STOP_FOREGROUND_REMOVE)
        sendBroadcast(Intent(ACTION_STOPPED).apply { putExtra(EXTRA_OUTPUT_PATH, outputPath) })
        stopSelf()
    }

    private fun updateNotification(content: String) {
        val nm = getSystemService(NotificationManager::class.java) as NotificationManager
        nm.notify(NOTIFICATION_ID, createNotification(content))
    }

    private fun startLocationUpdates() {
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION)
            == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                2000L,
                5f,
                this
            )
        }
    }

    private fun updateTracking(location: Location) {
        trackingPoints.add(location)

        if (trackingPoints.size > 1) {
            val prev = trackingPoints[trackingPoints.size - 2]
            totalDistance += calculateDistance(prev, location)
        }

        broadcastState()
        appendToGpx(location)
    }

    private fun appendToGpx(location: Location) {
        gpxWriter?.let {
            val time = dateFormat.format(Date(location.time))
            it.append("      <trkpt lat=\"${location.latitude}\" lon=\"${location.longitude}\">\n")
            it.append("        <ele>${location.altitude}</ele>\n")
            it.append("        <time>$time</time>\n")
            it.append("      </trkpt>\n")
            it.flush()
        }
    }

    private fun broadcastState() {
        sendBroadcast(Intent(ACTION_STATE))
    }

    private fun broadcastError(message: String) {
        Intent(ACTION_STOPPED).apply { putExtra(EXTRA_ERROR, message) }.also {
            sendBroadcast(it)
        }
    }

    private fun calculateDistance(loc1: Location, loc2: Location): Double {
        val results = FloatArray(1)
        Location.distanceBetween(loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude, results)
        return results[0] / 1000.0
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onLocationChanged(location: Location) {
        if (!isTracking.get() || isPaused.get()) return
        updateTracking(location)
    }

    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    override fun onProviderEnabled(provider: String) {}
    override fun onProviderDisabled(provider: String) {}

    override fun onDestroy() {
        locationManager.removeUpdates(this)
        gpxWriter?.close()
        super.onDestroy()
    }
}