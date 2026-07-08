package com.bikemaster

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

/**
 * Uploads finished ride GPX files to the backend `POST /api/v1/import/gpx` (#225).
 *
 * Behaviour:
 * - Multipart/form-data upload with `Authorization: Bearer <token>`.
 * - Retries with exponential backoff (default 3 attempts) when the request fails.
 * - On persistent failure the ride is persisted in an offline queue
 *   (`pending_uploads.json`) and retried later via [flushPending].
 *
 * The completion notification (#226) is fired by [BikeTrackingService] from the [UploadResult].
 */
object RideUploader {

    private const val TAG = "BikeUploader"
    const val ENDPOINT_PATH = "/api/v1/import/gpx"
    private const val MAX_ATTEMPTS = 3
    private const val QUEUE_FILE = "pending_uploads.json"

    data class UploadResult(
        val success: Boolean,
        val file: String,
        val rideId: Long? = null,
        val message: String = ""
    )

    fun uploadRide(
        context: Context,
        file: File,
        apiBaseUrl: String,
        token: String?,
        rideName: String?,
        callback: (UploadResult) -> Unit
    ) {
        var lastMessage = "Unknown error"
        for (attempt in 1..MAX_ATTEMPTS) {
            try {
                val result = doUpload(file, apiBaseUrl, token, rideName)
                if (result.success) {
                    callback(result)
                    return
                }
                lastMessage = result.message
            } catch (e: IOException) {
                lastMessage = "Network error: ${e.message}"
            } catch (e: Exception) {
                lastMessage = "Upload error: ${e.message}"
            }
            if (attempt < MAX_ATTEMPTS) {
                try {
                    Thread.sleep((attempt * attempt * 1500L))
                } catch (_: InterruptedException) {
                }
            }
        }
        enqueue(context, file, apiBaseUrl, token, rideName)
        callback(
            UploadResult(
                success = false,
                file = file.absolutePath,
                message = "$lastMessage — queued for later upload (offline)."
            )
        )
    }

    @Throws(IOException::class)
    private fun doUpload(
        file: File,
        apiBaseUrl: String,
        token: String?,
        rideName: String?
    ): UploadResult {
        val base = apiBaseUrl.trimEnd('/')
        val url = URL("$base$ENDPOINT_PATH")
        val conn = url.openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.connectTimeout = 30_000
        conn.readTimeout = 30_000
        conn.setRequestProperty("Authorization", "Bearer ${token ?: ""}")
        conn.setRequestProperty("Accept", "application/json")

        val boundary = "bikemaster-${System.currentTimeMillis()}"
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")

        conn.outputStream.use { out ->
            writeFilePart(out, boundary, file, rideName ?: file.name)
            out.write("--$boundary--\r\n".toByteArray(StandardCharsets.UTF_8))
        }

        val code = conn.responseCode
        val body = if (code in 200..299) {
            readStream(conn.inputStream)
        } else {
            readStream(conn.errorStream ?: conn.inputStream)
        }
        conn.disconnect()

        return if (code in 200..299) {
            val rideId = try {
                JSONObject(body).optLong("id", -1L).takeIf { it != -1L }
            } catch (_: Exception) {
                null
            }
            UploadResult(success = true, file = file.absolutePath, rideId = rideId, message = "Upload completato")
        } else {
            UploadResult(success = false, file = file.absolutePath, message = "HTTP $code: $body")
        }
    }

    private fun writeFilePart(out: OutputStream, boundary: String, file: File, name: String) {
        val start = "--$boundary\r\n" +
            "Content-Disposition: form-data; name=\"file\"; filename=\"${name.replace("\"", "")}\"\r\n" +
            "Content-Type: application/gpx+xml\r\n\r\n"
        out.write(start.toByteArray(StandardCharsets.UTF_8))
        FileInputStream(file).use { it.copyTo(out) }
        out.write("\r\n".toByteArray(StandardCharsets.UTF_8))
    }

    private fun readStream(stream: java.io.InputStream?): String {
        if (stream == null) return ""
        return BufferedReader(InputStreamReader(stream, StandardCharsets.UTF_8)).use { reader ->
            val sb = StringBuilder()
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                sb.append(line)
            }
            sb.toString()
        }
    }

    // ---- Offline queue -------------------------------------------------------------

    private fun enqueue(context: Context, file: File, apiBaseUrl: String, token: String?, rideName: String?) {
        try {
            val queue = readQueue(context).toMutableList()
            queue.add(
                JSONObject().apply {
                    put("path", file.absolutePath)
                    put("apiBaseUrl", apiBaseUrl)
                    put("token", token ?: "")
                    put("name", rideName ?: file.name)
                }
            )
            writeQueue(context, queue)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to enqueue pending upload", e)
        }
    }

    /** Retry every queued ride. Call on app foreground / next tracking start. */
    fun flushPending(context: Context, onEach: ((UploadResult) -> Unit)? = null) {
        val queue = readQueue(context)
        if (queue.isEmpty()) return
        val remaining = mutableListOf<JSONObject>()
        for (entry in queue) {
            val file = File(entry.optString("path"))
            if (!file.exists()) continue
            var lastResult: UploadResult? = null
            uploadRide(
                context, file, entry.optString("apiBaseUrl"),
                entry.optString("token").takeIf { it.isNotEmpty() },
                entry.optString("name"),
            ) { lastResult = it; onEach?.invoke(it) }
            if (lastResult?.success != true) remaining.add(entry)
        }
        writeQueue(context, remaining)
    }

    private fun readQueue(context: Context): List<JSONObject> {
        val file = File(context.filesDir, QUEUE_FILE)
        if (!file.exists()) return emptyList()
        return try {
            val arr = JSONObject(file.readText()).optJSONArray("queue") ?: return emptyList()
            (0 until arr.length()).map { arr.getJSONObject(it) }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeQueue(context: Context, entries: List<JSONObject>) {
        val file = File(context.filesDir, QUEUE_FILE)
        try {
            val arr = org.json.JSONArray()
            entries.forEach { arr.put(it) }
            file.writeText(JSONObject().put("queue", arr).toString())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to persist pending upload queue", e)
        }
    }
}
