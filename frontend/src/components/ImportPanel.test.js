import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ImportPanel from './ImportPanel.vue'
import * as api from '../utils/api'

function makeFile(name) {
  return new File(['ride'], name, { type: 'application/octet-stream' })
}

describe('ImportPanel', () => {
  it('mostra una barra di avanzamento mentre importa i file', async () => {
    vi.spyOn(api, 'apiUpload').mockResolvedValue({ id: 1 })

    const wrapper = mount(ImportPanel, {
      attachTo: document.body,
      global: {
        stubs: {
          Teleport: true,
        },
      },
    })

    const input = wrapper.find('input').element
    const event = new Event('change')
    Object.defineProperty(event, 'target', {
      value: { files: [makeFile('ride.gpx'), makeFile('second.fit')] },
    })
    input.dispatchEvent(event)
    await wrapper.vm.$nextTick()

    await wrapper.find('button').trigger('click')
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.progress-fill').attributes('style')).toContain('width: 100%')
    expect(wrapper.text()).toContain('Import completato')

    vi.restoreAllMocks()
  })
})
