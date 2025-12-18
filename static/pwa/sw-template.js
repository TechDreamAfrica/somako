/**
 * Soma Ko PWA Service Worker Template
 *
 * Usage: Copy this template and replace the following variables:
 * - {{APP_NAME}}: Application name (e.g., 'food', 'rent', 'shop', 'pharmacy', 'ride')
 * - {{APP_TITLE}}: Display title (e.g., 'Food', 'Rent', 'Shop')
 * - {{THEME_COLOR}}: Theme color hex code
 * - {{CACHE_URLS}}: Array of URLs to cache
 */

// Configuration - Replace these values
const APP_NAME = '{{APP_NAME}}'; // e.g., 'food', 'rent', 'shop'
const APP_TITLE = '{{APP_TITLE}}'; // e.g., 'Food', 'Rent'
const THEME_COLOR = '{{THEME_COLOR}}'; // e.g., '#ef4444'

// Cache Configuration
const CACHE_VERSION = 'v2';
const CACHE_STATIC = `somako-${APP_NAME}-static-${CACHE_VERSION}`;
const CACHE_RUNTIME = `somako-${APP_NAME}-runtime-${CACHE_VERSION}`;
const CACHE_IMAGES = `somako-${APP_NAME}-images-${CACHE_VERSION}`;
const CACHE_API = `somako-${APP_NAME}-api-${CACHE_VERSION}`;

// Static resources to cache
const STATIC_RESOURCES = [
  `/${APP_NAME}/dashboard/`,
  '/static/css/custom.css',
  `/static/pwa/${APP_NAME}/manifest.json`,
  `/static/pwa/${APP_NAME}/icon-192x192.png`,
  `/static/pwa/${APP_NAME}/icon-512x512.png`,
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
];

const OFFLINE_PAGE = `/${APP_NAME}/offline/`;

// Install Event
self.addEventListener('install', (event) => {
  console.log(`[${APP_TITLE} SW] Installing...`);

  event.waitUntil(
    caches.open(CACHE_STATIC)
      .then((cache) => {
        console.log(`[${APP_TITLE} SW] Caching static resources`);
        return cache.addAll(STATIC_RESOURCES.map(url => new Request(url, { cache: 'reload' })));
      })
      .then(() => self.skipWaiting())
      .catch((error) => console.error(`[${APP_TITLE} SW] Cache failed:`, error))
  );
});

// Activate Event
self.addEventListener('activate', (event) => {
  console.log(`[${APP_TITLE} SW] Activating...`);

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName.startsWith(`somako-${APP_NAME}-`) &&
              ![CACHE_STATIC, CACHE_RUNTIME, CACHE_IMAGES, CACHE_API].includes(cacheName)) {
            console.log(`[${APP_TITLE} SW] Deleting old cache:`, cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => self.clients.claim())
  );
});

// Fetch Event - Smart caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // API requests - Network First
  if (url.pathname.startsWith('/api/') || url.pathname.includes(`/${APP_NAME}/api/`)) {
    event.respondWith(networkFirst(request, CACHE_API));
    return;
  }

  // Images - Cache First
  if (request.destination === 'image' || /\.(jpg|jpeg|png|gif|svg|webp)$/i.test(url.pathname)) {
    event.respondWith(cacheFirst(request, CACHE_IMAGES));
    return;
  }

  // Static assets - Cache First
  if (request.destination === 'style' || request.destination === 'script' ||
      request.destination === 'font' || /\.(css|js|woff|woff2|ttf|otf)$/i.test(url.pathname)) {
    event.respondWith(cacheFirst(request, CACHE_STATIC));
    return;
  }

  // HTML pages - Network First with offline fallback
  if (request.destination === 'document' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstWithFallback(request));
    return;
  }

  // Default - Stale While Revalidate
  event.respondWith(staleWhileRevalidate(request, CACHE_RUNTIME));
});

// Caching Strategies
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response?.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    return cached || Promise.reject(error);
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response?.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return Promise.reject(error);
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cached = await caches.match(request);

  const fetchPromise = fetch(request).then((response) => {
    if (response?.status === 200) {
      caches.open(cacheName).then(cache => cache.put(request, response.clone()));
    }
    return response;
  });

  return cached || fetchPromise;
}

async function networkFirstWithFallback(request) {
  try {
    const response = await fetch(request);
    if (response?.status === 200) {
      const cache = await caches.open(CACHE_RUNTIME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;

    const offlinePage = await caches.match(OFFLINE_PAGE);
    if (offlinePage) return offlinePage;

    return new Response(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Offline - Soma Ko ${APP_TITLE}</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              min-height: 100vh;
              margin: 0;
              background: #f3f4f6;
              color: #1f2937;
            }
            .container {
              text-align: center;
              padding: 2rem;
            }
            .icon {
              font-size: 4rem;
              margin-bottom: 1rem;
            }
            h1 { color: ${THEME_COLOR}; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="icon">📡</div>
            <h1>You're Offline</h1>
            <p>Please check your internet connection and try again.</p>
          </div>
        </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Background Sync
self.addEventListener('sync', (event) => {
  console.log(`[${APP_TITLE} SW] Background sync:`, event.tag);

  if (event.tag.startsWith('sync-')) {
    event.waitUntil(syncData(event.tag));
  }
});

async function syncData(tag) {
  try {
    const db = await openDB();
    const data = await getPendingData(db, tag);

    for (const item of data) {
      await fetch(`/${APP_NAME}/api/sync/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      });
    }

    await clearPendingData(db, tag);
    console.log(`[${APP_TITLE} SW] Sync completed:`, tag);
  } catch (error) {
    console.error(`[${APP_TITLE} SW] Sync failed:`, error);
    throw error;
  }
}

// Push Notifications
self.addEventListener('push', (event) => {
  console.log(`[${APP_TITLE} SW] Push received`);

  let data = {
    title: `Soma Ko ${APP_TITLE}`,
    body: 'New update available',
    icon: `/static/pwa/${APP_NAME}/icon-192x192.png`,
    badge: `/static/pwa/${APP_NAME}/icon-96x96.png`,
  };

  if (event.data) {
    try {
      const pushData = event.data.json();
      data = { ...data, ...pushData };
    } catch (error) {
      console.error(`[${APP_TITLE} SW] Push data parse error:`, error);
    }
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
      tag: data.tag || `${APP_NAME}-notification`,
      data: data,
      vibrate: [200, 100, 200],
      actions: [
        { action: 'view', title: 'View' },
        { action: 'dismiss', title: 'Dismiss' }
      ]
    })
  );
});

// Notification Click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const urlToOpen = event.notification.data?.url || `/${APP_NAME}/dashboard/`;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes(`/${APP_NAME}/`) && 'focus' in client) {
            return client.focus().then(() => client.navigate(urlToOpen));
          }
        }
        return clients.openWindow(urlToOpen);
      })
  );
});

// Periodic Background Sync
self.addEventListener('periodicsync', (event) => {
  console.log(`[${APP_TITLE} SW] Periodic sync:`, event.tag);

  if (event.tag === 'update-data') {
    event.waitUntil(updateAppData());
  }
});

async function updateAppData() {
  try {
    const response = await fetch(`/${APP_NAME}/api/updates/`);
    const data = await response.json();

    const db = await openDB();
    await saveAppData(db, data);

    console.log(`[${APP_TITLE} SW] Data updated`);
  } catch (error) {
    console.error(`[${APP_TITLE} SW] Update failed:`, error);
  }
}

// IndexedDB Helpers
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(`SomaKo${APP_TITLE}DB`, 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('appData')) {
        db.createObjectStore('appData', { keyPath: 'id' });
      }
    };
  });
}

async function getPendingData(db, tag) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['syncQueue'], 'readonly');
    const store = tx.objectStore('syncQueue');
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result.filter(item => item.tag === tag));
    request.onerror = () => reject(request.error);
  });
}

async function clearPendingData(db, tag) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['syncQueue'], 'readwrite');
    const store = tx.objectStore('syncQueue');
    const request = store.clear();
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function saveAppData(db, data) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['appData'], 'readwrite');
    const store = tx.objectStore('appData');
    const request = store.put(data);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// Message Handler
self.addEventListener('message', (event) => {
  console.log(`[${APP_TITLE} SW] Message:`, event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (event.data.type === 'CLIENTS_CLAIM') {
    self.clients.claim();
  }
});

console.log(`[${APP_TITLE} SW] Loaded successfully`);
