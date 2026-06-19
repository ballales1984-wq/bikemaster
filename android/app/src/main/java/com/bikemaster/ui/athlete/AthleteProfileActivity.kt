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
    private var athleteId: Int? = null
    
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
                val response = ApiClient.getApi(this@AthleteProfileActivity).getAthletes()
                response.values.flatten().firstOrNull()?.let { athlete ->
                    athleteId = athlete.id
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
        val currentAthleteId = athleteId
        if (currentAthleteId == null) {
            Toast.makeText(this, "Profilo atleta non caricato", Toast.LENGTH_SHORT).show()
            return
        }

        val profile = AthleteProfile(
            id = currentAthleteId,
            name = binding.nameInput.text.toString().trim(),
            experienceLevel = binding.levelText.text.toString(),
            weightKg = binding.weightInput.text.toString().toFloatOrNull()?.toDouble(),
            ftp = binding.ftpInput.text.toString().toIntOrNull(),
            maxHr = binding.maxHrInput.text.toString().toIntOrNull(),
            restingHr = binding.restingHrInput.text.toString().toIntOrNull(),
        )

        lifecycleScope.launch {
            try {
                ApiClient.getApi(this@AthleteProfileActivity).updateAthlete(currentAthleteId, profile)
                Toast.makeText(this@AthleteProfileActivity, "Profilo salvato", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(this@AthleteProfileActivity, "Errore salvataggio: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}