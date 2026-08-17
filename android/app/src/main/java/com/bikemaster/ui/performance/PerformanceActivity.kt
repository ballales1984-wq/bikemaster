package com.bikemaster.ui.performance

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityPerformanceBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class PerformanceActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPerformanceBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, PerformanceActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPerformanceBinding.inflate(layoutInflater)
        setContentView(binding.root)

        loadPerformance()
    }

    private fun loadPerformance() {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE

                val api = ApiClient.getApi(this@PerformanceActivity)
                val response = api.getPerformanceMetrics()

                binding.progress.visibility = ProgressBar.GONE

                val ftp = response["ftp_watts"] as? Number ?: 0
                val np = response["normalized_power"] as? Number ?: 0
                val intensityFactor = response["intensity_factor"] as? Number ?: 0
                val tss = response["tss"] as? Number ?: 0

                binding.txtFtp.text = "FTP: ${ftp} W"
                binding.txtNp.text = "Normalized Power: ${np} W"
                binding.txtIf.text = "Intensity Factor: ${intensityFactor}"
                binding.txtTss.text = "TSS: ${tss}"

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@PerformanceActivity, "Errore caricamento performance", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
