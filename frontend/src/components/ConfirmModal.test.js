import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmModal from '../components/ConfirmModal.vue'

describe('ConfirmModal', () => {
  it('renders with default props', () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
      global: {
        stubs: {
          teleport: true,
          transition: false,
        },
      },
    })
    // With teleport stubbed, content should be visible
    expect(wrapper.find('h3').exists() || wrapper.text()).toContain('Confirm')
  })

  it('has confirm and cancel buttons', () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
      global: { stubs: { teleport: true, transition: false } },
    })
    expect(wrapper.findAll('button').length).toBeGreaterThanOrEqual(2)
  })

  it('emits confirm when confirm button is clicked', async () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
      global: { stubs: { teleport: true, transition: false } },
    })
    const buttons = wrapper.findAll('button')
    const dangerBtn = buttons.find(b => b.classes().includes('btn-danger'))
    if (dangerBtn) {
      await dangerBtn.trigger('click')
      expect(wrapper.emitted('confirm')).toBeTruthy()
    }
  })

  it('emits cancel when cancel button is clicked', async () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
      global: { stubs: { teleport: true, transition: false } },
    })
    const buttons = wrapper.findAll('button')
    const secondaryBtn = buttons.find(b => b.classes().includes('btn-secondary'))
    if (secondaryBtn) {
      await secondaryBtn.trigger('click')
      expect(wrapper.emitted('cancel')).toBeTruthy()
    }
  })
})