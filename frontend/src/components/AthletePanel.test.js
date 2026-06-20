import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
const apiPost = vi.hoisted(() => vi.fn())
const apiPut = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet, apiPost, apiPut }))

import AthletePanel from './AthletePanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockAthlete = {
  id: 3,
  name: 'Marco Rossi',
  age: 35,
  weight_kg: 72,
  height_cm: 178,
  fat_percentage: 14,
  years_active: 5,
  weekly_sessions: 4,
  monthly_hours: 12,
  annual_hours: 144,
  experience_level: 'Intermediate',
}

describe('AthletePanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads existing athlete profile on mount', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [mockAthlete] })

    const wrapper = mount(AthletePanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/athletes')
    expect(wrapper.find('#athlete-name').element.value).toBe('Marco Rossi')
    expect(wrapper.find('#athlete-age').element.value).toBe('35')
    expect(wrapper.find('#athlete-weight').element.value).toBe('72')
  })

  it('saves new athlete (POST) if none exists', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] })
    apiPost.mockResolvedValueOnce({ id: 10 })

    const wrapper = mount(AthletePanel)
    await flush()

    await wrapper.find('#athlete-name').setValue('Luca Bianchi')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(apiPost).toHaveBeenCalledWith('/api/v1/athletes', expect.objectContaining({ name: 'Luca Bianchi' }))
    expect(wrapper.find('.result-box').text()).toContain('ID: 10')
  })

  it('updates existing athlete (PUT)', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [mockAthlete] })
    apiPut.mockResolvedValueOnce({ id: 3 })

    const wrapper = mount(AthletePanel)
    await flush()

    await wrapper.find('#athlete-name').setValue('Marco Verdi')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(apiPut).toHaveBeenCalledWith('/api/v1/athletes/3', expect.objectContaining({ name: 'Marco Verdi' }))
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('shows error if save fails', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] })
    apiPost.mockRejectedValueOnce(new Error('Server error'))

    const wrapper = mount(AthletePanel)
    await flush()

    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Error')
  })

  it('Scores button calls scores endpoint', async () => {
    apiGet
      .mockResolvedValueOnce({ athletes: [mockAthlete] })
      .mockResolvedValueOnce({ performance: 85, endurance: 78 })

    const wrapper = mount(AthletePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/scores/athlete/3')
  })
})
