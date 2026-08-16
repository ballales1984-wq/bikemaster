package com.bikemaster.ui.tracking

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityTrackingBinding
import com.bikemaster.network.ApiClient
import com.bikemaster.sensors.SensorManager
import com.bikemaster.tracking.BikeTrackingService
import com.bikemaster.tracking.TrackingState
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.GoogleMap
import com.google.android.gms.maps.OnMapReadyCallback
import com.google.android.gms.maps.SupportMapFragment
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.Polyline
import com.google.android.gms.maps.model.PolylineOptions
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class TrackingActivity : AppCompatActivity(), OnMapReadyCallback {

    private lateinit var binding: ActivityTrackingBinding
    private lateinit var googleMap: GoogleMap
    private lateinit var sensorManager: SensorManager
    private val trackingPoints = mutableListOf<LatLng>()
    private var polyline: Polyline? = null
    private var currentOutputPath: String? = null

    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, TrackingActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTrackingBinding.inflate(layoutInflater)
        setContentView(binding.root)

        sensorManager = SensorManager(this)
        setupMap()
        setupButtons()
        registerReceiver()
    }

    private fun setupButtons() {
        binding.btnStart.setOnClickListener { startTracking() }
        binding.btnStop.setOnClickListener { stopTracking() }
        binding.btnPause.setOnClickListener { pauseTracking() }
        binding.btnSave.setOnClickListener { saveRide() }
        binding.btnSensors.setOnClickListener { toggleSensors() }
    }

    private fun toggleSensors() {
        if (binding.sensorPanel.visibility == android.view.View.VISIBLE) {
            sensorManager.stopSensors()
            binding.sensorPanel.visibility = android.view.View.GONE
        } else {
            sensorManager.startSensors()
            binding.sensorPanel.visibility = android.view.View.VISIBLE
        }
    }

    private fun setupMap() {
        val mapFragment = supportFragmentManager.findFragmentById(R.id.map) as SupportMapFragment
        mapFragment.getMapAsync(this)
    }

    private fun startTracking() {
        if (!hasPermission(Manifest.permission.ACCESS_FINE_LOCATION)) {
            requestFineLocationLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            return
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && !hasPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION)) {
            requestBackgroundLocationLauncher.launch(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
            return
        }

        currentOutputPath = getDefaultFilePath()
        BikeTrackingService.startService(this, currentOutputPath ?: return)
        binding.btnStart.isEnabled = false
        binding.btnStop.isEnabled = true
        binding.btnPause.isEnabled = true
        binding.btnSave.isEnabled = false
    }

    private fun stopTracking() {
        BikeTrackingService.sendStopIntent(this)
        binding.btnStop.isEnabled = false
    }

    fun pauseTracking() {
        BikeTrackingService.sendActionIntent(this, BikeTrackingService.ACTION_PAUSE)
        binding.btnPause.isEnabled = false
    }

    fun resumeTracking() {
        BikeTrackingService.sendActionIntent(this, BikeTrackingService.ACTION_RESUME)
        binding.btnPause.isEnabled = true
    }

    private fun saveRide() {
        val outputPath = currentOutputPath
        if (outputPath == null) {
            Toast.makeText(this, "Nessun file GPX da caricare", Toast.LENGTH_SHORT).show()
            return
        }
        uploadRide(File(outputPath))
    }

    private fun uploadRide(file: File) {
        binding.btnSave.isEnabled = false
        Toast.makeText(this, "Caricamento uscita in corso...", Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            try {
                val requestBody = file.asRequestBody("application/gpx+xml".toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", file.name, requestBody)
                ApiClient.getApi(this@TrackingActivity).importGpx(part)
                Toast.makeText(this@TrackingActivity, "Uscita caricata con successo", Toast.LENGTH_SHORT).show()
                binding.btnSave.isEnabled = true
            } catch (error: Exception) {
                Toast.makeText(this@TrackingActivity, "Errore caricamento: ${error.message}", Toast.LENGTH_LONG).show()
                binding.btnSave.isEnabled = true
            }
        }
    }

    private fun registerReceiver() {
        val filter = IntentFilter().apply {
            addAction(BikeTrackingService.ACTION_STATE)
            addAction(BikeTrackingService.ACTION_STOPPED)
        }
        ContextCompat.registerReceiver(
            this,
            trackingReceiver,
            filter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
    }

    private val trackingReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                BikeTrackingService.ACTION_STATE -> {
                    @Suppress("DEPRECATION")
                    val state = intent.getSerializableExtra("state") as? TrackingState
                    state?.let { updateUi(it) }
                }
                BikeTrackingService.ACTION_STOPPED -> {
                    intent.getStringExtra(BikeTrackingService.EXTRA_ERROR)?.let { error ->
                        Toast.makeText(this@TrackingActivity, error, Toast.LENGTH_LONG).show()
                    }
                    val outputPath = intent.getStringExtra(BikeTrackingService.EXTRA_OUTPUT_PATH)
                    if (!outputPath.isNullOrEmpty()) {
                        currentOutputPath = outputPath
                        binding.btnSave.isEnabled = true
                        Toast.makeText(this@TrackingActivity, "Tracciamento completato", Toast.LENGTH_SHORT).show()
                    }
                    binding.btnStart.isEnabled = true
                    binding.btnStop.isEnabled = false
                    binding.btnPause.isEnabled = false
                    binding.btnPause.text = "Pausa"
                }
            }
        }
    }

    private fun updateUi(state: TrackingState) {
        binding.distanceText.text = String.format("%.2f km", state.distance)
        binding.durationText.text = formatDuration(state.elapsedTime)
        binding.speedText.text = String.format("%.1f km/h", state.avgSpeed)
        binding.btnPause.text = if (state.isPaused) "Riprendi" else "Pausa"
        state.heartRate?.let { binding.heartRateText.text = it.toString() }
        state.cadence?.let { binding.cadenceText.text = it.toString() }
        state.power?.let { binding.powerText.text = it.toString() }

        val latest = trackingPoints.lastOrNull()
        if (::googleMap.isInitialized && latest != null) {
            googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(latest, 16f))
        }
        if (::googleMap.isInitialized && state.lastLatitude != null && state.lastLongitude != null) {
            addPoint(state.lastLatitude, state.lastLongitude)
        }
    }

    private fun formatDuration(seconds: Long): String {
        val hours = seconds / 3600
        val minutes = (seconds % 3600) / 60
        val remainingSeconds = seconds % 60
        return if (hours > 0) {
            String.format("%02d:%02d:%02d", hours, minutes, remainingSeconds)
        } else {
            String.format("%02d:%02d", minutes, remainingSeconds)
        }
    }

    private fun addPoint(lat: Double, lon: Double) {
        val point = LatLng(lat, lon)
        trackingPoints.add(point)
        polyline = if (polyline == null) {
            googleMap.addPolyline(
                PolylineOptions().add(point).color(getColor(R.color.purple_500)).width(8f)
            )
        } else {
            val points = polyline?.points?.toMutableList() ?: mutableListOf()
            points.add(point)
            polyline?.points = points
            polyline
        }
    }

    private fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED
    }

    private fun getDefaultFilePath(): String {
        val tracksDir = File(filesDir, "tracks").apply { mkdirs() }
        return File(tracksDir, "track_${System.currentTimeMillis()}.gpx").absolutePath
    }

    private val requestFineLocationLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) startTracking() else Toast.makeText(this, "Permesso GPS necessario", Toast.LENGTH_SHORT).show()
    }

    private val requestBackgroundLocationLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) startTracking() else Toast.makeText(this, "Permesso posizione in background negato", Toast.LENGTH_SHORT).show()
    }

    override fun onMapReady(map: GoogleMap) {
        googleMap = map
        googleMap.uiSettings.isZoomControlsEnabled = true
        if (hasPermission(Manifest.permission.ACCESS_FINE_LOCATION)) {
            googleMap.isMyLocationEnabled = true
        }
    }

    override fun onDestroy() {
        unregisterReceiver(trackingReceiver)
        sensorManager.stopSensors()
        super.onDestroy()
    }
}
