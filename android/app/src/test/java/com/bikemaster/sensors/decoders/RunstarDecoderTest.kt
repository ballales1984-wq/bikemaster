package com.bikemaster.sensors.decoders

import org.junit.Test
import org.junit.Assert.*

class RunstarDecoderTest {

    @Test
    fun `decode null data returns null`() {
        assertNull(RunstarDecoder.decode(null))
    }

    @Test
    fun `decode empty data returns null`() {
        assertNull(RunstarDecoder.decode(ByteArray(0)))
    }

    @Test
    fun `decode weight-only payload`() {
        val data = byteArrayOf(0x1D, 0x10, 0x27)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(50.0, result!!.weightKg, 0.001)
        assertNull(result.fatPercentage)
        assertNull(result.muscleMassKg)
        assertNull(result.boneMassKg)
        assertNull(result.waterPercentage)
    }

    @Test
    fun `decode weight with fat percentage only`() {
        val data = byteArrayOf(0x1D, 0x10, 0x27, 0x19)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(50.0, result!!.weightKg, 0.001)
        assertEquals(12.5, result.fatPercentage!!, 0.001)
        assertNull(result.muscleMassKg)
        assertNull(result.boneMassKg)
        assertNull(result.waterPercentage)
    }

    @Test
    fun `decode full body composition payload`() {
        val data = byteArrayOf(0x1D, 0x10, 0x27, 0x19, 0x0A, 0x05, 0x32)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(50.0, result!!.weightKg, 0.001)
        assertEquals(12.5, result.fatPercentage!!, 0.001)
        assertEquals(5.0, result.muscleMassKg!!, 0.001)
        assertEquals(0.5, result.boneMassKg!!, 0.001)
        assertEquals(25.0, result.waterPercentage!!, 0.001)
    }

    @Test
    fun `decode minimum weight payload`() {
        val data = byteArrayOf(0x1D, 0x01, 0x00)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(0.005, result!!.weightKg, 0.001)
    }

    @Test
    fun `decode maximum weight payload`() {
        val data = byteArrayOf(0x1D, 0xFF, 0x7F)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(3276.75, result!!.weightKg, 0.001)
    }

    @Test
    fun `decode payload with only weight and muscle mass`() {
        val data = byteArrayOf(0x1D, 0x10, 0x27, 0x00, 0x0A)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(50.0, result!!.weightKg, 0.001)
        assertNull(result.fatPercentage)
        assertEquals(5.0, result.muscleMassKg!!, 0.001)
        assertNull(result.boneMassKg)
        assertNull(result.waterPercentage)
    }

    @Test
    fun `decode payload with weight and water percentage only`() {
        val data = byteArrayOf(0x1D, 0x10, 0x27, 0x00, 0x00, 0x00, 0x32)
        val result = RunstarDecoder.decode(data)
        assertNotNull(result)
        assertEquals(50.0, result!!.weightKg, 0.001)
        assertNull(result.fatPercentage)
        assertNull(result.muscleMassKg)
        assertNull(result.boneMassKg)
        assertEquals(25.0, result.waterPercentage!!, 0.001)
    }

    @Test
    fun `decode sets timestamp to current time`() {
        val before = System.currentTimeMillis()
        val data = byteArrayOf(0x1D, 0x10, 0x27)
        val result = RunstarDecoder.decode(data)
        val after = System.currentTimeMillis()
        assertNotNull(result)
        assertTrue(result!!.timestamp in before..after)
    }

    @Test
    fun `decode single byte returns null`() {
        val data = byteArrayOf(0x1D)
        assertNull(RunstarDecoder.decode(data))
    }

    @Test
    fun `decode two bytes returns null`() {
        val data = byteArrayOf(0x1D, 0x10)
        assertNull(RunstarDecoder.decode(data))
    }
}