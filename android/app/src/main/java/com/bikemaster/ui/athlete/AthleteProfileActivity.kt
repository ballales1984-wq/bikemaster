package com.bikemaster.ui.athlete

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityAthleteProfileBinding
import com.bikemaster.models.AthleteProfile
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class AthleteProfileActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityAthleteProfileBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAthleteProfileBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        loadAthlete()
        setupButtons()
    }
    
    private fun loadAthlete() {
        lifecycleScope.launch {
            try {
                val response = ApiClient.api.getAthletes()
                response.athletes.firstOrNull()?.let { athlete ->
                    displayAthlete(athlete)
                }
            } catch (e: Exception) {
                Toast.makeText(this@AthleteProfileActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun displayAthlete(athlete: AthleteProfile) {
        binding.apply {
            nameInput.setText(athlete.name ?: "")
            levelText.text = athlete.experienceLevel
            weightInput.setText(athlete.weightKg?.toString() ?: "")
            ftpInput.setText(athlete.ftp?.toString() ?: "")
            maxHrInput.setText(athlete.maxHr?.toString() ?: "")
            restingHrInput.setText(athlete.restingHr?.toString() ?: "")
        }
    }
    
    private fun setupButtons() {
        binding.saveButton.setOnClickListener {
            saveAthlete()
        }
    }
    
    private fun saveAthlete() {
        // TODO: Implement save
        Toast.makeText(this, "Saved!", Toast.LENGTH_SHORT).show()
    }
}