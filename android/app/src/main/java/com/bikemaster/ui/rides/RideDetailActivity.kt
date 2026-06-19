package com.bikemaster.ui.rides

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityRideDetailBinding
import com.bikemaster.models.Ride
import com.bikemaster.network.ApiClient
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.GoogleMap
import com.google.android.gms.maps.OnMapReadyCallback
import com.google.android.gms.maps.SupportMapFragment
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.PolylineOptions
import kotlinx.coroutines.launch

class RideDetailActivity : AppCompatActivity(), OnMapReadyCallback {
    
    private lateinit var binding: ActivityRideDetailBinding
    private lateinit var ride: Ride
    private var googleMap: GoogleMap? = null
    
    companion object {
        fun start(activity: Activity, ride: Ride) {
            val intent = Intent(activity, RideDetailActivity::class.java).apply {
                putExtra("ride_id", ride.id)
            }
            activity.startActivity(intent)
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRideDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        val rideId = intent.getIntExtra("ride_id", 0)
        if (rideId > 0) loadRide(rideId)
        setupMap()
    }
    
    private fun loadRide(rideId: Int) {
        lifecycleScope.launch {
            try {
                ride = ApiClient.getApi(this@RideDetailActivity).getRide(rideId)
                displayRide()
            } catch (e: Exception) {
                Toast.makeText(this@RideDetailActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun displayRide() {
        binding.apply {
            nameText.text = ride.name ?: "Ride ${ride.id}"
            dateText.text = ride.date ?: ""
            distanceText.text = "${String.format("%.1f", ride.distanceKm)} km"
            durationText.text = "${String.format("%.0f", ride.durationMinutes)} min"
            speedText.text = "${String.format("%.1f", ride.avgSpeedKmh)} km/h"
            caloriesText.text = "${ride.calories} cal"
            fatigueText.text = "Fatigue: ${ride.fatigueScore ?: "-"}"
        }
    }
    
    private fun setupMap() {
        val mapFragment = supportFragmentManager.findFragmentById(R.id.map) as? SupportMapFragment
        mapFragment?.getMapAsync(this)
    }
    
    override fun onMapReady(map: GoogleMap) {
        googleMap = map
        ride.gpsPoints.takeIf { it.isNotEmpty() }?.let { points ->
            val path = points.map { LatLng(it.lat, it.lon) }
            map.addPolyline(PolylineOptions().addAll(path))
            if (path.isNotEmpty()) {
                map.animateCamera(CameraUpdateFactory.newLatLngZoom(path.first(), 14f))
            }
        }
    }
}