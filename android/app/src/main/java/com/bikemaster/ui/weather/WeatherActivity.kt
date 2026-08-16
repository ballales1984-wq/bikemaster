package com.bikemaster.ui.weather

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
import com.bikemaster.databinding.ActivityWeatherBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class WeatherActivity : AppCompatActivity() {

    private lateinit var binding: ActivityWeatherBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, WeatherActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWeatherBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnFetch.setOnClickListener {
            val lat = binding.inputLat.text.toString().toDoubleOrNull()
            val lon = binding.inputLon.text.toString().toDoubleOrNull()
            val date = binding.inputDate.text.toString().ifBlank { null }

            if (lat == null || lon == null) {
                Toast.makeText(this, "Inserisci latitudine e longitudine", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            fetchWeather(lat, lon, date)
        }
    }

    private fun fetchWeather(lat: Double, lon: Double, date: String?) {
        binding.progress.visibility = ProgressBar.VISIBLE
        binding.txtError.visibility = TextView.GONE
        binding.txtWeather.visibility = TextView.GONE

        lifecycleScope.launch {
            try {
                val api = ApiClient.getApi(this@WeatherActivity)
                val weather = api.getWeather(lat, lon, date)

                binding.progress.visibility = ProgressBar.GONE
                binding.txtWeather.visibility = TextView.VISIBLE

                val temp = weather["temperature"] as? Number ?: 0
                val feelsLike = weather["feels_like"] as? Number ?: 0
                val humidity = weather["humidity"] as? Number ?: 0
                val wind = weather["wind_speed_kmh"] as? Number ?: 0
                val score = weather["score"] as? Number ?: 0
                val recommendation = weather["recommendation"] as? String ?: ""

                binding.txtWeather.text = """
                    Temperatura: ${temp}°C
                    Feels like: ${feelsLike}°C
                    Umidità: ${humidity}%
                    Vento: ${wind} km/h
                    Score: ${score}/10
                    Consiglio: $recommendation
                """.trimIndent()

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@WeatherActivity, "Errore caricamento meteo", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
