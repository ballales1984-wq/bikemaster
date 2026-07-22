package com.bikemaster.sensors.decoders

import android.util.Log
import java.nio.ByteBuffer
import java.nio.ByteOrder

object RunstarDecoder {

    private const val TAG = "RunstarDecoder"

    data class ScaleData(
        val weightKg: Double,
        val fatPercentage: Double? = null,
        val muscleMassKg: Double? = null,
        val boneMassKg: Double? = null,
        val waterPercentage: Double? = null,
        val timestamp: Long = System.currentTimeMillis()
    )

    fun decode(data: ByteArray?): ScaleData? {
        if (data == null || data.isEmpty()) {
            Log.w(TAG, "Dati vuoti o nulli")
            return null
        }

        return try {
            val buffer = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)

            val flag = buffer.get().toUInt()
            Log.d(TAG, "Flag: 0x${flag.toString(16)}")

            val weightRaw = buffer.short.toUShort()
            val weightKg = weightRaw.toDouble() / 200.0

            var fatPercentage: Double? = null
            var muscleMassKg: Double? = null
            var boneMassKg: Double? = null
            var waterPercentage: Double? = null

            if (buffer.hasRemaining() && data.size >= 4) {
                fatPercentage = buffer.get().toUByte().toDouble() / 2.0
            }
            if (buffer.hasRemaining() && data.size >= 5) {
                muscleMassKg = buffer.get().toUByte().toDouble() / 10.0
            }
            if (buffer.hasRemaining() && data.size >= 6) {
                boneMassKg = buffer.get().toUByte().toDouble() / 10.0
            }
            if (buffer.hasRemaining() && data.size >= 7) {
                waterPercentage = buffer.get().toUByte().toDouble() / 2.0
            }

            ScaleData(
                weightKg = weightKg,
                fatPercentage = fatPercentage,
                muscleMassKg = muscleMassKg,
                boneMassKg = boneMassKg,
                waterPercentage = waterPercentage
            )
        } catch (e: Exception) {
            Log.e(TAG, "Errore decodifica Runstar", e)
            null
        }
    }
}