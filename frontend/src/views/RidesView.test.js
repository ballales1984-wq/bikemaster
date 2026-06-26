import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import RidesView from '../views/RidesView.vue'

vi.mock('../components/RidesPanel.vue', () => ({
  default: { template: '<div class="rides-panel-stub" />' },
}))

describe('RidesView', () => {
  it('renders welcome section', () => {
    const wrapper = mount(RidesView, {
      global: { stubs: { RouterLink: true } },
    })
    expect(wrapper.find('.welcome-card').exists()).toBe(true)
  })

  it('has welcome title', () => {
    const wrapper = mount(RidesView, {
      global: { stubs: { RouterLink: true } },
    })
    expect(wrapper.find('h2').text()).toContain('Bentornato')
  })
})