const API_BASE = ''

function clearAuth() {
  localStorage.removeItem('bikemaster_token')
  localStorage.removeItem('bikemaster_user')
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('bikemaster_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

interface ApiResponse {
  [key: string]: unknown
}

async function apiGet(path: string, params: Record<string, string> = {}, options: RequestInit = {}): Promise<ApiResponse> {
  const qs = new URLSearchParams(params).toString()
  const url = qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`
  const resp = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth()
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error((err as Record<string, string>).detail || `GET ${path}: ${resp.status}`)
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
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error((err as Record<string, string>).detail || `POST ${path}: ${resp.status}`)
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
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error((err as Record<string, string>).detail || `DELETE ${path}: ${resp.status}`)
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
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error((err as Record<string, string>).detail || `UPLOAD ${path}: ${resp.status}`)
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
      throw new Error('expired')
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error((err as Record<string, string>).detail || `PUT ${path}: ${resp.status}`)
  }
  return resp.json()
}

export { apiGet, apiPost, apiDelete, apiUpload, apiPut }
