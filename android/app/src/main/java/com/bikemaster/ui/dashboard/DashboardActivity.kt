package com.bikemaster.ui.dashboard

import android.animation.ValueAnimator
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.GridView
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.bikemaster.R
import com.bikemaster.databinding.ActivityDashboardBinding
import com.bikemaster.databinding.ItemStatCardBinding
import com.bikemaster.network.ApiClient
import com.bikemaster.ui.rides.RideAdapter
import com.bikemaster.ui.rides.RideDetailActivity
import kotlinx.coroutines.launch

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var rideAdapter: RideAdapter
    private var statsAdapter: StatsAdapter? = null

    companion object {
        fun start(context: Context) {
            context.startActivity(Intent(context, DashboardActivity::class.java))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.txtLoading.visibility = View.VISIBLE
        binding.txtError.visibility = View.GONE
        binding.gridStats.visibility = View.GONE
        binding.recyclerRides.visibility = View.GONE

        binding.recyclerRides.layoutManager = LinearLayoutManager(this)

        loadDashboard()
    }

    private fun loadDashboard() {
        lifecycleScope.launch {
            try {
                binding.txtLoading.visibility = View.VISIBLE
                binding.txtError.visibility = View.GONE

                val api = ApiClient.getApi(this@DashboardActivity)
                val dashboard = api.getDashboard()

                binding.txtLoading.visibility = View.GONE
                binding.gridStats.visibility = View.VISIBLE
                binding.recyclerRides.visibility = View.VISIBLE

                val rides = (dashboard["recent_rides"] as? List<Map<String, Any?>>) ?: emptyList()
                val count = (dashboard["rides_count"] as? Number)?.toInt() ?: rides.size
                val totalDistance = (dashboard["total_distance_km"] as? Number)?.toDouble() ?: 0.0
                val totalDuration = (dashboard["total_duration_minutes"] as? Number)?.toInt() ?: 0
                val avgSpeed = (dashboard["avg_speed_kmh"] as? Number)?.toDouble() ?: 0.0
                val totalCalories = (dashboard["total_calories"] as? Number)?.toInt()
                    ?: rides.sumOf { (it["calories"] as? Number)?.toInt() ?: 0 }
                val totalHours = totalDuration / 60.0

                val stats = listOf(
                    StatCard(
                        iconRes = R.drawable.ic_directions_bike,
                        value = count.toFloat(),
                        suffix = "",
                        label = "Uscite"
                    ),
                    StatCard(
                        iconRes = R.drawable.ic_route,
                        value = totalDistance.toFloat(),
                        suffix = " km",
                        label = "Distanza Totale"
                    ),
                    StatCard(
                        iconRes = R.drawable.ic_local_fire_department,
                        value = totalCalories.toFloat(),
                        suffix = "",
                        label = "Calorie"
                    ),
                    StatCard(
                        iconRes = R.drawable.ic_speed,
                        value = avgSpeed.toFloat(),
                        suffix = " km/h",
                        label = "Velocità Media"
                    ),
                    StatCard(
                        iconRes = R.drawable.ic_schedule,
                        value = totalHours.toFloat(),
                        suffix = " h",
                        label = "Ore Totali"
                    )
                )

                statsAdapter = StatsAdapter(stats)
                binding.gridStats.adapter = statsAdapter

                val rideList = rides.map { ride ->
                    com.bikemaster.models.Ride(
                        id = (ride["id"] as? Number)?.toInt() ?: 0,
                        date = ride["date"] as? String,
                        distanceKm = (ride["distance_km"] as? Number)?.toDouble() ?: 0.0,
                        durationMinutes = (ride["duration_minutes"] as? Number)?.toDouble() ?: 0.0,
                        avgSpeedKmh = (ride["avg_speed_kmh"] as? Number)?.toDouble() ?: 0.0,
                        calories = (ride["calories"] as? Number)?.toInt() ?: 0,
                        athleteId = (ride["athlete_id"] as? Number)?.toInt()
                    )
                }

                rideAdapter = RideAdapter { ride ->
                    RideDetailActivity.start(this@DashboardActivity, ride)
                }
                rideAdapter.submitList(rideList)
                binding.recyclerRides.adapter = rideAdapter

            } catch (e: Exception) {
                binding.txtLoading.visibility = View.GONE
                binding.txtError.visibility = View.VISIBLE
                binding.txtError.text = "Errore: ${e.message}"
                Toast.makeText(this@DashboardActivity, "Errore caricamento dashboard", Toast.LENGTH_SHORT).show()
            }
        }
    }

    data class StatCard(
        val iconRes: Int,
        val value: Float,
        val suffix: String,
        val label: String
    )

    class StatsAdapter(private val stats: List<StatCard>) : BaseAdapter() {
        override fun getCount(): Int = stats.size
        override fun getItem(position: Int): Any = stats[position]
        override fun getItemId(position: Int): Long = position.toLong()

        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val binding = if (convertView == null) {
                val inflater = LayoutInflater.from(parent.context)
                ItemStatCardBinding.inflate(inflater, parent, false)
            } else {
                ItemStatCardBinding.bind(convertView)
            }

            val stat = stats[position]
            binding.imgIcon.setImageResource(stat.iconRes)
            binding.txtLabel.text = stat.label

            val currentText = binding.txtValue.text.toString().toFloatOrNull() ?: 0f
            animateValue(binding.txtValue, currentText, stat.value, stat.suffix)

            return binding.root
        }

        private fun animateValue(textView: TextView, from: Float, to: Float, suffix: String) {
            val animator = ValueAnimator.ofFloat(from, to)
            animator.duration = 800
            animator.addUpdateListener { animation ->
                val value = animation.animatedValue as Float
                val formatted = if (suffix == " km" || suffix == " km/h" || suffix == " h") {
                    String.format("%.1f%s", value, suffix)
                } else {
                    String.format("%.0f%s", value, suffix)
                }
                textView.text = formatted
            }
            animator.start()
        }
    }
}
