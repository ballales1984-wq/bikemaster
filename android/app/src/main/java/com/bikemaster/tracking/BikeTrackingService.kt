package com.bikemaster.tracking

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
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
import com.google.android.gms.location.ActivityRecognition
import com.google.android.gms.location.ActivityRecognitionClient
import com.google.android.gms.location.ActivityRecognitionResult
import com.google.android.gms.location.DetectedActivity
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
        const val ACTION_ACTIVITY = "com.bikemaster.action.ACTIVITY_EVENT"
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

        // #230: on-device tracking performance tuning.
        private const val GPX_FLUSH_POINTS = 20
        private const val MAX_ACCURACY_METERS = 80f
        private const val MAX_PLAUSIBLE_SPEED_MPS = 45.0
        private const val GPS_TOLERANCE = 0.00005
    }

    private var fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
    private var activityRecognitionClient: ActivityRecognitionClient? = null
    private var activityPendingIntent: PendingIntent? = null
    private var locationCallback: LocationCallback? = null
    private val isTracking = AtomicBoolean(false)
    private val isPaused = AtomicBoolean(false)
    private var startTime = 0L
    private var totalDistance = 0.0
    private val trackPoints = mutableListOf<GpxPt>()
    private var lastLocation: Location? = null
    private var pointCount = 0
    private val gpxBuffer = StringBuilder()
    private var gpxBufferPoints = 0
    private var samplingBand = -1
    private var gpxFile: File? = null
    private var gpxWriter: FileWriter? = null

    private val _trackingState = MutableStateFlow(TrackingState())
    val trackingState: StateFlow<TrackingState> = _trackingState

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        activityRecognitionClient = ActivityRecognition.getClient(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startTracking(intent.getStringExtra(EXTRA_OUTPUT_PATH) ?: getDefaultFilePath())
            ACTION_PAUSE -> pauseTracking()
            ACTION_RESUME -> resumeTracking()
            ACTION_STOP -> stopTrackingAndSave()
            ACTION_ACTIVITY -> {
                if (ActivityRecognitionResult.hasResult(intent)) {
                    val result = ActivityRecognitionResult.extractResult(intent)
                    handleActivityRecognition(result)
                }
            }
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
        trackPoints.clear()
        lastLocation = null
        pointCount = 0
        gpxBuffer.setLength(0)
        gpxBufferPoints = 0
        samplingBand = -1

        val file = if (outputPath.isNotBlank()) File(outputPath) else File(getDefaultFilePath())
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
        startActivityRecognition()
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
        flushGpx()
        gpxWriter?.let {
            it.append("    </trkseg>\n")
            it.append("  </trk>\n")
            it.append("</gpx>\n")
            it.flush()
            it.close()
        }
        gpxWriter = null
        outputPath?.let { compressAndRewriteGpx(it) }

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

        val speedKmh = if (location.hasSpeed()) location.speed * 3.6 else 0.0

        val elapsedSeconds = ((System.currentTimeMillis() - startTime).coerceAtLeast(0L)) / 1000.0
        val avgSpeed = if (elapsedSeconds > 0) totalDistance / (elapsedSeconds / 3600.0) else 0.0

        _trackingState.value = TrackingState(
            distance = totalDistance,
            currentSpeed = speedKmh,
            avgSpeed = avgSpeed,
            elapsedTime = elapsedSeconds.toLong(),
            elevation = location.altitude,
            points = pointCount,
            isPaused = isPaused.get(),
            lastLatitude = location.latitude,
            lastLongitude = location.longitude
        )

        trackPoints.add(GpxPt(location.latitude, location.longitude, location.altitude, dateFormat.format(Date(location.time))))

        applyAdaptiveSampling(speedKmh)
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
     * stopped (battery). Re-requests Fused updates only when the speed band changes.
     */
    private fun applyAdaptiveSampling(speedKmh: Double) {
        val band = when {
            speedKmh < 5 -> 0
            speedKmh < 25 -> 1
            else -> 2
        }
        if (band == samplingBand || locationCallback == null) return
        samplingBand = band
        val intervalMs = when (band) {
            0 -> 5000L
            1 -> 2000L
            else -> 1000L
        }
        if (ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.ACCESS_FINE_LOCATION
            ) != android.content.pm.PackageManager.PERMISSION_GRANTED
        ) return
        try {
            val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, intervalMs)
                .setMinUpdateIntervalMillis((intervalMs / 2).coerceAtLeast(500L))
                .setMaxUpdateDelayMillis(intervalMs * 2)
                .build()
            fusedLocationClient.removeLocationUpdates(locationCallback!!)
            fusedLocationClient.requestLocationUpdates(
                request,
                locationCallback!!,
                android.os.Looper.getMainLooper()
            )
        } catch (_: Exception) {
            // Keep current update rate if re-request fails.
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

    private fun startActivityRecognition() {
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACTIVITY_RECOGNITION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        val intent = Intent(this, BikeTrackingService::class.java).apply { action = ACTION_ACTIVITY }
        activityPendingIntent = PendingIntent.getService(this, 1, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE)
        activityRecognitionClient?.requestActivityUpdates(5000L, activityPendingIntent!!)
    }

    private fun handleActivityRecognition(result: ActivityRecognitionResult?) {
        val event = result?.mostProbableActivity ?: return
        when (event.type) {
            DetectedActivity.STILL -> considerAutoPause()
            DetectedActivity.ON_BICYCLE, DetectedActivity.IN_VEHICLE, DetectedActivity.ON_FOOT -> considerAutoResume()
            else -> Unit
        }
    }

    private fun considerAutoPause() {
        if (!isTracking.get() || isPaused.get()) return
        val state = _trackingState.value
        if (AutoPausePolicy.shouldPause(state.currentSpeed, DetectedActivity.STILL, false)) {
            pauseTracking()
        }
    }

    private fun considerAutoResume() {
        if (!isTracking.get() || !isPaused.get()) return
        val state = _trackingState.value
        val activityType = if (state.currentSpeed >= 3.0) DetectedActivity.ON_BICYCLE else DetectedActivity.STILL
        if (AutoPausePolicy.shouldPause(state.currentSpeed, activityType, true).not()) {
            resumeTracking()
        }
    }

    private fun stopActivityRecognition() {
        activityPendingIntent?.let {
            activityRecognitionClient?.removeActivityUpdates(it)
            it.cancel()
        }
        activityPendingIntent = null
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
        stopActivityRecognition()
        flushGpx()
        gpxWriter?.close()
        super.onDestroy()
    }

    // ---- On-device GPX compression (#230) ---------------------------------

    private data class GpxPt(val lat: Double, val lon: Double, val ele: Double, val time: String)

    /** Iterative Ramer-Douglas-Peucker (no recursion limit). Mirrors the backend. */
    private fun douglasPeucker(points: List<GpxPt>): List<GpxPt> {
        val n = points.size
        if (n <= 2) return points
        val keep = BooleanArray(n)
        keep[0] = true
        keep[n - 1] = true
        val stack = ArrayDeque<IntRange>()
        stack.add(0..n - 1)
        while (stack.isNotEmpty()) {
            val range = stack.removeLast()
            val start = range.first
            val end = range.last
            if (end <= start + 1) continue
            var maxDist = 0.0
            var index = start + 1
            for (i in start + 1 until end) {
                val d = perpendicularDistance(points[i], points[start], points[end])
                if (d > maxDist) {
                    maxDist = d
                    index = i
                }
            }
            if (maxDist > GPS_TOLERANCE) {
                keep[index] = true
                stack.add(start..index)
                stack.add(index..end)
            }
        }
        return points.filterIndexed { i, _ -> keep[i] }
    }

    private fun perpendicularDistance(p: GpxPt, a: GpxPt, b: GpxPt): Double {
        val dx = b.lon - a.lon
        val dy = b.lat - a.lat
        if (dx == 0.0 && dy == 0.0) return kotlin.math.hypot(p.lat - a.lat, p.lon - a.lon)
        val num = kotlin.math.abs(dy * p.lon - dx * p.lat + b.lon * a.lat - b.lat * a.lon)
        val den = kotlin.math.hypot(dx, dy)
        return if (den == 0.0) 0.0 else num / den
    }

    /** Rewrite the saved GPX with a decimated point set to shrink the upload payload. */
    private fun compressAndRewriteGpx(path: String) {
        if (trackPoints.size <= 2) return
        val simplified = douglasPeucker(trackPoints)
        if (simplified.size >= trackPoints.size) return
        try {
            FileWriter(path).use { w ->
                w.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
                w.append("<gpx version=\"1.1\" creator=\"BikeMaster-Mobile\" xmlns=\"http://www.topografix.com/GPX/1/1/\">\n")
                w.append("  <trk>\n")
                w.append("    <trkseg>\n")
                for (p in simplified) {
                    w.append("      <trkpt lat=\"${p.lat}\" lon=\"${p.lon}\">\n")
                    w.append("        <ele>${p.ele}</ele>\n")
                    w.append("        <time>${p.time}</time>\n")
                    w.append("      </trkpt>\n")
                }
                w.append("    </trkseg>\n")
                w.append("  </trk>\n")
                w.append("</gpx>\n")
            }
        } catch (_: Exception) {
            // Keep the uncompressed GPX if rewrite fails.
        }
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
