const STATIC_CACHE = 'bikemaster-static-v2'
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

  const response = await fetch(request)
  if (response && response.ok) {
    cache.put(request, response.clone())
  }
  return response
}

async function navigationFallback(request) {
  const cache = await caches.open(STATIC_CACHE)
  const cached = await cache.match('/index.html')
  return cached || fetch(request)
}

self.addEventListener('fetch', event => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
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
