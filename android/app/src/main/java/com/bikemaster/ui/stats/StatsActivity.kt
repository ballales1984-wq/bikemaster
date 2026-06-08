package com.bikemaster.ui.stats

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityStatsBinding
import com.bikemaster.models.Ride
import com.bikemaster.network.ApiClient
import com.github.mikephil.charting.data.*
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
                setupCharts(response.rides)
            } catch (e: Exception) {
                Toast.makeText(this@StatsActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun setupCharts(rides: List<Ride>) {
        setupDistanceChart(rides)
        setupSpeedChart(rides)
    }
    
    private fun setupDistanceChart(rides: List<Ride>) {
        val entries = rides.takeLast(10).mapIndexed { index, ride ->
            BarEntry(index.toFloat(), ride.distanceKm.toFloat())
        }
        
        val dataSet = BarDataSet(entries, "Distanza (km)").apply {
            color = getColor(R.color.purple_500)
        }
        
        binding.distanceChart.data = BarData(dataSet)
        binding.distanceChart.invalidate()
    }
    
    private fun setupSpeedChart(rides: List<Ride>) {
        val entries = rides.takeLast(10).mapIndexed { index, ride ->
            Entry(index.toFloat(), ride.avgSpeedKmh.toFloat())
        }
        
        val dataSet = LineDataSet(entries, "Velocità (km/h)").apply {
            color = getColor(R.color.teal_200)
            setDrawFilled(true)
        }
        
        binding.speedChart.data = LineData(dataSet)
        binding.speedChart.invalidate()
    }
}