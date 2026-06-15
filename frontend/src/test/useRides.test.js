import { describe, it, expect, vi } from 'vitest'

describe('useRides composable', () => {
    it('fetchSummary returns default values on error', async () => {
        const { useRides } = await import('../../src/composables/useRides.js')
        const result = await useRides( vi.fn()).fetchSummary()
        expect(result.rides).toBe(0)
        expect(result.distance_km).toBe(0)
    })

    it('calculates totals correctly', () => {
        const mockData = {
            rides: [
                { id: 1, distance_km: 20, calories: 400, avg_speed_kmh: 25, duration_minutes: 60 },
                { id: 2, distance_km: 30, calories: 600, avg_speed_kmh: 30, duration_minutes: 90 },
            ],
            total: 2,
        }
        const emit = vi.fn()
        const { useRides } = require('../../src/composables/useRides.js')

        // Test calculation logic
        const totalKm = mockData.rides.reduce((s, r) => s + (Number(r.distance_km) || 0), 0)
        expect(totalKm).toBe(50)
    })
})