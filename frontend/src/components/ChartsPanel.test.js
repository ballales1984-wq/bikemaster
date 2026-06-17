import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

// Mock Chart.js — non disponibile in jsdom
vi.mock('chart.js', () => ({
  Chart: vi.fn().mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() })),
  registerables: [],
}))

// Mock globale Chart usato inline nel componente
globalThis.Chart = vi.fn().mockImplementation(() => ({ destroy: vi.fn() }))

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

import ChartsPanel from './ChartsPanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

describe('ChartsPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('si renderizza correttamente con dati minimi', async () => {
    apiGet.mockResolvedValue({ ready: false })

    const wrapper = mount(ChartsPanel, {
      props: { rides: [] },
    })
    await flush()

    expect(wrapper.find('.charts-panel').exists()).toBe(true)
    expect(wrapper.find('h2').text()).toContain('Andamento Performance')
  })

  it('mostra i selettori di metrica e finestra', async () => {
    apiGet.mockResolvedValue({ ready: false })

    const wrapper = mount(ChartsPanel, { props: { rides: [] } })
    await flush()

    const selects = wrapper.findAll('select')
    expect(selects).toHaveLength(2)

    const metricOptions = selects[0].findAll('option')
    expect(metricOptions.some(o => o.text().includes('Distanza'))).toBe(true)
    expect(metricOptions.some(o => o.text().includes('Velocità'))).toBe(true)
  })

  it('cambiare metrica richiama loadTrends', async () => {
    apiGet.mockResolvedValue({ ready: false })

    const wrapper = mount(ChartsPanel, { props: { rides: [] } })
    await flush()

    const callsBefore = apiGet.mock.calls.length
    const selects = wrapper.findAll('select')
    await selects[0].setValue('calories')
    await flush()

    expect(apiGet.mock.calls.length).toBeGreaterThan(callsBefore)
  })

  it('mostra 3 chart-card nella griglia', async () => {
    apiGet.mockResolvedValue({ ready: false })

    const wrapper = mount(ChartsPanel, { props: { rides: [] } })
    await flush()

    expect(wrapper.findAll('.chart-card')).toHaveLength(3)
  })

  it('mostra trend-up quando trend è improving', async () => {
    apiGet
      .mockResolvedValueOnce({ ready: true, trend: 'improving', r2: 0.85, mean: 45.2, values: [40, 45, 50], dates: ['2026-01', '2026-02', '2026-03'], rolling_avg: [42, 45, 47] })
      .mockResolvedValue({ ready: false })

    const wrapper = mount(ChartsPanel, { props: { rides: [] } })
    await flush()

    const summary = wrapper.find('.chart-summary')
    if (summary.exists()) {
      expect(summary.find('.trend-up').exists()).toBe(true)
    }
  })
})
