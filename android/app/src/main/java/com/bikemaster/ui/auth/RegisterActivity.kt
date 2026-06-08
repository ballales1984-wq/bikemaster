package com.bikemaster.ui.auth

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityRegisterBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class RegisterActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityRegisterBinding
    
    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, RegisterActivity::class.java))
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        binding.registerButton.setOnClickListener { register() }
        binding.loginLink.setOnClickListener { finish() }
    }
    
    private fun register() {
        val username = binding.usernameInput.text.toString()
        val password = binding.passwordInput.text.toString()
        
        if (username.length < 3 || password.length < 6) {
            Toast.makeText(this, "Username min 3 caratteri, password min 6", Toast.LENGTH_SHORT).show()
            return
        }
        
        lifecycleScope.launch {
            try {
                ApiClient.getApi(this@RegisterActivity).register(
                    mapOf("username" to username, "password" to password)
                )
                Toast.makeText(this@RegisterActivity, "Registrazione completata!", Toast.LENGTH_SHORT).show()
                LoginActivity.start(this@RegisterActivity)
                finish()
            } catch (e: Exception) {
                Toast.makeText(this@RegisterActivity, "Errore: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}