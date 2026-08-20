const CACHE_NAME = 'matchday-v2';
// '/' is intentionally excluded: it renders per-user content (login
// state, VIP badge), so it must never be served from a stale cache.
const urlsToCache = [
    '/static/predictions/styles.css',
    '/static/predictions/theme.css',
    '/static/predictions/app.js'
];

self.addEventListener('install', function(event) {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(urlsToCache);
        })
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(names) {
            return Promise.all(
                names.filter(function(name) { return name !== CACHE_NAME; })
                     .map(function(name) { return caches.delete(name); })
            );
        }).then(function() { return self.clients.claim(); })
    );
});

self.addEventListener('fetch', function(event) {
    // Never cache navigation requests (page loads) -- always go to the
    // network so login/VIP state is always current. Only static assets
    // use cache-first.
    if (event.request.mode === 'navigate') {
        event.respondWith(fetch(event.request));
        return;
    }
    event.respondWith(
        caches.match(event.request).then(function(response) {
            return response || fetch(event.request);
        })
    );
});
