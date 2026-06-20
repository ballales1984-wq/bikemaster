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
    })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    })
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/rides')
    const items = wrapper.findAll('.ride-item')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('42.5')
    expect(items[1].text()).toContain('2026-06-08')
  })

  it('shows empty state when no rides', async () => {
    apiGet.mockResolvedValueOnce({ rides: [] })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    })
    await flush()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('No rides recorded')
  })

  it('adds a ride by filling the form', async () => {
    apiGet
      .mockResolvedValueOnce({ rides: [] })
      .mockResolvedValueOnce({ rides: [{ id: 10, date: '2026-06-15', distance_km: 50, duration_minutes: 120, avg_speed_kmh: 25 }] })
    apiPost.mockResolvedValueOnce({ id: 10 })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    })
    await flush()

    await wrapper.find('input[type="date"]').setValue('2026-06-15')
    await wrapper.findAll('input[type="number"]')[0].setValue('50')
    await wrapper.findAll('input[type="number"]')[1].setValue('120')
    await wrapper.find('form').trigger('submit')
    await flush()

    expect(apiPost).toHaveBeenCalledWith('/api/v1/rides', expect.objectContaining({
      date: '2026-06-15',
      distance_km: 50,
      duration_minutes: 120,
    }))
  })

  it('opens confirm modal on Delete click', async () => {
    apiGet.mockResolvedValueOnce({
      rides: [{ id: 5, date: '2026-05-20', distance_km: 30, duration_minutes: 70, avg_speed_kmh: 25 }],
    })

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: { template: '<div class="confirm-modal-stub" />' } } },
    })
    await flush()

    await wrapper.find('.btn-danger').trigger('click')
    expect(wrapper.vm.showDeleteModal).toBe(true)
    expect(wrapper.vm.deleteTargetId).toBe(5)
  })
})
