package com.bikemaster.ui.maps

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityMapsBinding
import com.bikemaster.network.ApiClient
import com.bikemaster.ui.rides.RideDetailActivity
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.GoogleMap
import com.google.android.gms.maps.OnMapReadyCallback
import com.google.android.gms.maps.SupportMapFragment
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.PolylineOptions
import kotlinx.coroutines.launch

class MapsActivity : AppCompatActivity(), OnMapReadyCallback {

    private lateinit var binding: ActivityMapsBinding
    private var googleMap: GoogleMap? = null

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, MapsActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMapsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val mapFragment = supportFragmentManager.findFragmentById(R.id.map) as? SupportMapFragment
        mapFragment?.getMapAsync(this)
    }

    override fun onMapReady(map: GoogleMap) {
        googleMap = map
        loadRides()
    }

    private fun loadRides() {
        lifecycleScope.launch {
            try {
                val api = ApiClient.getApi(this@MapsActivity)
                val response = api.getRides(page = 1, pageSize = 50)
                val rides = response.rides.filter { it.gpsPoints.isNotEmpty() }

                if (rides.isEmpty()) {
                    Toast.makeText(this@MapsActivity, "Nessuna uscita con GPS disponibile", Toast.LENGTH_SHORT).show()
                    return@launch
                }

                googleMap?.clear()

                val boundsBuilder = com.google.android.gms.maps.model.LatLngBounds.Builder()

                rides.forEach { ride ->
                    val points = ride.gpsPoints.map { LatLng(it.lat, it.lon) }
                    if (points.size >= 2) {
                        googleMap?.addPolyline(
                            PolylineOptions()
                                .addAll(points)
                                .width(8f)
                                .color(resources.getColor(R.color.purple_500, null))
                        )
                        points.forEach { boundsBuilder.include(it) }
                    }
                }

                val bounds = boundsBuilder.build()
                val padding = 100
                googleMap?.animateCamera(CameraUpdateFactory.newLatLngBounds(bounds, padding))

            } catch (e: Exception) {
                Toast.makeText(this@MapsActivity, "Errore caricamento mappe: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
