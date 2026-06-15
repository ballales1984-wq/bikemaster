import { describe, it, expect } from 'vitest'

describe('useAuth composable', () => {
    it('isLoggedIn returns correct value', async () => {
        const { isLoggedIn } = await import('../composables/useAuth.js')
        expect(isLoggedIn()).toBe(false)
    })

    it('getAuthHeader returns empty object when no token', async () => {
        const { getAuthHeader } = await import('../composables/useAuth.js')
        expect(getAuthHeader()).toEqual({})
    })

    it('parseJWTPayload handles invalid token', async () => {
        const { parseJWTPayload } = await import('../composables/useAuth.js')
        expect(parseJWTPayload('invalid')).toBe(null)
    })
})
