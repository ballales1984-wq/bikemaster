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
import android.os.Handler
import android.os.IBinder
import android.os.Looper
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
        const val CHANNEL_UPLOAD_ID = "bikemaster_uploads"
        const val NOTIFICATION_ID = 101
        const val NOTIFICATION_UPLOAD_ID = 102
        const val ACTION_START = "com.bikemaster.action.START_TRACKING"
        const val ACTION_PAUSE = "com.bikemaster.action.PAUSE_TRACKING"
        const val ACTION_RESUME = "com.bikemaster.action.RESUME_TRACKING"
        const val ACTION_STOP = "com.bikemaster.action.STOP_TRACKING"
        const val ACTION_STATE = "com.bikemaster.action.TRACKING_STATE"
        const val ACTION_STOPPED = "com.bikemaster.action.TRACKING_STOPPED"
        const val EXTRA_OUTPUT_PATH = "output_path"
        const val EXTRA_AUTH_TOKEN = "auth_token"
        const val EXTRA_API_BASE_URL = "api_base_url"
        const val EXTRA_RIDE_NAME = "ride_name"
        const val EXTRA_ERROR = "error"
        const val EXTRA_ACTIVITIES = "activities"
        const val EXTRA_UPLOAD_STATUS = "upload_status"
        const val EXTRA_RIDE_ID = "ride_id"

        private val isTracking = AtomicBoolean(false)
        private val isPaused = AtomicBoolean(false)

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

        // #230: performance tuning for on-device tracking.
        private const val GPX_FLUSH_POINTS = 20          // buffer GPX writes, flush every N points
        private const val MAX_ACCURACY_METERS = 80f      // drop noisy GPS fixes above this accuracy
        private const val MAX_PLAUSIBLE_SPEED_MPS = 45.0 // reject GPS jumps implying > ~162 km/h
    }

    private var startTime = 0L
    private var totalDistance = 0.0
    private var gpxFile: File? = null
    private var gpxWriter: FileWriter? = null
    private var lastLocation: Location? = null
    private var pointCount = 0
    private val gpxBuffer = StringBuilder()
    private var gpxBufferPoints = 0
    private var samplingBand = -1
    private lateinit var locationManager: LocationManager

    private var recognizer: BikeActivityRecognizer? = null
    private var authToken: String? = null
    private var apiBaseUrl: String? = null
    private var rideName: String? = null

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        createUploadChannel()
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

    private fun createUploadChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_UPLOAD_ID,
                "BikeMaster Uploads",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Ride upload completion notifications"
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
            ACTION_START -> startTracking(
                outputPath = intent.getStringExtra(EXTRA_OUTPUT_PATH) ?: getDefaultFilePath(),
                authToken = intent.getStringExtra(EXTRA_AUTH_TOKEN),
                apiBaseUrl = intent.getStringExtra(EXTRA_API_BASE_URL),
                rideName = intent.getStringExtra(EXTRA_RIDE_NAME)
            )
            ACTION_PAUSE -> pauseTracking()
            ACTION_RESUME -> resumeTracking()
            ACTION_STOP -> stopTrackingAndSave()
        }
        return START_STICKY
    }

    private fun startTracking(outputPath: String, authToken: String?, apiBaseUrl: String?, rideName: String?) {
        if (isTracking.get()) return

        this.authToken = authToken
        this.apiBaseUrl = apiBaseUrl
        this.rideName = rideName

        isTracking.set(true)
        isPaused.set(false)
        startTime = System.currentTimeMillis()
        totalDistance = 0.0
        lastLocation = null
        pointCount = 0
        gpxBuffer.setLength(0)
        gpxBufferPoints = 0
        samplingBand = -1

        // #225: retry any rides that failed to upload while offline (background thread)
        if (!apiBaseUrl.isNullOrBlank()) {
            Thread { RideUploader.flushPending(this) }.start()
        }

        // #224: activity recognition (Play Services + speed heuristic fallback)
        recognizer = BikeActivityRecognizer(this).also {
            it.start(intervalMs = 5000L) { activity ->
                updateNotification("Tracking — ${activity.label}")
            }
        }

        val file = File(outputPath)
        gpxFile = file
        gpxFile?.parentFile?.mkdirs()
        gpxWriter = FileWriter(file).apply {
            append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            append("<gpx version=\"1.1\" creator=\"BikeMaster-Mobile\" xmlns=\"http://www.topografix.com/GPX/1/1/\" ")
            append("xmlns:bikemaster=\"https://bikemaster.app/ns\">\n")
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
        recognizer?.onLocationSpeed(0f)
        flushGpx()
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
        recognizer?.finalize()
        recognizer?.stop()
        val segments = recognizer?.getSegments() ?: emptyList()
        recognizer = null

        flushGpx()
        val outputPath = gpxFile?.absolutePath
        gpxWriter?.let {
            it.append("    </trkseg>\n")
            it.append(GpxExtensions.buildActivityExtensionsXml(segments))
            it.append("  </trk>\n")
            it.append("</gpx>\n")
            it.flush()
            it.close()
        }
        gpxWriter = null

        stopForeground(STOP_FOREGROUND_REMOVE)

        val activitiesJson = GpxExtensions.segmentsToJson(segments)
        // #225: automatic upload to the backend instead of local-only storage (background thread)
        if (outputPath != null && !apiBaseUrl.isNullOrBlank()) {
            val file = File(outputPath)
            Thread {
                RideUploader.uploadRide(this, file, apiBaseUrl!!, authToken, rideName) { result ->
                    Handler(Looper.getMainLooper()).post {
                        notifyUploadResult(result)
                        sendBroadcast(
                            Intent(ACTION_STOPPED).apply {
                                putExtra(EXTRA_OUTPUT_PATH, outputPath)
                                putExtra(EXTRA_ACTIVITIES, activitiesJson)
                                putExtra(EXTRA_UPLOAD_STATUS, if (result.success) "success" else "error")
                                putExtra(EXTRA_RIDE_ID, result.rideId ?: -1L)
                            }
                        )
                    }
                }
            }.start()
        } else {
            sendBroadcast(
                Intent(ACTION_STOPPED).apply {
                    putExtra(EXTRA_OUTPUT_PATH, outputPath)
                    putExtra(EXTRA_ACTIVITIES, activitiesJson)
                    putExtra(EXTRA_UPLOAD_STATUS, "skipped")
                }
            )
        }
        stopSelf()
    }

    // #226: local completion push notification (success / error)
    private fun notifyUploadResult(result: RideUploader.UploadResult) {
        val (title, text) = if (result.success) {
            "Upload completato" to "La tua uscita è stata salvata${result.rideId?.let { " (ID $it)" } ?: ""}."
        } else {
            "Upload fallito" to result.message
        }
        val notification = NotificationCompat.Builder(this, CHANNEL_UPLOAD_ID)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setSmallIcon(R.drawable.ic_bike_icon)
            .setAutoCancel(true)
            .build()
        (getSystemService(NotificationManager::class.java))
            .notify(NOTIFICATION_UPLOAD_ID, notification)
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
        // #230: drop low-accuracy fixes so the recorded track stays clean (beats naive logging).
        if (location.accuracy > 0f && location.accuracy > MAX_ACCURACY_METERS) return

        val prev = lastLocation
        if (prev != null) {
            val dist = calculateDistance(prev, location)
            val dt = (location.time - prev.time) / 1000.0
            // Reject GPS jumps that imply an impossible speed (outlier rejection).
            if (dt > 0 && dist / dt > MAX_PLAUSIBLE_SPEED_MPS) return
            totalDistance += dist
        }
        lastLocation = location
        pointCount++

        // #224: feed GPS speed to the activity recognizer (used by the heuristic fallback)
        if (location.hasSpeed()) {
            recognizer?.onLocationSpeed(location.speed)
        }

        applyAdaptiveSampling(if (location.hasSpeed()) location.speed * 3.6 else 0.0)

        broadcastState()
        appendToGpx(location)
    }

    private fun appendToGpx(location: Location) {
        val time = dateFormat.format(Date(location.time))
        gpxBuffer.append("      <trkpt lat=\"${location.latitude}\" lon=\"${location.longitude}\">\n")
        gpxBuffer.append("        <ele>${location.altitude}</ele>\n")
        gpxBuffer.append("        <time>$time</time>\n")
        gpxBuffer.append("      </trkpt>\n")
        if (++gpxBufferPoints >= GPX_FLUSH_POINTS) flushGpx()
    }

    private fun flushGpx() {
        if (gpxBufferPoints == 0) return
        gpxWriter?.append(gpxBuffer)
        gpxWriter?.flush()
        gpxBuffer.setLength(0)
        gpxBufferPoints = 0
    }

    /**
     * #230: adaptive GPS sampling. Faster fixes when moving (accuracy), slower when
     * stopped (battery). Re-requests updates only when the speed band actually changes.
     */
    private fun applyAdaptiveSampling(speedKmh: Double) {
        val band = when {
            speedKmh < 5 -> 0
            speedKmh < 25 -> 1
            else -> 2
        }
        if (band == samplingBand) return
        samplingBand = band
        val intervalMs = when (band) {
            0 -> 5000L
            1 -> 2000L
            else -> 1000L
        }
        if (ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.ACCESS_FINE_LOCATION
            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            try {
                locationManager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER,
                    intervalMs,
                    5f,
                    this
                )
            } catch (_: Exception) {
                // Keep the current update rate if re-request fails.
            }
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
        flushGpx()
        gpxWriter?.close()
        recognizer?.stop()
        super.onDestroy()
    }
}
