package com.bikemaster.ui.itineraries

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
import com.bikemaster.databinding.ActivityItinerariesBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class ItinerariesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityItinerariesBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, ItinerariesActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityItinerariesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        loadItineraries()
    }

    private fun loadItineraries() {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE

                val api = ApiClient.getApi(this@ItinerariesActivity)
                val response = api.getItineraries()

                binding.progress.visibility = ProgressBar.GONE

                val itineraries = response["itineraries"] as? List<Map<String, Any?>> ?: emptyList()

                if (itineraries.isEmpty()) {
                    binding.txtError.visibility = TextView.VISIBLE
                    binding.txtError.text = "Nessun itinerario disponibile"
                    return@launch
                }

                binding.layoutItineraries.removeAllViews()

                itineraries.forEach { itinerary ->
                    val title = itinerary["title"] as? String ?: "Itinerario"
                    val description = itinerary["description"] as? String ?: ""
                    val distance = itinerary["distance_km"] as? Number
                    val elevation = itinerary["elevation_gain_m"] as? Number

                    val tv = TextView(this@ItinerariesActivity)
                    val distanceText = distance?.let { "${it} km" } ?: ""
                    val elevationText = elevation?.let { "${it} m" } ?: ""
                    tv.text = "$title\n$description\n$distanceText $elevationText"
                    tv.setPadding(0, 0, 0, 16)
                    binding.layoutItineraries.addView(tv)
                }

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@ItinerariesActivity, "Errore caricamento itinerari", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
