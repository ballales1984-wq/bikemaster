package com.bikemaster.ui.dashboard

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.bikemaster.R
import com.bikemaster.databinding.ActivityDashboardBinding
import com.bikemaster.network.ApiClient
import com.bikemaster.ui.rides.RideAdapter
import com.bikemaster.ui.rides.RideDetailActivity
import kotlinx.coroutines.launch

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var rideAdapter: RideAdapter

    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, DashboardActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.txtLoading.visibility = android.view.View.VISIBLE
        binding.txtError.visibility = android.view.View.GONE
        binding.layoutSummary.visibility = android.view.View.GONE
        binding.recyclerRides.visibility = android.view.View.GONE

        binding.recyclerRides.layoutManager = LinearLayoutManager(this)

        loadDashboard()
    }

    private fun loadDashboard() {
        lifecycleScope.launch {
            try {
                binding.txtLoading.visibility = android.view.View.VISIBLE
                binding.txtError.visibility = android.view.View.GONE

                val api = ApiClient.getApi(this@DashboardActivity)
                val dashboard = api.getDashboard()

                binding.txtLoading.visibility = android.view.View.GONE
                binding.layoutSummary.visibility = android.view.View.VISIBLE
                binding.recyclerRides.visibility = android.view.View.VISIBLE

                val rides = (dashboard["recent_rides"] as? List<Map<String, Any?>>) ?: emptyList()
                val count = (dashboard["rides_count"] as? Number)?.toInt() ?: rides.size
                val totalDistance = (dashboard["total_distance_km"] as? Number)?.toDouble() ?: 0.0
                val totalDuration = (dashboard["total_duration_minutes"] as? Number)?.toInt() ?: 0
                val avgSpeed = (dashboard["avg_speed_kmh"] as? Number)?.toDouble() ?: 0.0

                binding.txtRidesCount.text = "Uscite: $count"
                binding.txtTotalDistance.text = String.format("Distanza totale: %.1f km", totalDistance)
                binding.txtTotalDuration.text = String.format("Durata totale: %d min", totalDuration)
                binding.txtAvgSpeed.text = String.format("Velocità media: %.1f km/h", avgSpeed)

                val rideList = rides.map { ride ->
                    com.bikemaster.models.Ride(
                        id = (ride["id"] as? Number)?.toInt() ?: 0,
                        date = ride["date"] as? String,
                        distanceKm = (ride["distance_km"] as? Number)?.toDouble() ?: 0.0,
                        durationMinutes = (ride["duration_minutes"] as? Number)?.toDouble() ?: 0.0,
                        avgSpeedKmh = (ride["avg_speed_kmh"] as? Number)?.toDouble() ?: 0.0,
                        calories = (ride["calories"] as? Number)?.toInt() ?: 0,
                        athleteId = (ride["athlete_id"] as? Number)?.toInt()
                    )
                }

                rideAdapter = RideAdapter { ride ->
                    RideDetailActivity.start(this@DashboardActivity, ride)
                }
                rideAdapter.submitList(rideList)
                binding.recyclerRides.adapter = rideAdapter

            } catch (e: Exception) {
                binding.txtLoading.visibility = android.view.View.GONE
                binding.txtError.visibility = android.view.View.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@DashboardActivity, "Errore caricamento dashboard", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
