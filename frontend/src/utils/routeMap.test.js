import { describe, expect, it } from 'vitest'
import { buildRidePolylines, escapeHtml, gradeRiskPercent, speedRiskPercent, weatherRiskPercent, speedColor } from './routeMap'

describe('routeMap helpers', () => {
  it('groups consecutive segments with the same color', () => {
    const ride = {
      segments: [
        { start: [0, 0], end: [1, 1], color: 'red', distance_m: 0, elevation_delta_m: 0, grade: 0, risk: 0 },
        { start: [1, 1], end: [2, 2], color: 'red', distance_m: 0, elevation_delta_m: 0, grade: 0, risk: 0 },
        { start: [2, 2], end: [3, 3], color: 'green', distance_m: 0, elevation_delta_m: 0, grade: 0, risk: 0 },
        { start: [3, 3], end: [4, 4], color: 'red', distance_m: 0, elevation_delta_m: 0, grade: 0, risk: 0 },
      ],
    }

    expect(buildRidePolylines(ride)).toEqual([
      { color: 'red', points: [[0, 0], [1, 1], [2, 2]] },
      { color: 'green', points: [[2, 2], [3, 3]] },
      { color: 'red', points: [[3, 3], [4, 4]] },
    ])
  })

  it('escapes html used in map popups', () => {
    expect(escapeHtml('<script>alert("x")</script>')).toBe('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;')
  })

  it('maps grade and weather scores to risk levels', () => {
    expect(gradeRiskPercent(2.9)).toBe(15)
    expect(gradeRiskPercent(6.1)).toBe(65)
    expect(weatherRiskPercent(8)).toBe(10)
    expect(weatherRiskPercent(4)).toBe(85)
  })

  it('maps speed to risk levels', () => {
    expect(speedRiskPercent(30)).toBe(15)
    expect(speedRiskPercent(25)).toBe(15)
    expect(speedRiskPercent(15)).toBe(45)
    expect(speedRiskPercent(14)).toBe(85)
    expect(speedRiskPercent(0)).toBe(85)
    expect(speedRiskPercent(null)).toBe(85)
  })

  it('speedColor returns default color for no points', () => {
    expect(speedColor({ gps_points: [] }, 0)).toBe('#4488ff')
  })

  it('speedColor returns default color when speed is null', () => {
    const ride = { gps_points: [{ lat: 0, lon: 0, speed: null }] }
    expect(speedColor(ride, 0)).toBe('#4488ff')
  })

  it('speedColor calculates gradient for speed values', () => {
    const ride = {
      gps_points: [
        { lat: 0, lon: 0, speed: 10 },
        { lat: 1, lon: 1, speed: 20 },
        { lat: 2, lon: 2, speed: 30 },
      ],
    }
    const color = speedColor(ride, 1)
    expect(color).toMatch(/^#[0-9a-f]{6}$/)
  })
})
