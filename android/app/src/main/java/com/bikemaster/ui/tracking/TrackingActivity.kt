package com.bikemaster.ui.tracking

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.os.Looper
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.bikemaster.R
import com.bikemaster.databinding.ActivityTrackingBinding
import com.google.android.gms.location.*
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.GoogleMap
import com.google.android.gms.maps.OnMapReadyCallback
import com.google.android.gms.maps.SupportMapFragment
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.PolylineOptions
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicReference

class TrackingActivity : AppCompatActivity(), OnMapReadyCallback {
    
    private lateinit var binding: ActivityTrackingBinding
    private lateinit var googleMap: GoogleMap
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    
    private val trackingPoints = mutableListOf<LatLng>()
    private var isTracking = false
    private var startTime = 0L
    private var totalDistance = 0.0
    
    companion object {
        fun start(context: Context) {
            context.startActivity(android.content.Intent(context, TrackingActivity::class.java))
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTrackingBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        setupMap()
        setupButtons()
    }
    
    private fun setupMap() {
        val mapFragment = supportFragmentManager.findFragmentById(R.id.map) as SupportMapFragment
        mapFragment.getMapAsync(this)
    }
    
    private fun setupButtons() {
        binding.btnStart.setOnClickListener { startTracking() }
        binding.btnStop.setOnClickListener { stopTracking() }
        binding.btnSave.setOnClickListener { saveRide() }
    }
    
    private fun startTracking() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) 
            != PackageManager.PERMISSION_GRANTED) {
            requestPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            return
        }
        
        isTracking = true
        startTime = System.currentTimeMillis()
        trackingPoints.clear()
        totalDistance = 0.0
        
        setupLocationCallback()
        startLocationUpdates()
        
        binding.btnStart.isEnabled = false
        binding.btnStop.isEnabled = true
        binding.btnSave.isEnabled = false
    }
    
    private fun stopTracking() {
        isTracking = false
        fusedLocationClient.removeLocationUpdates(locationCallback)
        binding.btnStart.isEnabled = true
        binding.btnStop.isEnabled = false
        binding.btnSave.isEnabled = true
    }
    
    private fun saveRide() {
        stopTracking()
        Toast.makeText(this, "Ride salvato! (${trackingPoints.size} punti)", Toast.LENGTH_SHORT).show()
        finish()
    }
    
    private fun setupLocationCallback() {
        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                if (!isTracking) return
                
                result.lastLocation?.let { location ->
                    updateTracking(location)
                }
            }
        }
    }
    
    private fun startLocationUpdates() {
        val locationRequest = LocationRequest.create().apply {
            interval = 5000
            fastestInterval = 2000
            priority = Priority.PRIORITY_HIGH_ACCURACY
        }
        
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) return
        
        fusedLocationClient.requestLocationUpdates(
            locationRequest,
            locationCallback,
            Looper.getMainLooper()
        )
    }
    
    private fun updateTracking(location: Location) {
        val position = LatLng(location.latitude, location.longitude)
        trackingPoints.add(position)
        
        googleMap.addPolyline(
            PolylineOptions().addAll(trackingPoints).color(getColor(R.color.purple_500))
        )
        
        googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(position, 16f))
        
        // Update stats
        if (trackingPoints.size > 1) {
            totalDistance += calculateDistance(trackingPoints[trackingPoints.size - 2], position)
        }
        
        val duration = (System.currentTimeMillis() - startTime) / 1000 / 60
        val avgSpeed = if (duration > 0) totalDistance / (duration / 60.0) else 0.0
        
        binding.distanceText.text = String.format("%.2f km", totalDistance)
        binding.durationText.text = String.format("%d min", duration)
        binding.speedText.text = String.format("%.1f km/h", avgSpeed)
    }
    
    private fun calculateDistance(p1: LatLng, p2: LatLng): Double {
        val results = FloatArray(1)
        Location.distanceBetween(p1.latitude, p1.longitude, p2.latitude, p2.longitude, results)
        return results[0] / 1000.0
    }
    
    override fun onMapReady(map: GoogleMap) {
        googleMap = map
        googleMap.uiSettings.isZoomControlsEnabled = true
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) 
            == PackageManager.PERMISSION_GRANTED) {
            googleMap.isMyLocationEnabled = true
        }
    }
    
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) startTracking()
        else Toast.makeText(this, "Permesso GPS necessario", Toast.LENGTH_SHORT).show()
    }
}