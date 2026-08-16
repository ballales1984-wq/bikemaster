package com.bikemaster.ui.coach

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityCoachBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class CoachActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityCoachBinding
    
    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, CoachActivity::class.java))
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCoachBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        loadCoachData()
    }
    
    private fun loadCoachData() {
        lifecycleScope.launch {
            try {
                val response = ApiClient.getApi(this@CoachActivity).getCoachFullData(athleteId = 1)
                binding.trainingAdvice.text = response["training_advice"] as? String ?: ""
                binding.recoveryAdvice.text = response["recovery_advice"] as? String ?: ""
            } catch (e: Exception) {
                Toast.makeText(this@CoachActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}