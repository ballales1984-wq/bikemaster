const STATIC_CACHE = 'bikemaster-static-v5'
const API_CACHE = 'bikemaster-api-v1'

self.addEventListener('install', event => {
  self.skipWaiting()
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll([
      '/index.html',
      '/registerSW.js',
      '/manifest.json',
      '/manifest.webmanifest',
      '/pwa-192x192.png',
      '/pwa-512x512.png',
      '/favicon.svg',
      '/apple-touch-icon.png',
    ])),
  )
})

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys()
    await Promise.all(
      keys
        .filter(key => ![STATIC_CACHE, API_CACHE].includes(key))
        .map(key => caches.delete(key)),
    )
    await self.clients.claim()
  })())
})

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE)
  const cached = await cache.match(request)
  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response && response.ok) {
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const index = await cache.match('/index.html')
    return index || new Response('', { status: 504, statusText: 'Gateway Timeout' })
  }
}

async function navigationFallback(request) {
  const cache = await caches.open(STATIC_CACHE)
  try {
    const response = await fetch(request)
    if (response && response.ok) {
      cache.put('/index.html', response.clone())
    }
    if (response && !response.ok) {
      const cached = await cache.match('/index.html')
      if (cached) return cached
    }
    return response
  } catch {
    const cached = await cache.match('/index.html')
    return cached || new Response('Offline', { status: 503, statusText: 'Offline' })
  }
}

self.addEventListener('fetch', event => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (request.mode === 'navigate' && url.pathname === '/api/v1/auth/google/callback') {
    return
  }
  if (request.mode === 'navigate') {
    event.respondWith(navigationFallback(request))
    return
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request))
    return
  }

  if (url.origin === self.location.origin) {
    event.respondWith(cacheFirst(request))
  }
})
