package com.bikemaster.models

import android.os.Parcelable
import kotlinx.parcelize.Parcelize

@Parcelize
data class Ride(
    val id: Int = 0,
    val name: String? = null,
    val date: String? = null,
    val distanceKm: Double = 0.0,
    val durationMinutes: Double = 0.0,
    val avgSpeedKmh: Double = 0.0,
    val calories: Int = 0,
    val elevationGainM: Double = 0.0,
    val gpsPoints: List<GPSPoint> = emptyList(),
    val athleteId: Int? = null,
    val fatigueScore: Double? = null,
    val caloriesPerKm: Double? = null
) : Parcelable

@Parcelize
data class GPSPoint(
    val lat: Double,
    val lon: Double,
    val elevation: Double? = null,
    val timestamp: String? = null
) : Parcelable

@Parcelize
data class AthleteProfile(
    val id: Int = 0,
    val name: String? = null,
    val experienceLevel: String = "Beginner",
    val weightKg: Double? = null,
    val ftp: Int? = null,
    val maxHr: Int? = null,
    val restingHr: Int? = null,
    val birthDate: String? = null
) : Parcelable

@Parcelize
data class CalendarEvent(
    val id: Int = 0,
    val athleteId: Int,
    val title: String,
    val description: String? = null,
    val date: String,
    val workoutType: String? = null,
    val completed: Boolean = false
) : Parcelable

data class RideResponse(
    val rides: List<Ride> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val pageSize: Int = 20
)

data class TrainingLoad(
    val atl: Double = 0.0,
    val ctl: Double = 0.0,
    val tsb: Double = 0.0,
    val recommendation: String? = null
)

data class WorkoutRecommendation(
    val recommendations: String
)

data class AuthResponse(
    val accessToken: String,
    val tokenType: String
)

data class LoginRequest(
    val username: String,
    val password: String
)