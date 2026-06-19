package com.bikemaster.ui.rides

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import androidx.appcompat.app.AlertDialog
import com.bikemaster.R
import com.bikemaster.databinding.DialogAddRideBinding
import com.bikemaster.models.Ride

class AddRideDialog(private val activity: Activity, private val onRideAdded: (Ride) -> Unit) {
    
    companion object {
        fun show(activity: Activity, onRideAdded: (Ride) -> Unit) {
            AddRideDialog(activity, onRideAdded).show()
        }
    }
    private lateinit var binding: DialogAddRideBinding
    
    fun show() {
        val dialog = AlertDialog.Builder(activity)
        binding = DialogAddRideBinding.inflate(LayoutInflater.from(activity))
        
        dialog.setView(binding.root)
            .setTitle("Nuova Attività")
            .setPositiveButton("Salva") { _, _ ->
                val ride = Ride(
                    name = binding.nameInput.text.toString(),
                    date = binding.dateInput.text.toString(),
                    distanceKm = binding.distanceInput.text.toString().toDoubleOrNull() ?: 0.0,
                    durationMinutes = binding.durationInput.text.toString().toDoubleOrNull() ?: 0.0,
                    avgSpeedKmh = binding.speedInput.text.toString().toDoubleOrNull() ?: 0.0
                )
                onRideAdded(ride)
            }
            .setNegativeButton("Annulla", null)
            .show()
    }
}
