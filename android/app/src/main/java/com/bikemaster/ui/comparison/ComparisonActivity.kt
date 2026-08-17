package com.bikemaster.ui.comparison

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
import com.bikemaster.databinding.ActivityComparisonBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class ComparisonActivity : AppCompatActivity() {

    private lateinit var binding: ActivityComparisonBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, ComparisonActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityComparisonBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnCompare.setOnClickListener {
            val periodDays = binding.inputPeriod.text.toString().toIntOrNull() ?: 30
            loadComparison(periodDays)
        }
    }

    private fun loadComparison(periodDays: Int) {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE

                val api = ApiClient.getApi(this@ComparisonActivity)
                val response = api.getComparison(periodDays)

                binding.progress.visibility = ProgressBar.GONE

                val current = response["current_period"] as? Map<String, Any?> ?: emptyMap()
                val previous = response["previous_period"] as? Map<String, Any?> ?: emptyMap()
                val change = response["change"] as? Map<String, Any?> ?: emptyMap()

                val currentDistance = current["distance_km"] as? Number ?: 0
                val previousDistance = previous["distance_km"] as? Number ?: 0
                val changePct = change["distance_km_pct"] as? Number ?: 0

                binding.txtCurrentDistance.text = "Distanza corrente: ${currentDistance} km"
                binding.txtPreviousDistance.text = "Distanza precedente: ${previousDistance} km"
                binding.txtChange.text = "Variazione: ${changePct}%"

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@ComparisonActivity, "Errore caricamento confronto", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
