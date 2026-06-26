import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SpeedMap from '../components/SpeedMap.vue'

describe('SpeedMap', () => {
  it('renders map container', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: 'test-key' },
    })
    expect(wrapper.find('.google-speed-map').exists()).toBe(true)
  })

  it('has loading state initially', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: 'test-key' },
    })
    expect(wrapper.vm.loading).toBe(true)
  })
})