import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
const apiPost = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet, apiPost }))

import CoachPanel from './CoachPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockAthletes = {
  athlete: { id: 1, name: 'Marco Rossi' },
}

const mockCoachData = {
  training_scores: [
    { label: 'Performance', value: 88 },
    { label: 'Endurance', value: 76 },
    { label: 'Efficiency', value: 91 },
  ],
}

const mockChatResponse = {
  response: 'Increase volume gradually',
}

describe('CoachPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads first athlete on mount', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/athletes/me')
  })

  it('displays AI Coach title', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('h2').text()).toContain('coach.title')
  })

  it('shows score pills after loading coach data', async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockCoachData)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('88')
  })

  it('has chat input', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.chat-input').exists()).toBe(true)
  })

  it('has chat input', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.chat-input').exists()).toBe(true)
  })

  it('has send button', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.send-btn').exists()).toBe(true)
  })

  it('has quick action buttons', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.findAll('.quick-btn').length).toBeGreaterThan(0)
  })

  it('shows welcome message in chat', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('coach.welcome')
  })

  it('has Report button for full coach data', async () => {
    apiGet.mockResolvedValueOnce(mockAthletes)

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.text()).toContain('coach.report')
  })

  it('handles athlete API failure gracefully', async () => {
    apiGet.mockRejectedValueOnce(new Error('API error'))

    const wrapper = mount(CoachPanel)
    await flush()

    expect(wrapper.find('.coach-panel').exists()).toBe(true)
  })
})