package com.bikemaster.ui.rides

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bikemaster.R
import com.bikemaster.databinding.ItemRideBinding
import com.bikemaster.models.Ride

class RideAdapter(
    private val onItemClick: (Ride) -> Unit
) : ListAdapter<Ride, RideAdapter.RideViewHolder>(RideDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RideViewHolder {
        val binding = ItemRideBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return RideViewHolder(binding)
    }

    override fun onBindViewHolder(holder: RideViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    fun addRide(ride: Ride) {
        val current = currentList.toMutableList()
        current.add(0, ride)
        submitList(current)
    }

    inner class RideViewHolder(private val binding: ItemRideBinding) : 
        RecyclerView.ViewHolder(binding.root) {
        
        fun bind(ride: Ride) {
            binding.apply {
                nameText.text = ride.name ?: "Ride ${ride.id}"
                distanceText.text = "${String.format("%.1f", ride.distanceKm)} km"
                durationText.text = "${String.format("%.0f", ride.durationMinutes)} min"
                speedText.text = "${String.format("%.1f", ride.avgSpeedKmh)} km/h"
                dateText.text = ride.date ?: ""
                
                root.setOnClickListener { onItemClick(ride) }
            }
        }
    }
}

class RideDiffCallback : DiffUtil.ItemCallback<Ride>() {
    override fun areItemsTheSame(oldItem: Ride, newItem: Ride): Boolean = oldItem.id == newItem.id
    override fun areContentsTheSame(oldItem: Ride, newItem: Ride): Boolean = oldItem == newItem
}