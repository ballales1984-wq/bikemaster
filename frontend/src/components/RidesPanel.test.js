import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
const apiPost = vi.hoisted(() => vi.fn())
const apiDelete = vi.hoisted(() => vi.fn())

vi.mock('../utils/api.ts', () => ({ apiGet, apiPost, apiDelete }))

import RidesPanel from './RidesPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

describe('RidesPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the list of loaded rides', async () => {
    apiGet.mockResolvedValueOnce({
      rides: [
        { id: 1, date: '2026-06-01', distance_km: 42.5, duration_minutes: 90, avg_speed_kmh: 28.3 },
        { id: 2, date: '2026-06-08', distance_km: 25.0, duration_minutes: 60, avg_speed_kmh: 25.0 },
      ],
      total: 2,
    })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    })
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/rides', { limit: 200 })
    const items = wrapper.findAll('.ride-item')
    expect(items).toHaveLength(2)
  })

  it('shows empty state when no rides', async () => {
    apiGet.mockResolvedValueOnce({ rides: [], total: 0 })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    })
    await flush()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('Nessuna uscita registrata')
  })

  it('adds a ride by filling the form', async () => {
    apiGet
      .mockResolvedValueOnce({ rides: [], total: 0 })
      .mockResolvedValueOnce({ rides: [{ id: 10, date: '2026-06-15', distance_km: 50, duration_minutes: 120, avg_speed_kmh: 25 }], total: 1 })
    apiPost.mockResolvedValueOnce({ id: 10 })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    })
    await flush()

    // Open form
    await wrapper.find('.add-header').trigger('click')
    await flush()

    // Fill form fields
    const dateInput = wrapper.find('input[type="date"]')
    const numberInputs = wrapper.findAll('input[type="number"]')
    await dateInput.setValue('2026-06-15')
    await numberInputs[0].setValue('50')
    await numberInputs[1].setValue('120')
    await wrapper.find('form').trigger('submit')
    await flush()

    expect(apiPost).toHaveBeenCalledWith('/api/v1/rides', expect.objectContaining({
      date: '2026-06-15',
      distance_km: 50,
      duration_minutes: 120,
    }))
  })

  it('opens ride detail on click', async () => {
    apiGet.mockResolvedValueOnce({
      rides: [{ id: 5, date: '2026-05-20', distance_km: 30, duration_minutes: 70, avg_speed_kmh: 25 }],
      total: 1,
    })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: { template: '<div class="confirm-modal-stub" />' } } },
    })
    await flush()

    // Click on the first ride
    await wrapper.findAll('.ride-item')[0].trigger('click')
    await flush()

    // verify the ride detail modal opens (selectedRide is set)
    expect(wrapper.vm.selectedRide).toBeTruthy()
  })
})