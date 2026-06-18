package com.bikemaster.tracking

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.bikemaster.R
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean

class BikeTrackingService : Service() {

    companion object {
        const val CHANNEL_ID = "bike_tracking_channel"
        const val NOTIFICATION_ID = 101
        const val ACTION_START = "com.bikemaster.action.START_TRACKING"
        const val ACTION_PAUSE = "com.bikemaster.action.PAUSE_TRACKING"
        const val ACTION_RESUME = "com.bikemaster.action.RESUME_TRACKING"
        const val ACTION_STOP = "com.bikemaster.action.STOP_TRACKING"
        const val ACTION_STATE = "com.bikemaster.action.TRACKING_STATE"
        const val ACTION_STOPPED = "com.bikemaster.action.TRACKING_STOPPED"
        const val EXTRA_OUTPUT_PATH = "output_path"
        const val EXTRA_ERROR = "error"

        fun startService(context: Context, outputPath: String) {
            val intent = Intent(context, BikeTrackingService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_OUTPUT_PATH, outputPath)
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun sendActionIntent(context: Context, action: String) {
            val intent = Intent(context, BikeTrackingService::class.java).apply {
                this.action = action
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun sendStopIntent(context: Context) {
            sendActionIntent(context, ACTION_STOP)
        }
    }

    private var fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
    private var locationCallback: LocationCallback? = null
    private val isTracking = AtomicBoolean(false)
    private val isPaused = AtomicBoolean(false)
    private var startTime = 0L
    private var totalDistance = 0.0
    private val trackingPoints = mutableListOf<Location>()
    private var gpxFile: File? = null
    private var gpxWriter: FileWriter? = null

    private val _trackingState = MutableStateFlow(TrackingState())
    val trackingState: StateFlow<TrackingState> = _trackingState

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
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

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Bike Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Tracciamento GPS in tempo reale"
                setShowBadge(false)
            }
            (getSystemService(NotificationManager::class.java)).createNotificationChannel(channel)
        }
    }

    private fun getDefaultFilePath(): String {
        val tracksDir = File(filesDir, "tracks").apply { mkdirs() }
        return File(tracksDir, "track_${System.currentTimeMillis()}.gpx").absolutePath
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
            val notification = createNotification("Tracking in corso...")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification)
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (error: Exception) {
            broadcastError(error.message ?: "Impossibile avviare il foreground service")
            stopTrackingAndSave()
            return
        }

        startLocationUpdates()
        broadcastState()
    }

    private fun pauseTracking() {
        if (!isTracking.get()) return
        isPaused.set(true)
        updateNotification("Tracking in pausa")
        broadcastState()
    }

    private fun resumeTracking() {
        if (!isTracking.get()) return
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
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
        locationCallback = null

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
        sendBroadcast(
            Intent(ACTION_STOPPED).apply {
                putExtra(EXTRA_OUTPUT_PATH, outputPath)
            }
        )
        stopSelf()
    }

    private fun createNotification(content: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("BikeMaster")
        .setContentText(content)
        .setSmallIcon(R.drawable.ic_bike_icon)
        .setOngoing(true)
        .build()

    private fun updateNotification(content: String) {
        val nm = getSystemService(NotificationManager::class.java) as NotificationManager
        nm.notify(NOTIFICATION_ID, createNotification(content))
    }

    private fun startLocationUpdates() {
        val locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 2000L)
            .setMinUpdateIntervalMillis(1000L)
            .setMaxUpdateDelayMillis(5000L)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                if (!isTracking.get() || isPaused.get()) return
                result.lastLocation?.let { location ->
                    updateTracking(location)
                }
            }
        }

        if (ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        fusedLocationClient.requestLocationUpdates(
            locationRequest,
            locationCallback!!,
            android.os.Looper.getMainLooper()
        )
    }

    private fun updateTracking(location: Location) {
        trackingPoints.add(location)

        val speedKmh = if (location.hasSpeed()) location.speed * 3.6 else 0.0
        if (trackingPoints.size > 1) {
            val prev = trackingPoints[trackingPoints.size - 2]
            totalDistance += calculateDistance(prev, location)
        }

        val elapsedSeconds = ((System.currentTimeMillis() - startTime).coerceAtLeast(0L)) / 1000.0
        val avgSpeed = if (elapsedSeconds > 0) totalDistance / (elapsedSeconds / 3600.0) else 0.0

        _trackingState.value = TrackingState(
            distance = totalDistance,
            currentSpeed = speedKmh,
            avgSpeed = avgSpeed,
            elapsedTime = elapsedSeconds.toLong(),
            elevation = location.altitude,
            points = trackingPoints.size,
            isPaused = isPaused.get(),
            lastLatitude = location.latitude,
            lastLongitude = location.longitude
        )
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
        sendBroadcast(
            Intent(ACTION_STATE).apply {
                putExtra("state", _trackingState.value)
            }
        )
    }

    private fun broadcastError(message: String) {
        sendBroadcast(
            Intent(ACTION_STOPPED).apply {
                putExtra(EXTRA_ERROR, message)
            }
        )
    }

    private fun calculateDistance(loc1: Location, loc2: Location): Double {
        val results = FloatArray(1)
        Location.distanceBetween(
            loc1.latitude, loc1.longitude,
            loc2.latitude, loc2.longitude,
            results
        )
        return results[0] / 1000.0
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
        gpxWriter?.close()
        super.onDestroy()
    }
}

data class TrackingState(
    val distance: Double = 0.0,
    val currentSpeed: Double = 0.0,
    val avgSpeed: Double = 0.0,
    val elapsedTime: Long = 0L,
    val elevation: Double = 0.0,
    val points: Int = 0,
    val isPaused: Boolean = false,
    val lastLatitude: Double? = null,
    val lastLongitude: Double? = null,
    val heartRate: Int? = null,
    val cadence: Int? = null,
    val power: Int? = null
) : java.io.Serializable
