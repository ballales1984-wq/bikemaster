self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function () {
  self.clients.claim().catch(() => {});
});

self.addEventListener("message", function (event) {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

import { registerRoute, setCatchHandler } from "workbox-routing";
import {
  CacheFirst,
  StaleWhileRevalidate,
  NetworkFirst,
} from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";
import {
  precacheAndRoute,
  matchPrecache,
  addRoute,
  cleanupOutdatedCaches,
} from "workbox-precaching";
import { setCacheNameDetails } from "workbox-core";
import { BackgroundSyncPlugin } from "workbox-background-sync";

setCacheNameDetails({
  prefix: "bikemaster",
  suffix: "v2",
});

const STATIC_CACHE = "bikemaster-static-v8";
const API_CACHE = "bikemaster-api-v1";
const IMAGE_CACHE = "bikemaster-images-v1";
const RIDE_QUEUE_CACHE = "bikemaster-ride-queue-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) =>
        cache.addAll([
          "/index.html",
          "/registerSW.js",
          "/manifest.json",
          "/pwa-192x192.png",
          "/pwa-512x512.png",
          "/favicon.svg",
          "/apple-touch-icon.png",
        ]),
      )
      .then(() => {
        if (self.registration.navigationPreload) {
          return self.registration.navigationPreload.enable().catch(() => {});
        }
      }),
  );
});

// Must run during the initial evaluation of the worker script: it registers
// its own `activate` listener. Calling it from inside an `activate` handler
// throws "Event handler of 'activate' event must be added on the initial
// evaluation of worker script."
cleanupOutdatedCaches();

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter(
            (key) =>
              ![
                STATIC_CACHE,
                API_CACHE,
                IMAGE_CACHE,
                RIDE_QUEUE_CACHE,
              ].includes(key),
          )
          .map((key) => caches.delete(key)),
      );
      await self.clients.claim().catch(() => {});
    })(),
  );
});

// Navigation handler MUST be registered before `precacheAndRoute` so it wins
// over Workbox's precache route. Workbox's precache route matches "/" requests
// (SPA directory index) and would otherwise serve a *stale* cached index.html
// whose hashed JS/CSS chunks were deleted by a newer deploy — breaking the app
// boot on OAuth returns and forcing a manual refresh to log in.
registerRoute(
  ({ request }) =>
    request.mode === "navigate" && !request.url.includes("/api/"),
  async ({ event }) => {
    try {
      const response = await fetch(event.request.url, {
        cache: "no-store",
        redirect: "follow",
      });
      if (response.ok) return response;
      // opaqueredirect can appear if the browser did not follow a redirect
      // (e.g. Chrome inherits redirect:"manual" from navigation requests
      // inside service workers).  Never return a redirect/opaqueredirect
      // for a navigation — fall through to the precached shell instead.
      if (response.type === "opaqueredirect") {
        throw new TypeError("opaque redirect received for navigation");
      }
    } catch (_) {
      /* network error, redirect or opaque-redirect — fall through to cache */
    }
    try {
      const cache = await caches.open(STATIC_CACHE);
      const cached = await cache.match("/index.html");
      if (cached) return cached;
    } catch (_) {
      /* cache error, fall through to offline response */
    }
    return new Response("", { status: 503, statusText: "Offline" });
  },
);

precacheAndRoute(self.__WB_MANIFEST || []);

const bgSyncPlugin = new BackgroundSyncPlugin(RIDE_QUEUE_CACHE, {
  maxRetentionTime: 24 * 60,
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftRequest())) {
      const { request } = entry;
      try {
        await fetch(request);
      } catch (error) {
        await queue.pushRequest(entry);
        throw error;
      }
    }
  },
});

// Only handle *same-origin* API requests. When the frontend is deployed on a
// different origin than the backend (e.g. Vercel SPA -> ngrok/Render backend),
// cross-origin /api calls must fall through to the browser's normal CORS
// handling. Intercepting them here produces opaque/duplicate "no-response"
// errors in the service worker and adds no value (we never cache third-party
// responses meaningfully).
function isSameOriginApi(url) {
  return (
    url.origin === self.location.origin && url.pathname.startsWith("/api/")
  );
}

registerRoute(
  ({ url }) => isSameOriginApi(url) && url.pathname.includes("rides"),
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
);

registerRoute(
  ({ url }) =>
    isSameOriginApi(url) &&
    (url.pathname.includes("/auth/") || url.pathname.includes("/auth")),
  new NetworkFirst({
    cacheName: API_CACHE,
    plugins: [new ExpirationPlugin({ maxEntries: 10, maxAgeSeconds: 0 })],
  }),
);

registerRoute(
  ({ url }) => isSameOriginApi(url),
  new NetworkFirst({
    cacheName: API_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 60,
      }),
    ],
  }),
);

registerRoute(
  ({ request, url }) =>
    request.destination === "image" && url.origin === self.location.origin,
  new CacheFirst({
    cacheName: IMAGE_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 30 * 24 * 60 * 60,
      }),
    ],
  }),
);

registerRoute(
  ({ request }) =>
    (request.destination === "script" || request.destination === "style") &&
    request.url.startsWith(self.location.origin),
  new NetworkFirst({
    cacheName: STATIC_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 24 * 60 * 60,
      }),
    ],
  }),
  );

self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || "BikeMaster";
  const options = {
    body: data.body || "Ride tracking update",
    icon: "/pwa-192x192.png",
    badge: "/pwa-192x192.png",
    data: data.url || "/",
    tag: data.tag || "bikemaster-notification",
    renotify: true,
    actions: data.actions || [
      { action: "open", title: "Open App" },
      { action: "dismiss", title: "Dismiss" },
    ],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const action = event.action;
  const url = event.notification.data || "/";
  if (action === "dismiss") {
    return;
  }
  event.waitUntil(clients.openWindow(url));
});

self.addEventListener("periodicsync", (event) => {
  if (event.tag === "sync-rides") {
    event.waitUntil(
      (async () => {
        const cache = await caches.open(RIDE_QUEUE_CACHE);
        const requests = await cache.keys();
        for (const request of requests) {
          const response = await fetch(request);
          if (response.ok) {
            await cache.delete(request);
          }
        }
      })(),
    );
  }
});
