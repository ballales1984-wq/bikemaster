package com.bikemaster

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Pure GPX extension builders for ride metadata (no Android dependencies) so the mapping logic
 * can be unit-tested with plain JUnit (#227) and reused by [BikeTrackingService].
 */
object GpxExtensions {

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)

    /** Build the `<extensions>` block listing detected activity segments for a ride. */
    fun buildActivityExtensionsXml(segments: List<ActivitySegment>): String {
        if (segments.isEmpty()) return ""
        val sb = StringBuilder()
        sb.append("    <extensions>\n")
        sb.append("      <bikemaster:activities>\n")
        for (seg in segments) {
            val start = dateFormat.format(Date(seg.startMs))
            val end = dateFormat.format(Date(seg.endMs))
            sb.append(
                "        <bikemaster:activity type=\"${seg.activity.label}\" " +
                    "start=\"$start\" end=\"$end\" source=\"${seg.source}\"/>\n"
            )
        }
        sb.append("      </bikemaster:activities>\n")
        sb.append("    </extensions>\n")
        return sb.toString()
    }

    /** Serialize segments to a JSON array string (mirrors the JS payload sent to the web layer). */
    fun segmentsToJson(segments: List<ActivitySegment>): String {
        val arr = org.json.JSONArray()
        segments.forEach { seg ->
            arr.put(
                org.json.JSONObject().apply {
                    put("type", seg.activity.label)
                    put("start", seg.startMs)
                    put("end", seg.endMs)
                    put("source", seg.source)
                }
            )
        }
        return arr.toString()
    }
}
