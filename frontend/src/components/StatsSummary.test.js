import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatsSummary from './StatsSummary.vue'

describe('StatsSummary', () => {
  it('formats summary metrics', () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: {
          rides: 12,
          distance_km: 128.456,
          calories: 3200,
          avg_speed_kmh: 27.5,
          duration_minutes: 150,
        },
      },
    })

    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('128.5')
    expect(wrapper.text()).toContain('3200')
    expect(wrapper.text()).toContain('27.5')
    expect(wrapper.text()).toContain('2.5')
  })

  it('emits refresh when clicked', async () => {
    const wrapper = mount(StatsSummary)

    await wrapper.get('.stat-refresh').trigger('click')

    expect(wrapper.emitted().refresh).toEqual([[]])
  })

  it('disables refresh while loading', () => {
    const wrapper = mount(StatsSummary, { props: { loading: true } })

    expect(wrapper.get('.stat-refresh').attributes('disabled')).toBe('')
  })
})
