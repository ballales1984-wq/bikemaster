package com.bikemaster.ui.calendar

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bikemaster.R
import com.bikemaster.databinding.ItemCalendarEventBinding
import com.bikemaster.models.CalendarEvent

class CalendarAdapter : ListAdapter<CalendarEvent, CalendarAdapter.ViewHolder>(CalendarDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemCalendarEventBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(private val binding: ItemCalendarEventBinding) : 
        RecyclerView.ViewHolder(binding.root) {
        
        fun bind(event: CalendarEvent) {
            binding.apply {
                titleText.text = event.title
                dateText.text = event.date
                typeText.text = event.workoutType ?: "Training"
                completedCheckbox.isChecked = event.completed
            }
        }
    }
}

class CalendarDiffCallback : DiffUtil.ItemCallback<CalendarEvent>() {
    override fun areItemsTheSame(oldItem: CalendarEvent, newItem: CalendarEvent): Boolean = oldItem.id == newItem.id
    override fun areContentsTheSame(oldItem: CalendarEvent, newItem: CalendarEvent): Boolean = oldItem == newItem
}