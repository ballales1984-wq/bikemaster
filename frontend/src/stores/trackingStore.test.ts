import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTrackingStore } from '../stores/trackingStore'

describe('trackingStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with default values', () => {
    const store = useTrackingStore()
    expect(store.isTracking).toBe(false)
    expect(store.isPaused).toBe(false)
    expect(store.distance).toBe(0)
    expect(store.currentSpeed).toBe(0)
    expect(store.avgSpeed).toBe(0)
  })

  it('starts tracking correctly', () => {
    const store = useTrackingStore()
    store.start()
    expect(store.isTracking).toBe(true)
    expect(store.isPaused).toBe(false)
  })

  it('pauses tracking', () => {
    const store = useTrackingStore()
    store.start()
    store.pause()
    expect(store.isPaused).toBe(true)
  })

  it('resumes tracking', () => {
    const store = useTrackingStore()
    store.start()
    store.pause()
    store.resume()
    expect(store.isPaused).toBe(false)
  })

  it('stops tracking', () => {
    const store = useTrackingStore()
    store.start()
    store.stop()
    expect(store.isTracking).toBe(false)
  })

  it('updates metrics correctly', () => {
    const store = useTrackingStore()
    store.updateMetrics({
      distance: 15000,
      currentSpeed: 25.5,
      avgSpeed: 22.0,
      elapsedTime: 3600,
      points: 500,
    })
    expect(store.distance).toBe(15000)
    expect(store.currentSpeed).toBe(25.5)
    expect(store.avgSpeed).toBe(22.0)
    expect(store.elapsedTime).toBe(3600)
    expect(store.points).toBe(500)
  })

  it('formats time correctly', () => {
    const store = useTrackingStore()
    store.elapsedTime = 3661
    expect(store.formattedTime).toBe('01:01:01')
  })

  it('formats distance correctly', () => {
    const store = useTrackingStore()
    store.distance = 12345
    expect(store.formattedDistance).toBe('12.35')
  })

  it('resets metrics', () => {
    const store = useTrackingStore()
    store.updateMetrics({ distance: 10000, currentSpeed: 25 })
    store.resetMetrics()
    expect(store.distance).toBe(0)
    expect(store.currentSpeed).toBe(0)
  })
})