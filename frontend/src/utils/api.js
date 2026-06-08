const API_BASE = ''

function authHeaders() {
  const token = localStorage.getItem('bikemaster_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function apiGet(path, params = {}, options = {}) {
  const qs = new URLSearchParams(params).toString()
  const url = qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`
  const resp = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers || {}) },
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('bikemaster_token')
      localStorage.removeItem('bikemaster_user')
      window.location.href = '/'
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `GET ${path}: ${resp.status}`)
  }
  return resp.json()
}

async function apiPost(path, body, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers || {}) },
    body: JSON.stringify(body),
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('bikemaster_token')
      localStorage.removeItem('bikemaster_user')
      window.location.href = '/'
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `POST ${path}: ${resp.status}`)
  }
  return resp.json()
}

async function apiDelete(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: { ...authHeaders(), ...(options.headers || {}) },
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('bikemaster_token')
      localStorage.removeItem('bikemaster_user')
      window.location.href = '/'
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `DELETE ${path}: ${resp.status}`)
  }
  return resp.json()
}

async function apiUpload(path, file, options = {}) {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { ...authHeaders(), ...(options.headers || {}) },
    body: form,
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('bikemaster_token')
      localStorage.removeItem('bikemaster_user')
      window.location.href = '/'
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `UPLOAD ${path}: ${resp.status}`)
  }
  return resp.json()
}

async function apiPut(path, body, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers || {}) },
    body: JSON.stringify(body),
    ...options,
  })
  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('bikemaster_token')
      localStorage.removeItem('bikemaster_user')
      window.location.href = '/'
    }
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `PUT ${path}: ${resp.status}`)
  }
  return resp.json()
}

export { apiGet, apiPost, apiDelete, apiUpload, apiPut }
