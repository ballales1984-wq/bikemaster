import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiPost = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiPost }))

describe('useAuth composable', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('isLoggedIn returns correct value', async () => {
      const { isLoggedIn } = await import('../composables/useAuth.ts')
      expect(isLoggedIn()).toBe(false)
  })

  it('getAuthHeader returns empty object when no token', async () => {
      const { getAuthHeader } = await import('../composables/useAuth.ts')
      expect(getAuthHeader()).toEqual({})
  })

  it('parseJWTPayload handles invalid token', async () => {
      const { parseJWTPayload } = await import('../composables/useAuth.ts')
      expect(parseJWTPayload('invalid')).toBe(null)
  })
})
