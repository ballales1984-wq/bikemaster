import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

import CoachPanel from './CoachPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockAthletes = {
  athletes: [{ id: 1, name: 'Marco Rossi' }],
}

const mockCoachData = {
  training_advice: 'Increase volume gradually',
  recovery_advice: 'Sleep 8+ hours nightly',
  historical_analysis: 'Performance improved 10% last month',
  training_scores: [
    { label: 'Performance', value: 88 },
    { label: 'Endurance', value: 76 },
    { label: 'Efficiency', value: 91 },
  ],
}

describe('CoachPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads first athlete and displays coach data', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/athletes')
    expect(apiGet).toHaveBeenCalledWith('/api/v1/coach/full', { athlete_id: 1 })
    expect(wrapper.text()).toContain('88')
    expect(wrapper.text()).toContain('Increase volume gradually')
  })

  it('displays recovery advice and historical analysis', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('Sleep 8+ hours nightly')
    expect(wrapper.text()).toContain('Performance improved 10% last month')
  })

  it('shows all training scores', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('Performance')
    expect(wrapper.text()).toContain('Endurance')
    expect(wrapper.text()).toContain('Efficiency')
    expect(wrapper.text()).toContain('76')
    expect(wrapper.text()).toContain('91')
  })

  it('shows empty state when no athletes', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] })

    const wrapper = mount(CoachPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/athletes')
    expect(wrapper.text()).toContain('No coach data')
  })

  it('handles athlete API failure gracefully', async () => {
    apiGet.mockRejectedValueOnce(new Error('API error'))

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('renders form grid with athlete selector', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.form-grid').exists()).toBe(true)
    expect(wrapper.find('#coach-athlete-id').exists()).toBe(true)
  })

  it('displays button text correctly', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('Load Full Coach')
  })

  it('has AI Coach title', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('h2').text()).toContain('AI Coach')
  })

  it('shows stat cards after loading coach data', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.findAll('.stat-card').length).toBe(3)
  })

  it('shows training advice sections after loading', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('Training Advice')
    expect(wrapper.text()).toContain('Historical Analysis')
    expect(wrapper.text()).toContain('Recovery Advice')
  })

  it('displays stats container after coach data loaded', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.stats').exists()).toBe(true)
  })
})
