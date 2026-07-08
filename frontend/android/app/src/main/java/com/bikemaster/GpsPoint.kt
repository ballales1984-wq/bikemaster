package com.bikemaster

import android.os.Parcelable
import kotlinx.parcelize.Parcelize

/**
 * Lightweight GPS point used for in-memory processing, compression and unit tests.
 * Mirrors the backend dict shape consumed by `gps_parser.douglas_peucker`.
 */
@Parcelize
data class GpsPoint(
    val lat: Double,
    val lon: Double,
    val altitude: Double? = null,
    val timestampMs: Long? = null
) : Parcelable
