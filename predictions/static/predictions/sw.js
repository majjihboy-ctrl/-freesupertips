const CACHE_NAME = 'matchday-v3';
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
        event.respondWith(
            fetch(event.request).catch(function() {
                // Network failed entirely (offline, DNS hiccup, etc).
                // Fall back to whatever cached shell we have, if any,
                // rather than letting the fetch reject uncaught.
                return caches.match(event.request).then(function(cached) {
                    return cached || new Response(
                        '<!doctype html><title>Offline</title>' +
                        '<p style="font-family:sans-serif;padding:2rem;">' +
                        'You appear to be offline. Please check your connection and try again.</p>',
                        { headers: { 'Content-Type': 'text/html' } }
                    );
                });
            })
        );
        return;
    }
    event.respondWith(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.match(event.request).then(function(cached) {
                // Always refresh the cache in the background, even when we
                // have a cached copy to serve immediately. This is what
                // keeps static assets from going permanently stale after a
                // deploy -- previously, a cache hit meant the network was
                // never touched again until CACHE_NAME changed by hand.
                var networkUpdate = fetch(event.request).then(function(response) {
                    if (response && response.ok) {
                        cache.put(event.request, response.clone());
                    }
                    return response;
                }).catch(function() {
                    // Network unavailable -- fall back to whatever's cached,
                    // or a clean 504 rather than an uncaught rejection.
                    return cached || new Response('', { status: 504, statusText: 'Network error' });
                });
                return cached || networkUpdate;
            });
        })
    );
});
