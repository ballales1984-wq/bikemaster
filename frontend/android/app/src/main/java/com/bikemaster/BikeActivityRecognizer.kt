package com.bikemaster

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import com.google.android.gms.location.ActivityRecognition
import com.google.android.gms.location.ActivityRecognitionResult
import com.google.android.gms.location.ActivityTransition
import com.google.android.gms.location.ActivityTransitionRequest
import com.google.android.gms.location.DetectedActivity
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Detects the user's motion context (still / walking / running / cycling / in vehicle) while
 * tracking a ride (#224).
 *
 * Primary source is the Google Play [ActivityRecognitionClient] (Transition API). If Google Play
 * services are unavailable (e.g. AOSP / offline emulator) the recognizer transparently falls back
 * to a GPS-speed heuristic ([DetectedActivityType.fromSpeed]) so activity is still recorded.
 *
 * Detected segments are accumulated and can be embedded into the ride GPX `<extensions>` block.
 */
class BikeActivityRecognizer(private val context: Context) {

    private val activityClient by lazy { ActivityRecognition.getClient(context) }
    private var pendingIntent: PendingIntent? = null
    private var receiver: BroadcastReceiver? = null

    @Volatile private var usingPlayServices = false
    @Volatile private var heuristicMode = false

    private val segments = CopyOnWriteArrayList<ActivitySegment>()
    @Volatile private var current: ActivitySegment? = null

    private val callbackLock = Any()
    @Volatile private var onActivityChanged: ((DetectedActivityType) -> Unit)? = null

    fun start(intervalMs: Long = 5000L, callback: ((DetectedActivityType) -> Unit)? = null) {
        onActivityChanged = callback
        registerReceiver()
        try {
            val pi = pendingIntent ?: return
            activityClient.requestActivityUpdates(intervalMs, pi)
                .addOnSuccessListener { usingPlayServices = true }
                .addOnFailureListener {
                    usingPlayServices = false
                    heuristicMode = true
                }
        } catch (e: Exception) {
            usingPlayServices = false
            heuristicMode = true
        }
        recordActivity(DetectedActivityType.UNKNOWN, System.currentTimeMillis())
    }

    /** Feed GPS speed (m/s) so the heuristic fallback can update the detected activity. */
    fun onLocationSpeed(speedMps: Float) {
        if (usingPlayServices) return
        heuristicMode = true
        recordActivity(DetectedActivityType.fromSpeed(speedMps), System.currentTimeMillis())
    }

    /** Finalise the open segment; call when the ride stops. */
    fun finalize(nowMs: Long = System.currentTimeMillis()) {
        current?.let {
            if (it.endMs == it.startMs) {
                val idx = segments.indexOf(it)
                if (idx >= 0) segments[idx] = it.copy(endMs = nowMs)
            }
        }
    }

    fun getSegments(): List<ActivitySegment> = segments.toList()

    fun currentActivity(): DetectedActivityType = current?.activity ?: DetectedActivityType.UNKNOWN

    fun isUsingPlayServices(): Boolean = usingPlayServices

    fun stop() {
        try {
            pendingIntent?.let { activityClient.removeActivityUpdates(it) }
        } catch (_: Exception) {
        }
        try {
            receiver?.let { context.unregisterReceiver(it) }
        } catch (_: Exception) {
        }
        receiver = null
        pendingIntent = null
        onActivityChanged = null
    }

    private fun registerReceiver() {
        val action = "${context.packageName}.ACTION_ACTIVITY_RECOGNITION"
        receiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context?, intent: Intent?) {
                val result = ActivityRecognitionResult.extractResult(intent ?: return) ?: return
                val mostProbable = result.mostProbableActivity
                recordActivity(
                    DetectedActivityType.fromGoogleType(mostProbable.type),
                    System.currentTimeMillis()
                )
            }
        }
        context.registerReceiver(receiver, IntentFilter(action))
        pendingIntent = PendingIntent.getBroadcast(
            context,
            0,
            Intent(action),
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            else PendingIntent.FLAG_UPDATE_CURRENT
        )
    }

    private fun recordActivity(activity: DetectedActivityType, nowMs: Long) {
        val prev = current
        if (prev != null && prev.activity == activity) return
        val source = if (usingPlayServices) "play_services" else "speed_heuristic"
        prev?.let {
            val idx = segments.indexOf(it)
            if (idx >= 0) segments[idx] = it.copy(endMs = nowMs)
        }
        val segment = ActivitySegment(activity = activity, startMs = nowMs, source = source)
        segments.add(segment)
        current = segment
        onActivityChanged?.invoke(activity)
    }

    companion object {
        // Transition API request builder kept for documentation / future richer tracking.
        @Suppress("unused")
        fun buildTransitionRequest(): ActivityTransitionRequest {
            val types = listOf(
                DetectedActivity.STILL,
                DetectedActivity.WALKING,
                DetectedActivity.RUNNING,
                DetectedActivity.ON_BICYCLE,
                DetectedActivity.IN_VEHICLE
            )
            val transitions = types.flatMap { type ->
                listOf(
                    ActivityTransition.Builder()
                        .setActivityType(type)
                        .setActivityTransition(ActivityTransition.ACTIVITY_TRANSITION_ENTER)
                        .build(),
                    ActivityTransition.Builder()
                        .setActivityType(type)
                        .setActivityTransition(ActivityTransition.ACTIVITY_TRANSITION_EXIT)
                        .build()
                )
            }
            return ActivityTransitionRequest(transitions)
        }
    }
}
