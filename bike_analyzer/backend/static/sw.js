const CACHE_NAME = 'bikemaster-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/static/index.html',
    '/static/styles.css',
    '/static/app.js',
    '/static/manifest.json',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(ASSETS_TO_CACHE))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys => 
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request).catch(() => {
            return new Response(JSON.stringify({ error: 'Offline - dati non disponibili' }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }));
        return;
    }
    event.respondWith(
        caches.match(event.request)
            .then(resp => resp || fetch(event.request))
            .catch(() => {
                if (event.request.mode === 'navigate') {
                    return caches.match('/static/index.html');
                }
            })
    );
});