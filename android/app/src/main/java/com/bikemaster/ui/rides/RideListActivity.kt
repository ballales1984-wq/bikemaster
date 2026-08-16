package com.bikemaster.ui.rides

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityRideListBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch
import androidx.core.view.isVisible

class RideListActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityRideListBinding
    private lateinit var adapter: RideAdapter
    
    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, RideListActivity::class.java))
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRideListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupRecyclerView()
        loadRides()
        
        binding.fabAddRide.setOnClickListener {
            AddRideDialog.show(this) { ride ->
                adapter.addRide(ride)
            }
        }
    }
    
    private fun setupRecyclerView() {
        adapter = RideAdapter { ride ->
            RideDetailActivity.start(this, ride)
        }
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter
    }
    
    private fun loadRides() {
        binding.progressBar.isVisible = true
        lifecycleScope.launch {
            try {
                val response = ApiClient.getApi(this@RideListActivity).getRides()
                adapter.submitList(response.rides)
            } catch (e: Exception) {
                Toast.makeText(this@RideListActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.isVisible = false
            }
        }
    }
}