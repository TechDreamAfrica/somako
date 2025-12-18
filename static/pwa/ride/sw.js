// Soma Ko Ride - Service Worker
const CACHE_NAME = 'somako-ride-v1';
const urlsToCache = [
  '/ride/dashboard/',
  '/static/css/custom.css',
  '/static/pwa/ride/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        const responseToCache = response.clone();
        caches.open(CACHE_NAME)
          .then((cache) => cache.put(event.request, responseToCache));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New update from Soma Ko Ride',
    icon: '/static/pwa/ride/icon-192x192.png',
    badge: '/static/pwa/ride/icon-96x96.png',
    vibrate: [200, 100, 200],
  };
  event.waitUntil(
    self.registration.showNotification('Soma Ko Ride', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/ride/dashboard/'));
});
