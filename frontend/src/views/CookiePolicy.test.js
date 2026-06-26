import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CookiePolicy from '../views/CookiePolicy.vue'

describe('CookiePolicy', () => {
  it('renders the page title', () => {
    const wrapper = mount(CookiePolicy)
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('has multiple sections', () => {
    const wrapper = mount(CookiePolicy)
    const sections = wrapper.findAll('h2')
    expect(sections.length).toBeGreaterThan(3)
  })

  it('mentions technical cookies', () => {
    const wrapper = mount(CookiePolicy)
    expect(wrapper.text()).toContain('access_token')
  })
})