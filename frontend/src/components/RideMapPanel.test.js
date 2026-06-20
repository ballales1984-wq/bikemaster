import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      addLayer: vi.fn().mockReturnThis(),
      remove: vi.fn(),
      fitBounds: vi.fn().mockReturnThis(),
      invalidateSize: vi.fn().mockReturnThis(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn().mockReturnThis() })),
    layerGroup: vi.fn(() => ({
      clearLayers: vi.fn(),
      addLayer: vi.fn().mockReturnThis(),
    })),
    polyline: vi.fn(() => ({ addTo: vi.fn().mockReturnThis() })),
    latLngBounds: vi.fn(() => ({
      extend: vi.fn().mockReturnThis(),
      isValid: vi.fn(() => true),
      pad: vi.fn().mockReturnThis(),
    })),
    circleMarker: vi.fn(() => ({
      bindPopup: vi.fn().mockReturnThis(),
      addTo: vi.fn().mockReturnThis(),
    })),
  },
}))

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

vi.mock('../utils/routeMap', () => ({
  buildRidePolylines: vi.fn(() => [{ color: '#4ecca3', points: [[45.46, 9.19], [45.47, 9.20]] }]),
  escapeHtml: vi.fn((v) => String(v)),
  formatDistance: vi.fn((m) => `${(m / 1000).toFixed(2)} km`),
  gradeRiskPercent: vi.fn(() => 25),
  riskColor: vi.fn(() => '#27ae60'),
  speedRiskPercent: vi.fn(() => 30),
  weatherRiskPercent: vi.fn(() => 20),
}))

import RideMapPanel from './RideMapPanel.vue'

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

const mockRides = {
  rides: [
    {
      id: 1,
      date: '2026-06-01',
      distance_km: 42.5,
      duration_minutes: 90,
      avg_speed_kmh: 28.3,
      gps_points: [
        { lat: 45.46, lon: 9.19, altitude: 100 },
        { lat: 45.47, lon: 9.20, altitude: 110 },
      ],
    },
  ],
  total: 1,
}

describe('RideMapPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders panel with title', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.text()).toContain('Route Maps')
  })

  it('has map container', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.find('#route-map').exists()).toBe(true)
  })

  it('has update button', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.find('.btn-primary').exists()).toBe(true)
  })

  it('has coloring mode selector', () => {
    const wrapper = mount(RideMapPanel)
    const selects = wrapper.findAll('select')
    expect(selects.length).toBeGreaterThanOrEqual(1)
  })

  it('has weather toggle checkbox', () => {
    const wrapper = mount(RideMapPanel)
    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
  })

  it('has risk levels defined', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.vm.riskLevels.length).toBe(4)
  })

  it('has grade legend defined', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.vm.gradeLegend.length).toBe(4)
  })

  it('has speed legend defined', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.vm.speedLegend.length).toBe(3)
  })

  it('formats distances correctly', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.vm.formatDistance(5000)).toBe('5.00 km')
  })

  it('has demo route points', () => {
    const wrapper = mount(RideMapPanel)
    expect(wrapper.vm.demoRoutePoints.length).toBeGreaterThan(0)
  })
})