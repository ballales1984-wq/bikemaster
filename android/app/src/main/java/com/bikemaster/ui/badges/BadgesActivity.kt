package com.bikemaster.ui.badges

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
import com.bikemaster.databinding.ActivityBadgesBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch

class BadgesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBadgesBinding

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, BadgesActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBadgesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnLoad.setOnClickListener {
            val athleteId = binding.inputAthleteId.text.toString().toIntOrNull()
            if (athleteId == null) {
                Toast.makeText(this, "Inserisci un Athlete ID valido", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            loadBadges(athleteId)
        }
    }

    private fun loadBadges(athleteId: Int) {
        lifecycleScope.launch {
            try {
                binding.progress.visibility = ProgressBar.VISIBLE
                binding.txtError.visibility = TextView.GONE

                val api = ApiClient.getApi(this@BadgesActivity)
                val response = api.getBadges(athleteId)

                binding.progress.visibility = ProgressBar.GONE
                binding.txtSummary.visibility = TextView.VISIBLE
                binding.txtSummary.text = "Badge sbloccati: ${response["achieved"]}/${response["total_badges"]}"

                binding.layoutBadges.removeAllViews()

                val badges = response["badges"] as? List<Map<String, Any?>> ?: emptyList()
                val grouped = badges.groupBy { it["category"] as? String ?: "other" }

                grouped.forEach { (category, badgeList) ->
                    val categoryTitle = TextView(this@BadgesActivity)
                    categoryTitle.text = category.replaceFirstChar { it.uppercase() }
                    categoryTitle.textSize = 18f
                    categoryTitle.setPadding(0, 16, 0, 8)
                    binding.layoutBadges.addView(categoryTitle)

                    badgeList.forEach { badge ->
                        val tv = TextView(this@BadgesActivity)
                        val name = badge["name"] as? String ?: "Badge"
                        val description = badge["description"] as? String ?: ""
                        val achieved = badge["achieved"] as? Boolean ?: false
                        val progress = (badge["progress"] as? Number)?.toDouble() ?: 0.0

                        tv.text = "${if (achieved) "✅" else "⭕"} $name: ${String.format("%.0f", progress)}%\n$description"
                        tv.setPadding(0, 0, 0, 12)
                        binding.layoutBadges.addView(tv)
                    }
                }

            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@BadgesActivity, "Errore caricamento badge", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
