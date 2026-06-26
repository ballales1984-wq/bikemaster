import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmModal from '../components/ConfirmModal.vue'

describe('ConfirmModal', () => {
  it('renders with default props', () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    })
    expect(wrapper.find('h3').text()).toBe('Confirm')
    expect(wrapper.find('p').text()).toBe('Are you sure?')
  })

  it('renders custom title and message', () => {
    const wrapper = mount(ConfirmModal, {
      props: {
        modelValue: true,
        title: 'Delete Ride',
        message: 'Are you sure you want to delete this ride?',
      },
    })
    expect(wrapper.find('h3').text()).toBe('Delete Ride')
    expect(wrapper.find('p').text()).toBe('Are you sure you want to delete this ride?')
  })

  it('emits confirm when confirm button is clicked', async () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    })
    await wrapper.find('.btn-danger').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
  })

  it('emits cancel when cancel button is clicked', async () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    })
    await wrapper.find('.btn-secondary').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
  })
})