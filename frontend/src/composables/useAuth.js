import { ref, computed } from 'vue'

const TOKEN_KEY = 'bikemaster_token'
const USER_KEY = 'bikemaster_user'

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const user = ref(() => {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
})

function isLoggedIn() {
  return !!token.value
}

function isAdmin() {
  return user.value?.is_admin === true
}

function getAuthHeader() {
  return token.value ? { Authorization: `Bearer ${token.value}` } : {}
}

function parseBase64Url(base64Url) {
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '=='.slice(0, (4 - (base64.length % 4)) % 4)
  return decodeURIComponent(
    Array.from(atob(padded))
      .map(c => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`)
      .join('')
  )
}

function parseJWTPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const decoded = parseBase64Url(parts[1])
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

async function login(username, password) {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  const resp = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Login fallito' }))
    throw new Error(err.detail || 'Login fallito')
  }
  const data = await resp.json()
  token.value = data.access_token
  const payload = parseJWTPayload(data.access_token)
  user.value = {
    id: Number(data.id || (payload?.sub ?? '')),
    username: payload?.sub ?? '',
    is_admin: !!payload?.is_admin,
  }
  localStorage.setItem(TOKEN_KEY, data.access_token)
  localStorage.setItem(USER_KEY, JSON.stringify(user.value))
}

function register(username, password) {
  return fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }).then(r => {
    if (!r.ok) throw new Error('Registrazione fallita')
    return r.json()
  })
}

async function logout() {
  try {
    const token = localStorage.getItem('bikemaster_token')
    if (token) {
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

const authToken = computed(() => token.value)
const authUser = computed(() => user.value)

export {
  isLoggedIn,
  isAdmin,
  getAuthHeader,
  login,
  register,
  logout,
  authToken,
  authUser,
}
