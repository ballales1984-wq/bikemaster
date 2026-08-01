package com.bikemaster.utils

import android.content.Context
import androidx.preference.PreferenceManager

object PreferencesManager {
    private const val KEY_BACKEND_URL = "backend_url"
    private const val KEY_API_KEY = "api_key"
    private const val KEY_ATHLETE_ID = "athlete_id"

    fun getBaseUrl(context: Context): String {
        val prefs = PreferenceManager.getDefaultSharedPreferences(context)
        return prefs.getString(KEY_BACKEND_URL, "https://bikemaster-api.onrender.com/api/v1/") ?: "https://bikemaster-api.onrender.com/api/v1/"
    }

    fun getApiKey(context: Context): String? {
        val prefs = PreferenceManager.getDefaultSharedPreferences(context)
        return prefs.getString(KEY_API_KEY, null)
    }

    fun setBaseUrl(context: Context, url: String) {
        PreferenceManager.getDefaultSharedPreferences(context).edit()
            .putString(KEY_BACKEND_URL, url).apply()
    }

    fun getAthleteId(context: Context): Int? {
        val prefs = PreferenceManager.getDefaultSharedPreferences(context)
        return prefs.getInt(KEY_ATHLETE_ID, -1).takeIf { it != -1 }
    }

    fun setAthleteId(context: Context, athleteId: Int) {
        PreferenceManager.getDefaultSharedPreferences(context).edit()
            .putInt(KEY_ATHLETE_ID, athleteId).apply()
    }
}