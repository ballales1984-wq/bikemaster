import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import RideComparison from '../components/RideComparison.vue'

vi.mock('../utils/api.ts', () => ({
  apiGet: vi.fn().mockResolvedValue({ rides: [] }),
}))

describe('RideComparison', () => {
  it('renders the title', () => {
    const wrapper = mount(RideComparison)
    expect(wrapper.find('h2').text()).toContain('Confronto')
  })

  it('has swap button', () => {
    const wrapper = mount(RideComparison)
    expect(wrapper.find('.swap-btn').exists()).toBe(true)
  })

  it('shows empty state initially', () => {
    const wrapper = mount(RideComparison)
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('calculates comparison correctly', async () => {
    const wrapper = mount(RideComparison)
    // Set rides directly
    wrapper.vm.rides = [
      { id: 1, date: '2026-01-01', distance_km: 40, duration_minutes: 90, avg_speed_kmh: 26.7, elevation_gain_m: 500, calories: 400 },
      { id: 2, date: '2026-01-02', distance_km: 50, duration_minutes: 120, avg_speed_kmh: 25, elevation_gain_m: 600, calories: 500 },
    ]
    wrapper.vm.rideA = wrapper.vm.rides[0]
    wrapper.vm.rideB = wrapper.vm.rides[1]
    
    const comparison = wrapper.vm.comparison
    expect(comparison.ready).toBe(true)
  })

  it('swaps rides correctly', async () => {
    const wrapper = mount(RideComparison)
    wrapper.vm.rides = [{ id: 1, date: '2026-01-01', distance_km: 40 }]
    wrapper.vm.rideA = wrapper.vm.rides[0]
    wrapper.vm.rideB = null
    
    await wrapper.find('.swap-btn').trigger('click')
    
    expect(wrapper.vm.rideB).toEqual(wrapper.vm.rides[0])
    expect(wrapper.vm.rideA).toBeNull()
  })
})