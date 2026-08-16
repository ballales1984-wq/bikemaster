package com.bikemaster.ui.heatmap

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityHeatmapBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class HeatmapActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHeatmapBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, HeatmapActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHeatmapBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnLoad.setOnClickListener {
            val athleteId = binding.inputAthleteId.text.toString().toIntOrNull()
            if (athleteId == null) {
                Toast.makeText(this, "Inserisci un Athlete ID valido", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            loadHeatmap(athleteId)
        }
    }

    private fun loadHeatmap(athleteId: Int) {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE

                val api = ApiClient.getApi(this@HeatmapActivity)
                val response = api.getHeatmap(athleteId)

                binding.progress.visibility = ProgressBar.GONE

                val points = response["points"] as? List<Map<String, Any?>> ?: emptyList()
                val totalPoints = response["total_points"] as? Number ?: points.size

                binding.txtStats.visibility = TextView.VISIBLE
                binding.txtStats.text = "Punti GPS totali: $totalPoints · Celle heatmap: ${points.size}"

                if (points.isEmpty()) {
                    binding.txtError.visibility = TextView.VISIBLE
                    binding.txtError.text = "Nessun dato heatmap disponibile"
                }

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@HeatmapActivity, "Errore caricamento heatmap", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
