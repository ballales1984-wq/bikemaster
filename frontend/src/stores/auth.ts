import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Athlete } from '../types/index'

const TOKEN_KEY = 'bikemaster_token'
const USER_KEY = 'bikemaster_user'
const JUST_LOGGED_IN_KEY = 'bikemaster_just_logged_in'

function parseBase64Url(base64Url: string): string {
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '=='.slice(0, (4 - (base64.length % 4)) % 4)
  return decodeURIComponent(
    Array.from(atob(padded))
      .map(c => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`)
      .join('')
  )
}

function parseJWTPayload(tokenStr: string): Record<string, unknown> | null {
  try {
    const parts = tokenStr.split('.')
    if (parts.length < 2) return null
    const decoded = parseBase64Url(parts[1])
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  
  const user = ref<Athlete | null>(
    (function() {
      try {
        const raw = localStorage.getItem(USER_KEY)
        return raw ? JSON.parse(raw) : null
      } catch {
        return null
      }
    })()
  )

  const justLoggedIn = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin === true)

  function isTokenValid(): boolean {
    if (!token.value) return false
    const payload = parseJWTPayload(token.value)
    if (!payload) return false
    const exp = payload.exp as number | undefined
    if (!exp) return true
    return Date.now() < exp * 1000
  }

  function getAuthHeader(): Record<string, string> {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {}
  }

  async function login(username: string, password: string): Promise<void> {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    const resp = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error((err as { detail?: string }).detail || 'Login failed')
    }
    const data = await resp.json()
    token.value = data.access_token
    const payload = parseJWTPayload(data.access_token)
    user.value = {
      id: typeof data.id === 'number' ? data.id : 0,
      username: typeof payload?.sub === 'string' ? payload.sub : '',
      is_admin: !!payload?.is_admin,
      tenant_id: typeof payload?.tenant_id === 'number' ? payload.tenant_id : (typeof data.id === 'number' ? data.id : 0),
    }
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function register(username: string, password: string): Promise<unknown> {
    return fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => {
      if (!r.ok) throw new Error('Registration failed')
      return r.json()
    })
  }

  async function logout(): Promise<void> {
    try {
      const currentToken = localStorage.getItem(TOKEN_KEY)
      if (currentToken) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { ...getAuthHeader() },
        }).catch(() => {})
      }
    } catch {}
  
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  function setAuthFromUrl(urlToken: string, email: string) {
    const payload = parseJWTPayload(urlToken)
    const userData = {
      username: email || '',
      email,
      is_admin: false,
      tenant_id: typeof payload?.tenant_id === 'number' ? payload.tenant_id : 0,
    }
    localStorage.setItem(TOKEN_KEY, urlToken)
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    token.value = urlToken
    user.value = userData
    localStorage.removeItem('bikemaster_login_error')
    localStorage.setItem(JUST_LOGGED_IN_KEY, 'true')
    justLoggedIn.value = true
  }

  function setOauthError(oauthError: string) {
    token.value = ''
    user.value = null
    localStorage.setItem('bikemaster_login_error', oauthError)
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    isTokenValid,
    getAuthHeader,
    login,
    register,
    logout,
    parseJWTPayload,
    setAuthFromUrl,
    setOauthError
  }
})
