/* Minimal service worker for PWA installability. */
const CACHE_NAME = 'fuel-req-v1';

self.addEventListener('install', function (event) {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function (event) {
  /* Always use network for the app; no offline caching of Streamlit UI. */
  event.respondWith(fetch(event.request).catch(function () {
    return new Response(
      '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Offline</title></head>' +
      '<body><p>You are offline. Please check your connection and reload.</p></body></html>',
      { headers: { 'Content-Type': 'text/html' } }
    );
  }));
});
