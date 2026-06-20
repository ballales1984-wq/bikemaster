import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('isLoggedIn is false initially', async () => {
    const { useAuthStore } = await import('./auth')
    const store = useAuthStore()
    expect(store.isLoggedIn).toBe(false)
  })

  it('isAdmin is false initially', async () => {
    const { useAuthStore } = await import('./auth')
    const store = useAuthStore()
    expect(store.isAdmin).toBe(false)
  })

  it('getAuthHeader returns empty object when no token', async () => {
    const { useAuthStore } = await import('./auth')
    const store = useAuthStore()
    expect(store.getAuthHeader()).toEqual({})
  })

  it('parseJWTPayload handles invalid token', async () => {
    const { useAuthStore } = await import('./auth')
    const store = useAuthStore()
    expect(store.parseJWTPayload('invalid')).toBe(null)
  })

  it('setAuthFromUrl sets token and user', async () => {
    const { useAuthStore } = await import('./auth')
    const store = useAuthStore()
    store.setAuthFromUrl('test-token', 'test@example.com')
    expect(store.token).toBe('test-token')
    expect(store.user?.username).toBe('test@example.com')
  })
})