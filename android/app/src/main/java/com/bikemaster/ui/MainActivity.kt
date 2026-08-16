package com.bikemaster.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.bikemaster.R
import com.bikemaster.ui.athlete.AthleteProfileActivity
import com.bikemaster.ui.auth.LoginActivity
import com.bikemaster.ui.calendar.CalendarActivity
import com.bikemaster.ui.coach.CoachActivity
import com.bikemaster.ui.dashboard.DashboardActivity
import com.bikemaster.ui.imports.ImportActivity
import com.bikemaster.ui.maps.MapsActivity
import com.bikemaster.ui.rides.RideListActivity
import com.bikemaster.ui.weather.WeatherActivity
import com.bikemaster.ui.zones.ZonesActivity
import com.bikemaster.ui.badges.BadgesActivity
import com.bikemaster.ui.heatmap.HeatmapActivity
import com.bikemaster.ui.settings.SettingsActivity
import com.bikemaster.ui.stats.StatsActivity
import com.bikemaster.ui.tracking.TrackingActivity
import com.bikemaster.utils.PreferencesManager

class MainActivity : AppCompatActivity() {

    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, MainActivity::class.java))
        }
    }

    private lateinit var navSpinner: Spinner
    private lateinit var btnDashboard: Button
    private lateinit var btnImport: Button
    private lateinit var btnWeather: Button
    private lateinit var btnMaps: Button
    private lateinit var btnZones: Button
    private lateinit var btnBadges: Button
    private lateinit var btnHeatmap: Button
    private lateinit var btnRides: Button
    private lateinit var btnTracking: Button
    private lateinit var btnStats: Button
    private lateinit var btnAthlete: Button
    private lateinit var btnCoach: Button
    private lateinit var btnCalendar: Button
    private lateinit var btnLogin: Button
    private lateinit var btnSettings: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!isUserLoggedIn()) {
            LoginActivity.start(this)
            finish()
            return
        }

        setContentView(R.layout.activity_main)

        navSpinner = findViewById(R.id.nav_spinner)
        btnDashboard = findViewById(R.id.btn_dashboard)
        btnImport = findViewById(R.id.btn_import)
        btnWeather = findViewById(R.id.btn_weather)
        btnMaps = findViewById(R.id.btn_maps)
        btnZones = findViewById(R.id.btn_zones)
        btnBadges = findViewById(R.id.btn_badges)
        btnHeatmap = findViewById(R.id.btn_heatmap)
        btnRides = findViewById(R.id.btn_rides)
        btnTracking = findViewById(R.id.btn_tracking)
        btnStats = findViewById(R.id.btn_stats)
        btnAthlete = findViewById(R.id.btn_athlete)
        btnCoach = findViewById(R.id.btn_coach)
        btnCalendar = findViewById(R.id.btn_calendar)
        btnLogin = findViewById(R.id.btn_login)
        btnSettings = findViewById(R.id.btn_settings)

        setupNavigationSpinner()
        setupButtons()
        updateLoginButton()
    }

    private fun isUserLoggedIn(): Boolean {
        return !PreferencesManager.getAuthToken(this).isNullOrBlank()
    }

    private fun setupNavigationSpinner() {
        val routes = resources.getStringArray(R.array.nav_routes)
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, routes)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        navSpinner.adapter = adapter

        navSpinner.setOnItemSelectedListener(object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: android.widget.AdapterView<*>,
                view: android.view.View?,
                position: Int,
                id: Long
            ) {
                when (routes[position]) {
                    "Dashboard" -> DashboardActivity.start(this@MainActivity)
                    "Uscite" -> RideListActivity.start(this@MainActivity)
                    "Tracciamento GPS" -> TrackingActivity.start(this@MainActivity)
                    "Mappe" -> MapsActivity.start(this@MainActivity)
                    "Zone" -> ZonesActivity.start(this@MainActivity)
                    "Badge" -> BadgesActivity.start(this@MainActivity)
                    "Heatmap" -> HeatmapActivity.start(this@MainActivity)
                    "Statistiche" -> StatsActivity.start(this@MainActivity)
                    "Profilo atleta" -> AthleteProfileActivity.start(this@MainActivity)
                    "AI Coach" -> CoachActivity.start(this@MainActivity)
                    "Calendario" -> CalendarActivity.start(this@MainActivity)
                    "Impostazioni" -> SettingsActivity.start(this@MainActivity)
                }
            }

            override fun onNothingSelected(parent: android.widget.AdapterView<*>) {
            }
        })
    }

    private fun setupButtons() {
        btnDashboard.setOnClickListener { DashboardActivity.start(this) }
        btnImport.setOnClickListener { ImportActivity.start(this) }
        btnWeather.setOnClickListener { WeatherActivity.start(this) }
        btnMaps.setOnClickListener { MapsActivity.start(this) }
        btnZones.setOnClickListener { ZonesActivity.start(this) }
        btnBadges.setOnClickListener { BadgesActivity.start(this) }
        btnHeatmap.setOnClickListener { HeatmapActivity.start(this) }
        btnRides.setOnClickListener { RideListActivity.start(this) }
        btnTracking.setOnClickListener { TrackingActivity.start(this) }
        btnStats.setOnClickListener { StatsActivity.start(this) }
        btnAthlete.setOnClickListener { AthleteProfileActivity.start(this) }
        btnCoach.setOnClickListener { CoachActivity.start(this) }
        btnCalendar.setOnClickListener { CalendarActivity.start(this) }
        btnSettings.setOnClickListener { SettingsActivity.start(this) }
        btnLogin.setOnClickListener { handleLoginButtonClick() }
    }

    private fun handleLoginButtonClick() {
        if (isUserLoggedIn()) {
            PreferencesManager.clearAuthToken(this)
            Toast.makeText(this, "Logout effettuato", Toast.LENGTH_SHORT).show()
            updateLoginButton()
        } else {
            LoginActivity.start(this)
        }
    }

    private fun updateLoginButton() {
        btnLogin.text = if (isUserLoggedIn()) getString(R.string.logout) else getString(R.string.login)
    }

    override fun onResume() {
        super.onResume()
        if (!isUserLoggedIn()) {
            LoginActivity.start(this)
            finish()
        } else {
            updateLoginButton()
        }
    }
}
