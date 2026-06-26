import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

import DashboardPanel from './DashboardPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockDashboard = {
  athlete: { name: 'Marco Rossi', email: 'marco@test.it', experience_level: 'Intermediate' },
  summary: { total_rides: 42, total_km: 1250.5, total_hours: 65, total_calories: 32000 },
  scores: { performance: 7.5, endurance: 6.8, recovery: 8.0, efficiency: 7.2 },
  fitness: { atl: 45.2, ctl: 52.1, tsb: -6.9, status: 'In forma' },
  trends: { weekly_progress: [12, 0, 25, 0, 18, 30, 0] },
}

describe('DashboardPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows dashboard data correctly', async () => {
    apiGet.mockResolvedValueOnce(mockDashboard)

    const wrapper = mount(DashboardPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/dashboard')
    expect(wrapper.text()).toContain('Marco Rossi')
    expect(wrapper.text()).toContain('42')
    expect(wrapper.text()).toContain('1250.5')
  })

  it('shows loading state initially', async () => {
    apiGet.mockResolvedValueOnce(mockDashboard)

    const wrapper = mount(DashboardPanel)
    
    // Initially loading is true, so skeleton-grid is shown when no summary yet
    expect(wrapper.vm.loading).toBe(true)
  })

  it('shows error if fetch fails', async () => {
    apiGet.mockRejectedValueOnce(new Error('Network error'))

    const wrapper = mount(DashboardPanel)
    await flush()

    expect(wrapper.find('.error-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('Errore')
  })

  it('shows dashboard cards in grid', async () => {
    apiGet.mockResolvedValueOnce(mockDashboard)

    const wrapper = mount(DashboardPanel)
    await flush()

    const cards = wrapper.findAll('.dash-card')
    expect(cards.length).toBeGreaterThanOrEqual(2)
  })

  it('shows scores correctly', async () => {
    apiGet.mockResolvedValueOnce(mockDashboard)

    const wrapper = mount(DashboardPanel)
    await flush()

    // Scores are rendered in ring-value elements
    const scoreValues = wrapper.findAll('.ring-value')
    const scoreTexts = scoreValues.map(v => v.text())
    expect(scoreTexts.some(t => t.includes('7.5') || t.includes('7.5') || t.includes('7'))).toBe(true)
  })

  it('shows ATL/CTL/TSB values from fitness', async () => {
    apiGet.mockResolvedValueOnce(mockDashboard)

    const wrapper = mount(DashboardPanel)
    await flush()

    expect(wrapper.text()).toContain('45.2')
    expect(wrapper.text()).toContain('52.1')
    expect(wrapper.text()).toContain('In forma')
  })
})