package com.bikemaster.ui.auth

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityLoginBinding
import com.bikemaster.network.ApiClient
import com.bikemaster.utils.PreferencesManager
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityLoginBinding
    
    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, LoginActivity::class.java))
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        binding.loginButton.setOnClickListener { login() }
        binding.registerLink.setOnClickListener { RegisterActivity.start(this) }
    }
    
    private fun login() {
        val username = binding.usernameInput.text.toString()
        val password = binding.passwordInput.text.toString()
        
        if (username.isBlank() || password.isBlank()) {
            Toast.makeText(this, "Inserisci username e password", Toast.LENGTH_SHORT).show()
            return
        }
        
        lifecycleScope.launch {
            try {
                val response = ApiClient.getApi(this@LoginActivity).login(
                    username = username,
                    password = password
                )
                saveAuthToken(response.accessToken)
                val intent = Intent(this@LoginActivity, com.bikemaster.ui.MainActivity::class.java)
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                startActivity(intent)
            } catch (e: Exception) {
                Toast.makeText(this@LoginActivity, "Errore login: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun saveAuthToken(token: String) {
        PreferencesManager.setAuthToken(this, token)
    }
}