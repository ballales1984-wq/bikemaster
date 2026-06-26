import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import RideTracking from '../views/RideTracking.vue'

vi.mock('../stores/trackingStore', () => ({
  useTrackingStore: () => ({
    isTracking: { value: false },
    isPaused: { value: false },
    start: vi.fn(),
    stop: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    addPoint: vi.fn(),
    updateMetrics: vi.fn(),
    resetMetrics: vi.fn(),
    setGpxPath: vi.fn(),
    setGpxBlob: vi.fn(),
    toGpx: vi.fn(() => ''),
    routePoints: [],
    gpxPath: null,
    gpxBlob: null,
  }),
}))

vi.mock('../utils/api', () => ({
  apiUpload: vi.fn(),
}))

vi.mock('../components/LiveMap.vue', () => ({
  default: { template: '<div class="live-map-stub" />' },
}))

vi.mock('../components/RideMetricsPanel.vue', () => ({
  default: { template: '<div class="metrics-panel-stub" />' },
}))

describe('RideTracking', () => {
  it('renders empty state when not tracking', () => {
    const wrapper = mount(RideTracking)
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('has start tracking button', () => {
    const wrapper = mount(RideTracking)
    const btn = wrapper.find('.btn-primary')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Start')
  })

  it('renders header', () => {
    const wrapper = mount(RideTracking)
    expect(wrapper.find('h2').exists()).toBe(true)
    expect(wrapper.find('h2').text()).toContain('Tracking')
  })
})