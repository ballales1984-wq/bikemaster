package com.bikemaster.ui.stats

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.databinding.ActivityStatsBinding
import com.bikemaster.models.Ride
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class StatsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStatsBinding

    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, StatsActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        loadStats()
    }

    private fun loadStats() {
        lifecycleScope.launch {
            try {
                val response = ApiClient.getApi(this@StatsActivity).getRides()
                setupStatsText(response.rides)
            } catch (e: Exception) {
                Toast.makeText(this@StatsActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun setupStatsText(rides: List<Ride>) {
        val recent = rides.takeLast(10)
        binding.distanceChart.text = recent.joinToString("\n") { ride ->
            "${ride.date}: ${"%.1f".format(ride.distanceKm)} km"
        }.ifEmpty { "Nessuna attività disponibile" }
        binding.speedChart.text = recent.joinToString("\n") { ride ->
            "${ride.date}: ${"%.1f".format(ride.avgSpeedKmh)} km/h"
        }.ifEmpty { "Nessuna attività disponibile" }
    }
<<<<<<< Updated upstream
}
=======
    
    private fun setupDistanceChart(rides: List<Ride>) {
        val lastTen = rides.takeLast(10)
        val totalDistance = lastTen.sumOf { it.distanceKm }
        binding.distanceChart.text = if (lastTen.isEmpty()) {
            "Nessuna attività disponibile"
        } else {
            "Ultime ${lastTen.size} attività\nDistanza totale: ${String.format("%.1f", totalDistance)} km"
        }
    }
    
    private fun setupSpeedChart(rides: List<Ride>) {
        val lastTen = rides.takeLast(10)
        val avgSpeed = lastTen.map { it.avgSpeedKmh }.takeIf { it.isNotEmpty() }?.average() ?: 0.0
        binding.speedChart.text = if (lastTen.isEmpty()) {
            "Nessuna attività disponibile"
        } else {
            "Ultime ${lastTen.size} attività\nVelocità media: ${String.format("%.1f", avgSpeed)} km/h"
        }
    }
}
>>>>>>> Stashed changes
