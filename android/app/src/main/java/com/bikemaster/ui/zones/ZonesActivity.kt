package com.bikemaster.ui.zones

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityZonesBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class ZonesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityZonesBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, ZonesActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityZonesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        loadZones()
    }

    private fun loadZones() {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE

                val api = ApiClient.getApi(this@ZonesActivity)
                val data = api.getZones()

                binding.progress.visibility = ProgressBar.GONE

                val ftp = data["ftp_watts"] as? Number ?: 0
                val maxHr = data["max_hr"] as? Number ?: 0
                binding.txtSummary.text = "FTP: ${ftp}W · FC max: ${maxHr}bpm"

                val power = data["power"] as? Map<String, Any?>
                val hr = data["hr"] as? Map<String, Any?>

                binding.layoutPowerZones.removeAllViews()
                binding.layoutHrZones.removeAllViews()

                power?.get("zones")?.let { zones ->
                    val zonesList = zones as? List<Map<String, Any?>> ?: emptyList()
                    zonesList.forEach { zone ->
                        val label = zone["zone"] as? String ?: ""
                        val zoneLabel = zone["label"] as? String ?: ""
                        val pct = (zone["pct_time"] as? Number)?.toDouble() ?: 0.0
                        val lowerW = zone["lower_w"] as? Number
                        val upperW = zone["upper_w"] as? Number

                        val tv = TextView(this@ZonesActivity)
                        val range = if (lowerW != null && upperW != null) "${lowerW}–${upperW}W" else ""
                        tv.text = "$label $zoneLabel: ${String.format("%.1f", pct)}% $range"
                        tv.setPadding(0, 0, 0, 8)
                        binding.layoutPowerZones.addView(tv)
                    }
                }

                hr?.get("zones")?.let { zones ->
                    val zonesList = zones as? List<Map<String, Any?>> ?: emptyList()
                    zonesList.forEach { zone ->
                        val label = zone["zone"] as? String ?: ""
                        val zoneLabel = zone["label"] as? String ?: ""
                        val pct = (zone["pct_time"] as? Number)?.toDouble() ?: 0.0
                        val lowerBpm = zone["lower_bpm"] as? Number
                        val upperBpm = zone["upper_bpm"] as? Number

                        val tv = TextView(this@ZonesActivity)
                        val range = if (lowerBpm != null && upperBpm != null) "${lowerBpm}–${upperBpm} bpm" else ""
                        tv.text = "$label $zoneLabel: ${String.format("%.1f", pct)}% $range"
                        tv.setPadding(0, 0, 0, 8)
                        binding.layoutHrZones.addView(tv)
                    }
                }

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@ZonesActivity, "Errore caricamento zone", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
