import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ErrorBoundary from './ErrorBoundary.vue'

describe('ErrorBoundary', () => {
  it('renders default slot when no error', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div class="child">Safe content</div>',
      },
    })
    expect(wrapper.find('.child').exists()).toBe(true)
  })

  it('shows error UI when error is set via wrapper setData', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div class="safe">OK</div>',
      },
    })
    expect(wrapper.find('.error-boundary').exists()).toBe(false)

    await wrapper.setData({ error: 'boom' })
    await nextTick()
    expect(wrapper.find('.error-boundary').exists()).toBe(true)
    expect(wrapper.text()).toContain('Something went wrong')
    expect(wrapper.text()).toContain('boom')

    await wrapper.find('button').trigger('click')
    await nextTick()
    expect(wrapper.find('.error-boundary').exists()).toBe(false)
    expect(wrapper.find('.safe').exists()).toBe(true)
  })
})
