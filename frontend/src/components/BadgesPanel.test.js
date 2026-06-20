import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

import BadgesPanel from './BadgesPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockBadgesData = {
  achieved: 3,
  total_badges: 10,
  badges: [
    { id: 1, category: 'milestone', name: 'First Ride', description: 'First ride completed', icon: '🎯', progress: 100, achieved: true },
    { id: 2, category: 'distance', name: '100km Club', description: '100km total', icon: '📏', progress: 80, achieved: false },
    { id: 3, category: 'speed', name: 'Speedster', description: '40km/h peak', icon: '⚡', progress: 50, achieved: false },
  ],
}

describe('BadgesPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads athlete and badges on mount', async () => {
    apiGet
      .mockResolvedValueOnce({ athletes: [{ id: 7 }] })
      .mockResolvedValueOnce(mockBadgesData)

    const wrapper = mount(BadgesPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/athletes')
    expect(apiGet).toHaveBeenCalledWith('/api/v1/badges', { athlete_id: 7 })
    expect(wrapper.text()).toContain('3/10')
  })

  it('shows correct completion percentage', async () => {
    apiGet
      .mockResolvedValueOnce({ athletes: [{ id: 1 }] })
      .mockResolvedValueOnce(mockBadgesData)

    const wrapper = mount(BadgesPanel)
    await flush()

    // 3/10 = 30%
    const progressFill = wrapper.find('.progress-fill')
    expect(progressFill.exists()).toBe(true)
    expect(progressFill.attributes('style')).toContain('30')
  })

  it('shows badges by category', async () => {
    apiGet
      .mockResolvedValueOnce({ athletes: [{ id: 1 }] })
      .mockResolvedValueOnce(mockBadgesData)

    const wrapper = mount(BadgesPanel)
    await flush()

    const cards = wrapper.findAll('.badge-card')
    expect(cards.length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('First Ride')
    expect(wrapper.text()).toContain('100km Club')
  })

  it('achieved badge has CSS class achieved', async () => {
    apiGet
      .mockResolvedValueOnce({ athletes: [{ id: 1 }] })
      .mockResolvedValueOnce(mockBadgesData)

    const wrapper = mount(BadgesPanel)
    await flush()

    const achievedCards = wrapper.findAll('.badge-card.achieved')
    expect(achievedCards).toHaveLength(1)
  })

  it('does not load badges if no athlete found', async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] })

    const wrapper = mount(BadgesPanel)
    await flush()

    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.badges-container').exists()).toBe(false)
  })
})
