import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SpeedMap from '../components/SpeedMap.vue'

vi.mock('../utils/api.ts', () => ({
  apiGet: vi.fn(),
}))

describe('SpeedMap', () => {
  it('shows error when API key is missing', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: '' },
    })
    expect(wrapper.find('.map-error').exists()).toBe(true)
  })

  it('renders loading state initially with API key', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: 'test-key' },
    })
    // After mount without API loaded, loading is true
    expect(wrapper.vm.loading).toBe(true)
  })
})