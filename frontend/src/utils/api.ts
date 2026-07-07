import { useAuthStore } from '../stores/auth'

const API_BASE = ''

function clearAuth() {
  localStorage.removeItem('bikemaster_token')
  localStorage.removeItem('bikemaster_user')
}

let sessionExpiredNotified = false

function notifySessionExpired() {
  const toast = (window as unknown as { __toast?: { add?: (msg: string, type?: string, ms?: number) => void } }).__toast
  if (toast?.add && !sessionExpiredNotified) {
    toast.add('Sessione scaduta. Effettua di nuovo il login.', 'error')
    sessionExpiredNotified = true
  }
  const auth = useAuthStore()
  if (auth.isLoggedIn) {
    void auth.logout().catch(() => {})
  }
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('bikemaster_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

interface ApiResponse {
  [key: string]: unknown
}

function extractErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { detail?: unknown })?.detail
  if (detail == null) return fallback
  if (typeof detail === "string") return detail
  // FastAPI 422 validation errors return detail as an array of {loc, msg, type}
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg?: unknown }).msg) : String(d)))
      .filter(Boolean)
    return messages.length ? messages.join("; ") : fallback
  }
  try {
    return JSON.stringify(detail)
  } catch {
    return fallback
  }
}

async function apiGet(path: string, params: Record<string, string | number> = {}, options: RequestInit = {}): Promise<ApiResponse> {
  const qs = new URLSearchParams(params as Record<string, string>).toString()
  const url = qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`
  const resp = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth()
      notifySessionExpired()
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(extractErrorMessage(err, `GET ${path}: ${resp.status}`))
  }
  return resp.json()
}

async function apiPost(path: string, body: unknown, options: RequestInit = {}): Promise<ApiResponse> {
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: isForm ? { ...authHeaders(), ...(options.headers as Record<string, string> || {}) } : { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
    body: isForm ? body as BodyInit : JSON.stringify(body),
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth()
      notifySessionExpired()
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(extractErrorMessage(err, `POST ${path}: ${resp.status}`))
  }
  return resp.json()
}

async function apiDelete(path: string, options: RequestInit = {}): Promise<ApiResponse> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: { ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth()
      notifySessionExpired()
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(extractErrorMessage(err, `DELETE ${path}: ${resp.status}`))
  }
  return resp.json()
}

async function apiUpload(path: string, file: Blob | File, options: RequestInit = {}): Promise<ApiResponse> {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
    body: form,
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth()
      notifySessionExpired()
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(extractErrorMessage(err, `UPLOAD ${path}: ${resp.status}`))
  }
  return resp.json()
}

async function apiPut(path: string, body: unknown, options: RequestInit = {}): Promise<ApiResponse> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
    body: JSON.stringify(body),
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth()
      notifySessionExpired()
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(extractErrorMessage(err, `PUT ${path}: ${resp.status}`))
  }
  return resp.json()
}

export { apiGet, apiPost, apiDelete, apiUpload, apiPut }
