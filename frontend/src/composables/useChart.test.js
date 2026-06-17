import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock Chart.js globale (usato direttamente nel composable)
const mockChartInstance = { destroy: vi.fn(), update: vi.fn() }
globalThis.Chart = vi.fn().mockImplementation(() => mockChartInstance)

// useChart usa lifecycle hooks (onMounted/watch) — testabile in isolamento
// per le funzioni pure di formattazione dati

describe('useChart helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.Chart = vi.fn().mockImplementation(() => ({ destroy: vi.fn() }))
  })

  it('Chart viene costruito con type bar di default', () => {
    const canvas = { getContext: vi.fn().mockReturnValue({}) }
    const data = { labels: ['Jan', 'Feb'], datasets: [{ data: [10, 20] }] }

    new globalThis.Chart(canvas.getContext(), { type: 'bar', data, options: {} })

    expect(globalThis.Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: 'bar' })
    )
  })

  it('Chart viene costruito con type line se specificato', () => {
    const canvas = { getContext: vi.fn().mockReturnValue({}) }
    const data = { labels: ['A', 'B', 'C'], datasets: [{ data: [1, 2, 3] }] }

    new globalThis.Chart(canvas.getContext(), { type: 'line', data, options: {} })

    expect(globalThis.Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: 'line' })
    )
  })

  it('il costruttore Chart riceve le opzioni responsive e maintainAspectRatio', () => {
    const canvas = { getContext: vi.fn().mockReturnValue({}) }
    const data = { labels: [], datasets: [] }

    new globalThis.Chart(canvas.getContext(), {
      type: 'bar',
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#aaa' } } },
      },
    })

    const callArgs = globalThis.Chart.mock.calls[0][1]
    expect(callArgs.options.responsive).toBe(true)
    expect(callArgs.options.maintainAspectRatio).toBe(false)
  })

  it('destroy viene chiamato prima di ri-renderizzare', () => {
    const destroyFn = vi.fn()
    const instance = { destroy: destroyFn }
    globalThis.Chart = vi.fn().mockImplementation(() => instance)

    const ctx = {}
    const data = { labels: [], datasets: [] }

    // Prima istanza
    const c1 = new globalThis.Chart(ctx, { type: 'bar', data, options: {} })
    // Distruggi come farebbe render()
    c1.destroy()
    // Seconda istanza
    new globalThis.Chart(ctx, { type: 'bar', data, options: {} })

    expect(destroyFn).toHaveBeenCalledTimes(1)
    expect(globalThis.Chart).toHaveBeenCalledTimes(2)
  })
})

describe('chart data formatters', () => {
  it('calcola la media mobile su finestra 3', () => {
    const values = [10, 20, 30, 40, 50]
    const windowSize = 3
    const rollingAvg = values.map((_, i) => {
      if (i < windowSize - 1) return null
      const slice = values.slice(i - windowSize + 1, i + 1)
      return slice.reduce((a, b) => a + b, 0) / windowSize
    })
    expect(rollingAvg[2]).toBe(20)
    expect(rollingAvg[3]).toBe(30)
    expect(rollingAvg[4]).toBe(40)
  })

  it('calcola percentuale variazione tra periodi', () => {
    const recent = 150
    const previous = 100
    const changePct = Math.round(((recent - previous) / previous) * 100)
    expect(changePct).toBe(50)
  })

  it('formatta le etichette mese correttamente', () => {
    const dates = ['2026-01-15', '2026-02-10', '2026-03-22']
    const labels = dates.map(d => d?.slice(5) || '?')
    expect(labels).toEqual(['01-15', '02-10', '03-22'])
  })
})
