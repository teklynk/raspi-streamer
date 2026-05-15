// Minimal Service Worker for PWA Installability
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
    // The browser requires a fetch handler to be present
    // to trigger the "Add to Home Screen" prompt.
    event.respondWith(fetch(event.request));
});