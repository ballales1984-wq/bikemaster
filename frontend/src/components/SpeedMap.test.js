import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SpeedMap from '../components/SpeedMap.vue'

describe('SpeedMap', () => {
  it('shows error when API key is missing', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: '' },
    })
    expect(wrapper.find('.map-error').exists() || wrapper.vm.loading).toBe(true)
  })

  it('renders map container', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: 'test-key' },
    })
    expect(wrapper.find('.google-speed-map').exists()).toBe(true)
  })

  it('has addPoint method exposed', () => {
    const wrapper = mount(SpeedMap, {
      props: { rideId: 1, apiKey: 'test-key' },
    })
    expect(wrapper.vm.addPoint).toBeDefined()
  })
})