package com.bikemaster.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.bikemaster.R
import com.bikemaster.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupNavigation()
    }
    
    private fun setupNavigation() {
        binding.btnRides.setOnClickListener {
            startActivity(android.content.Intent(this, com.bikemaster.ui.rides.RideListActivity::class.java))
        }
        
        binding.btnAthlete.setOnClickListener {
            startActivity(android.content.Intent(this, com.bikemaster.ui.athlete.AthleteProfileActivity::class.java))
        }
        
        binding.btnCoach.setOnClickListener {
            startActivity(android.content.Intent(this, com.bikemaster.ui.coach.CoachActivity::class.java))
        }
        
        binding.btnCalendar.setOnClickListener {
            startActivity(android.content.Intent(this, com.bikemaster.ui.calendar.CalendarActivity::class.java))
        }
        
binding.btnTracking.setOnClickListener {
             // Usa il nuovo foreground service per tracking background
             com.bikemaster.tracking.BikeTrackingService.startService(this, "")
         }
        
        binding.btnStats.setOnClickListener {
            com.bikemaster.ui.stats.StatsActivity.start(this)
        }
        
        binding.btnSettings.setOnClickListener {
            com.bikemaster.ui.settings.SettingsActivity.start(this)
        }
        
        binding.btnLogin.setOnClickListener {
            com.bikemaster.ui.auth.LoginActivity.start(this)
        }
    }
}