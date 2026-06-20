import { describe, expect, it } from 'vitest'
import { buildRidePolylines, escapeHtml, gradeRiskPercent, speedRiskPercent, weatherRiskPercent } from './routeMap.ts'

describe('routeMap helpers', () => {
  it('groups consecutive segments with the same color', () => {
    const ride = {
      segments: [
        { start: [0, 0], end: [1, 1], color: 'red' },
        { start: [1, 1], end: [2, 2], color: 'red' },
        { start: [2, 2], end: [3, 3], color: 'green' },
        { start: [3, 3], end: [4, 4], color: 'red' },
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
})
