import { describe, it, expect, vi } from 'vitest'

describe('useAuth composable', () => {
    it('isLoggedIn returns correct value', () => {
        const { isLoggedIn } = require('../../src/composables/useAuth.js')
        expect(isLoggedIn()).toBe(false)
    })

    it('getAuthHeader returns empty object when no token', () => {
        const { getAuthHeader } = require('../../src/composables/useAuth.js')
        expect(getAuthHeader()).toEqual({})
    })

    it('parseJWTPayload handles invalid token', () => {
        const { parseJWTPayload } = require('../../src/composables/useAuth.js')
        expect(parseJWTPayload('invalid')).toBe(null)
    })
})