package com.bikemaster.models

import android.os.Parcelable
import com.google.gson.annotations.SerializedName
import kotlinx.parcelize.Parcelize

@Parcelize
data class HealthMetric(
    val metric_type: String,
    val value: Double,
    val unit: String? = null,
    val source: String = "health_connect",
    val recorded_at: String? = null
) : Parcelable

@Parcelize
data class HealthMetricsBatch(
    val metrics: List<HealthMetric> = emptyList()
) : Parcelable