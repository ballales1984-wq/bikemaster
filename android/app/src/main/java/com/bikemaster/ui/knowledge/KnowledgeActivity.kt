package com.bikemaster.ui.knowledge

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityKnowledgeBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class KnowledgeActivity : AppCompatActivity() {

    private lateinit var binding: ActivityKnowledgeBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, KnowledgeActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityKnowledgeBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnSearch.setOnClickListener {
            val query = binding.inputQuery.text.toString().trim()
            if (query.length < 3) {
                Toast.makeText(this, "Inserisci almeno 3 caratteri", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            searchKnowledge(query)
        }
    }

    private fun searchKnowledge(query: String) {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE
                binding.layoutResults.removeAllViews()

                val api = ApiClient.getApi(this@KnowledgeActivity)
                val response = api.searchKnowledge(query)

                binding.progress.visibility = ProgressBar.GONE

                val results = response["results"] as? List<Map<String, Any?>> ?: emptyList()

                if (results.isEmpty()) {
                    binding.txtError.visibility = TextView.VISIBLE
                    binding.txtError.text = "Nessun risultato per: $query"
                    return@launch
                }

                results.forEach { result ->
                    val title = result["title"] as? String ?: "Senza titolo"
                    val content = result["content"] as? String ?: ""
                    val score = result["score"] as? Number

                    val tv = TextView(this@KnowledgeActivity)
                    tv.text = "$title\n$content"
                    tv.setPadding(0, 0, 0, 16)
                    binding.layoutResults.addView(tv)
                }

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@KnowledgeActivity, "Errore ricerca knowledge", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
