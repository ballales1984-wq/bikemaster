import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ContactUs from '../views/ContactUs.vue'

describe('ContactUs', () => {
  it('renders the page title', () => {
    const wrapper = mount(ContactUs)
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('has contact form', () => {
    const wrapper = mount(ContactUs)
    expect(wrapper.find('form').exists()).toBe(true)
  })
})