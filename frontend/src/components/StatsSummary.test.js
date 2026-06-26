import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import StatsSummary from '../components/StatsSummary.vue'

describe('StatsSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders zero stats when props are null', () => {
    const wrapper = mount(StatsSummary, {
      props: { stats: null, loading: false },
    })
    const values = wrapper.findAll('.stat-value')
    // StatsSummary shows values with units (0 km, 0 h) or just numbers
    expect(values[0].text()).toBe('0')
    expect(values[1].text()).toContain('0')
    expect(values[2].text()).toBe('0')
    expect(values[3].text()).toContain('0')
    expect(values[4].text()).toContain('0')
  })

  it('renders rides count', async () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: { rides: 42, calories: 1234, distance_km: 0, avg_speed_kmh: 0, duration_minutes: 0 },
        loading: false,
      },
    })
    const values = wrapper.findAll('.stat-value')
    expect(values[0].text()).toBe('42')
  })

  it('formats distance with one decimal', async () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: { rides: 0, distance_km: 123.45, avg_speed_kmh: 0, calories: 0, duration_minutes: 0 },
        loading: false,
      },
    })
    const values = wrapper.findAll('.stat-value')
    expect(values[1].text()).toContain('123.5')
  })

  it('formats avg speed with one decimal', async () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: { rides: 0, distance_km: 0, avg_speed_kmh: 28.3, calories: 0, duration_minutes: 0 },
        loading: false,
      },
    })
    const values = wrapper.findAll('.stat-value')
    expect(values[3].text()).toContain('28.3')
  })

  it('converts duration_minutes to hours with one decimal', async () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: { rides: 0, distance_km: 0, avg_speed_kmh: 0, calories: 0, duration_minutes: 125 },
        loading: false,
      },
    })
    const values = wrapper.findAll('.stat-value')
    expect(values[4].text()).toContain('2.1')
  })

  it('shows 0 for NaN values', () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: { rides: NaN, distance_km: NaN, avg_speed_kmh: NaN, calories: NaN, duration_minutes: NaN },
        loading: false,
      },
    })
    const values = wrapper.findAll('.stat-value')
    expect(values[0].text()).toBe('0')
    expect(values[2].text()).toBe('0')
  })

  it('emits refresh when refresh button is clicked', async () => {
    const wrapper = mount(StatsSummary, {
      props: { stats: { rides: 0, distance_km: 0, avg_speed_kmh: 0, calories: 0, duration_minutes: 0 }, loading: false },
    })
    await wrapper.find('button.stat-refresh').trigger('click')
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })

  it('disables refresh button and shows loading text', () => {
    const wrapper = mount(StatsSummary, {
      props: { stats: { rides: 0, distance_km: 0, avg_speed_kmh: 0, calories: 0, duration_minutes: 0 }, loading: true },
    })
    const btn = wrapper.find('button.stat-refresh')
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.text()).toContain('Updating')
  })

  it('has accessible labels', () => {
    const wrapper = mount(StatsSummary, {
      props: { stats: { rides: 0, distance_km: 0, avg_speed_kmh: 0, calories: 0, duration_minutes: 0 }, loading: false },
    })
    expect(wrapper.find('[aria-label="General Statistics"]').exists()).toBe(true)
    expect(wrapper.findAll('[role="status"]').length).toBeGreaterThan(0)
  })
})