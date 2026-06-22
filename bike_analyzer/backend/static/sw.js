const i = "bikemaster-static-v1", c = "bikemaster-api-v1";
self.addEventListener("install", (t) => {
  self.skipWaiting(), t.waitUntil(
    caches.open(i).then((a) => a.addAll([
      "/index.html",
      "/registerSW.js",
      "/manifest.json",
      "/manifest.webmanifest",
      "/pwa-192x192.png",
      "/pwa-512x512.png",
      "/favicon.svg",
      "/apple-touch-icon.png"
    ]))
  );
});
self.addEventListener("activate", (t) => {
  t.waitUntil((async () => {
    const a = await caches.keys();
    await Promise.all(
      a.filter((e) => ![i, c].includes(e)).map((e) => caches.delete(e))
    ), await self.clients.claim();
  })());
});
async function s(t) {
  const a = await caches.open(i), e = await a.match(t);
  if (e) return e;
  try {
    const n = await fetch(t);
    return n && n.ok && a.put(t, n.clone()), n;
  } catch (_) {
    return null;
  }
}
async function o(t) {
  const c = await (await caches.open(i)).match("/index.html");
  if (c) return c;
  try {
    const n = await fetch(t);
    if (n && n.ok) await (await caches.open(i)).put(t, n.clone());
    return n;
  } catch (_) {
    return null;
  }
}
self.addEventListener("fetch", (t) => {
  const { request: a } = t;
  if (a.method !== "GET") return;
  const e = new URL(a.url);
  if (a.mode === "navigate") {
    t.respondWith(o(a));
    return;
  }
  if (e.pathname.startsWith("/api/")) {
    t.respondWith(fetch(a));
    return;
  }
  e.origin === self.location.origin && t.respondWith(s(a));
});
