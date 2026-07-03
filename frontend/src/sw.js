import { registerRoute, setCatchHandler } from 'workbox-routing'
import { CacheFirst, StaleWhileRevalidate, NetworkFirst } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'
import { precacheAndRoute, matchPrecache, addRoute } from 'workbox-precaching'
import { setCacheNameDetails } from 'workbox-core'
import { BackgroundSyncPlugin } from 'workbox-background-sync'

setCacheNameDetails({
  prefix: 'bikemaster',
  suffix: 'v1',
})

const STATIC_CACHE = 'bikemaster-static-v6'
const API_CACHE = 'bikemaster-api-v1'
const IMAGE_CACHE = 'bikemaster-images-v1'
const RIDE_QUEUE_CACHE = 'bikemaster-ride-queue-v1'

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
    ])).then(() => {
      if (self.registration.navigationPreload) {
        return self.registration.navigationPreload.enable().catch(() => {})
      }
    }),
  )
})

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys()
    await Promise.all(
      keys
        .filter(key => ![STATIC_CACHE, API_CACHE, IMAGE_CACHE, RIDE_QUEUE_CACHE].includes(key))
        .map(key => caches.delete(key)),
    )
    await self.clients.claim()
  })())
})

precacheAndRoute(self.__WB_MANIFEST || [])

const bgSyncPlugin = new BackgroundSyncPlugin(RIDE_QUEUE_CACHE, {
  maxRetentionTime: 24 * 60,
  onSync: async ({queue}) => {
    let entry
    while ((entry = await queue.shiftRequest())) {
      const {request} = entry
      try {
        await fetch(request)
      } catch (error) {
        await queue.pushRequest(entry)
        throw error
      }
    }
  },
})

registerRoute(
  ({ request }) => request.mode === 'navigate',
  async ({ event }) => {
    try {
      const response = await fetch(event.request)
      if (response.ok) return response
    } catch (_) { /* network error, fall through */ }
    const cache = await caches.open(STATIC_CACHE)
    return await cache.match('/index.html') || new Response('', { status: 503, statusText: 'Offline' })
  },
)

registerRoute(
  ({ url }) => url.pathname.startsWith('/api/') && url.pathname.includes('rides'),
  new NetworkFirst({
    cacheName: API_CACHE,
    plugins: [
      bgSyncPlugin,
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 60,
      }),
    ],
  }),
)

registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: API_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 60,
      }),
    ],
  }),
)

registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: IMAGE_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 30 * 24 * 60 * 60,
      }),
    ],
  }),
)

registerRoute(
  ({ url }) => url.origin === self.location.origin && url.pathname.startsWith('/'),
  new StaleWhileRevalidate({
    cacheName: STATIC_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 24 * 60 * 60,
      }),
    ],
  }),
)

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {}
  const title = data.title || 'BikeMaster'
  const options = {
    body: data.body || 'Ride tracking update',
    icon: '/pwa-192x192.png',
    badge: '/pwa-192x192.png',
    data: data.url || '/',
    tag: data.tag || 'bikemaster-notification',
    renotify: true,
    actions: data.actions || [
      { action: 'open', title: 'Open App' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const action = event.action
  const url = event.notification.data || '/'
  if (action === 'dismiss') {
    return
  }
  event.waitUntil(clients.openWindow(url))
})

self.addEventListener('periodicsync', event => {
  if (event.tag === 'sync-rides') {
    event.waitUntil((async () => {
      const cache = await caches.open(RIDE_QUEUE_CACHE)
      const requests = await cache.keys()
      for (const request of requests) {
        const response = await fetch(request)
        if (response.ok) {
          await cache.delete(request)
        }
      }
    })())
  }
})