const API_BASE = ''

async function apiGet(path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  const url = qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`GET ${path}: ${resp.status}`)
  return resp.json()
}

async function apiPost(path, body) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) throw new Error(`POST ${path}: ${resp.status}`)
  return resp.json()
}

async function apiDelete(path) {
  const resp = await fetch(`${API_BASE}${path}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`DELETE ${path}: ${resp.status}`)
  return resp.json()
}

async function apiUpload(path, file) {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${API_BASE}${path}`, { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`UPLOAD ${path}: ${resp.status}`)
  return resp.json()
}

export { apiGet, apiPost, apiDelete, apiUpload }
