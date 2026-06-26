import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrivacyPolicy from '../views/PrivacyPolicy.vue'

describe('PrivacyPolicy', () => {
  it('renders the page title', () => {
    const wrapper = mount(PrivacyPolicy)
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('has multiple sections', () => {
    const wrapper = mount(PrivacyPolicy)
    const sections = wrapper.findAll('h2')
    expect(sections.length).toBeGreaterThan(5)
  })

  it('mentions GDPR', () => {
    const wrapper = mount(PrivacyPolicy)
    expect(wrapper.text()).toContain('GDPR')
  })
})