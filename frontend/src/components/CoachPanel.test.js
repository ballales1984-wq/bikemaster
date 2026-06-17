import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

import CoachPanel from './CoachPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

describe('CoachPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads the first athlete and displays coach data', async () => {
    apiGet
      .mockResolvedValueOnce({ athletes: [{ id: 42 }] })
      .mockResolvedValueOnce({
        training_advice: 'Aggiungi una seduta Z2',
        recovery_advice: 'Dormi almeno 8 ore',
        training_scores: [
          { label: 'Performance', value: 88 },
          { label: 'Endurance', value: 76 },
          { label: 'Efficiency', value: 91 },
        ],
      })

    const wrapper = mount(CoachPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/athletes')
    expect(apiGet).toHaveBeenCalledWith('/api/v1/coach/full', { athlete_id: 42 })
    expect(wrapper.find('#coach-athlete-id').element.value).toBe('42')
    expect(wrapper.find('.stat-card').text()).toContain('88')
    expect(wrapper.get('.result-box').text()).toContain('Aggiungi una seduta Z2')
  })

  it('does not request coach data when no athlete exists', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] })

    const wrapper = mount(CoachPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Nessun dato coach')
  })
})
