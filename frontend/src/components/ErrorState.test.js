import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ErrorState from './ErrorState.vue'

describe('ErrorState', () => {
  it('renders title, message and retry action', async () => {
    const wrapper = mount(ErrorState, {
      props: {
        title: 'Errore rete',
        message: 'Connessione non disponibile',
      },
    })

    expect(wrapper.text()).toContain('Errore rete')
    expect(wrapper.text()).toContain('Connessione non disponibile')
    expect(wrapper.get('.retry-btn')).toBeTruthy()
  })

  it('hides retry when disabled', () => {
    const wrapper = mount(ErrorState, { props: { showRetry: false } })

    expect(wrapper.find('.retry-btn').exists()).toBe(false)
  })

  it('emits retry when clicked', async () => {
    const wrapper = mount(ErrorState)

    await wrapper.get('.retry-btn').trigger('click')

    expect(wrapper.emitted().retry).toEqual([[]])
  })
})
