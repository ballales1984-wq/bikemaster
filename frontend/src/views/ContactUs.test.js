import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ContactUs from '../views/ContactUs.vue'

describe('ContactUs', () => {
  it('renders the page title', () => {
    const wrapper = mount(ContactUs, {
      global: { stubs: { RouterLink: true } },
    })
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('has email contact info', () => {
    const wrapper = mount(ContactUs, {
      global: { stubs: { RouterLink: true } },
    })
    const infoCards = wrapper.findAll('.info-card')
    expect(infoCards.length).toBeGreaterThanOrEqual(2)
  })

  it('has useful links section', () => {
    const wrapper = mount(ContactUs, {
      global: { stubs: { RouterLink: true } },
    })
    expect(wrapper.find('.links-grid').exists()).toBe(true)
  })
})