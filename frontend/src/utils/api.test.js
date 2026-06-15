import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiGet } from './api.ts'

class MemoryStorage {
  constructor() {
    this.store = new Map()
  }

  getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null
  }

  setItem(key, value) {
    this.store.set(key, String(value))
  }

  removeItem(key) {
    this.store.delete(key)
  }
}

describe('apiGet', () => {
  let storage

  beforeEach(() => {
    storage = new MemoryStorage()
    globalThis.localStorage = storage
    globalThis.window = { location: { href: '' } }
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete globalThis.window
    delete globalThis.localStorage
  })

  it('adds auth header and query parameters', async () => {
    storage.setItem('bikemaster_token', 'token-123')
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    })

    const result = await apiGet('/api/v1/rides', { limit: 2 })

    expect(result).toEqual({ ok: true })
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/rides?limit=2',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer token-123',
          'Content-Type': 'application/json',
        }),
      })
    )
  })

  it('clears auth state on 401 responses', async () => {
    storage.setItem('bikemaster_token', 'token-123')
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
    })

    await expect(apiGet('/api/v1/me')).rejects.toThrow('Unauthorized')

    expect(storage.getItem('bikemaster_token')).toBeNull()
    expect(globalThis.window.location.href).toBe('/')
  })
})
