import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AboutUs from '../views/AboutUs.vue'

describe('AboutUs', () => {
  it('renders the page title', () => {
    const wrapper = mount(AboutUs)
    expect(wrapper.find('h1').text()).toContain('BikeMaster')
  })

  it('has feature cards', () => {
    const wrapper = mount(AboutUs)
    const cards = wrapper.findAll('.feature-card')
    expect(cards.length).toBeGreaterThanOrEqual(5)
  })

  it('displays tech stack information', () => {
    const wrapper = mount(AboutUs)
    expect(wrapper.text()).toContain('Vue 3')
    expect(wrapper.text()).toContain('FastAPI')
  })
})