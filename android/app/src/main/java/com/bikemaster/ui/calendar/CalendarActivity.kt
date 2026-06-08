package com.bikemaster.ui.calendar

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.bikemaster.R
import com.bikemaster.databinding.ActivityCalendarBinding
import com.bikemaster.models.CalendarEvent
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch
import java.util.Calendar

class CalendarActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityCalendarBinding
    private lateinit var adapter: CalendarAdapter
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCalendarBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupCalendar()
        loadEvents()
    }
    
    private fun setupCalendar() {
        adapter = CalendarAdapter()
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter
    }
    
    private fun loadEvents() {
        val calendar = Calendar.getInstance()
        lifecycleScope.launch {
            try {
                val response = ApiClient.api.getCalendarEvents(
                    athleteId = 1,
                    year = calendar.get(Calendar.YEAR),
                    month = calendar.get(Calendar.MONTH) + 1
                )
                adapter.submitList(response["events"] ?: emptyList<CalendarEvent>())
            } catch (e: Exception) {
                Toast.makeText(this@CalendarActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}