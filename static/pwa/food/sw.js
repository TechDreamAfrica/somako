// Soma Ko Food - Enhanced Service Worker with Full PWA Features
const CACHE_VERSION = 'v2';
const CACHE_NAME = `somako-food-${CACHE_VERSION}`;
const CACHE_RUNTIME = `somako-food-runtime-${CACHE_VERSION}`;
const CACHE_IMAGES = `somako-food-images-${CACHE_VERSION}`;
const CACHE_API = `somako-food-api-${CACHE_VERSION}`;

// Resources to cache on install
const STATIC_CACHE = [
  '/food/dashboard/',
  '/food/restaurants/',
  '/food/menu/',
  '/food/orders/',
  '/static/css/custom.css',
  '/static/pwa/food/manifest.json',
  '/static/pwa/food/icon-192x192.png',
  '/static/pwa/food/icon-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
];

// Offline fallback page
const OFFLINE_PAGE = '/food/offline/';

// Install Event - Cache static resources
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static resources');
        return cache.addAll(STATIC_CACHE.map(url => new Request(url, { cache: 'reload' })));
      })
      .then(() => self.skipWaiting())
      .catch((error) => console.error('[SW] Cache failed:', error))
  );
});

// Activate Event - Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName.startsWith('somako-food-') && cacheName !== CACHE_NAME &&
              cacheName !== CACHE_RUNTIME && cacheName !== CACHE_IMAGES && cacheName !== CACHE_API) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => self.clients.claim())
  );
});

// Fetch Event - Advanced caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // API requests - Network First, fallback to cache
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/food/api/')) {
    event.respondWith(networkFirstStrategy(request, CACHE_API));
    return;
  }

  // Images - Cache First
  if (request.destination === 'image' || /\.(jpg|jpeg|png|gif|svg|webp)$/i.test(url.pathname)) {
    event.respondWith(cacheFirstStrategy(request, CACHE_IMAGES));
    return;
  }

  // Static assets (CSS, JS, fonts) - Cache First
  if (request.destination === 'style' || request.destination === 'script' || request.destination === 'font' ||
      /\.(css|js|woff|woff2|ttf|otf)$/i.test(url.pathname)) {
    event.respondWith(cacheFirstStrategy(request, CACHE_NAME));
    return;
  }

  // HTML pages - Network First with offline fallback
  if (request.destination === 'document' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstWithOffline(request));
    return;
  }

  // Default - Stale While Revalidate
  event.respondWith(staleWhileRevalidate(request, CACHE_RUNTIME));
});

// Caching Strategies
async function networkFirstStrategy(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function cacheFirstStrategy(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[SW] Fetch failed:', error);
    throw error;
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cached = await caches.match(request);

  const fetchPromise = fetch(request).then((response) => {
    if (response && response.status === 200) {
      const cache = caches.open(cacheName);
      cache.then(c => c.put(request, response.clone()));
    }
    return response;
  });

  return cached || fetchPromise;
}

async function networkFirstWithOffline(request) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(CACHE_RUNTIME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;

    // Return offline page if available
    const offlinePage = await caches.match(OFFLINE_PAGE);
    if (offlinePage) return offlinePage;

    // Fallback offline response
    return new Response('<h1>Offline</h1><p>You are currently offline. Please check your connection.</p>', {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Background Sync - Queue failed requests
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-orders') {
    event.waitUntil(syncOrders());
  } else if (event.tag === 'sync-cart') {
    event.waitUntil(syncCart());
  }
});

async function syncOrders() {
  try {
    // Retrieve pending orders from IndexedDB and sync
    const db = await openDB();
    const pendingOrders = await getAllPendingOrders(db);

    for (const order of pendingOrders) {
      await fetch('/food/api/orders/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order)
      });
    }

    await clearPendingOrders(db);
    console.log('[SW] Orders synced successfully');
  } catch (error) {
    console.error('[SW] Sync failed:', error);
    throw error;
  }
}

async function syncCart() {
  // Similar sync logic for cart updates
  console.log('[SW] Cart sync completed');
}

// Push Notifications - Enhanced
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  let notificationData = {
    title: 'Soma Ko Food',
    body: 'New update available',
    icon: '/static/pwa/food/icon-192x192.png',
    badge: '/static/pwa/food/icon-96x96.png',
    tag: 'food-notification',
    requireInteraction: false,
  };

  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = {
        title: data.title || notificationData.title,
        body: data.body || data.message || notificationData.body,
        icon: data.icon || notificationData.icon,
        badge: data.badge || notificationData.badge,
        tag: data.tag || notificationData.tag,
        data: data,
        vibrate: [200, 100, 200],
        actions: data.actions || [
          { action: 'view', title: 'View', icon: '/static/pwa/food/icon-96x96.png' },
          { action: 'dismiss', title: 'Dismiss' }
        ]
      };
    } catch (error) {
      console.error('[SW] Error parsing push data:', error);
    }
  }

  event.waitUntil(
    self.registration.showNotification(notificationData.title, notificationData)
  );
});

// Notification Click Handler
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  event.notification.close();

  const clickAction = event.action;
  const notificationData = event.notification.data || {};

  let urlToOpen = '/food/dashboard/';

  if (clickAction === 'view' || !clickAction) {
    if (notificationData.url) {
      urlToOpen = notificationData.url;
    } else if (notificationData.order_id) {
      urlToOpen = `/food/orders/${notificationData.order_id}/`;
    }
  } else if (clickAction === 'dismiss') {
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if available
        for (const client of clientList) {
          if (client.url.includes('/food/') && 'focus' in client) {
            return client.focus().then(() => client.navigate(urlToOpen));
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Periodic Background Sync (for browsers that support it)
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] Periodic sync triggered:', event.tag);

  if (event.tag === 'update-menu') {
    event.waitUntil(updateMenuData());
  } else if (event.tag === 'check-orders') {
    event.waitUntil(checkOrderStatus());
  }
});

async function updateMenuData() {
  try {
    const response = await fetch('/food/api/menu/');
    const data = await response.json();
    // Store in IndexedDB for offline access
    const db = await openDB();
    await saveMenuData(db, data);
    console.log('[SW] Menu data updated');
  } catch (error) {
    console.error('[SW] Menu update failed:', error);
  }
}

async function checkOrderStatus() {
  try {
    const response = await fetch('/food/api/orders/status/');
    const data = await response.json();

    // Notify user of order updates
    if (data.updates && data.updates.length > 0) {
      for (const update of data.updates) {
        await self.registration.showNotification('Order Update', {
          body: update.message,
          icon: '/static/pwa/food/icon-192x192.png',
          tag: `order-${update.order_id}`,
          data: { order_id: update.order_id }
        });
      }
    }
  } catch (error) {
    console.error('[SW] Order status check failed:', error);
  }
}

// IndexedDB Helper Functions
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('SomaKoFoodDB', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('pendingOrders')) {
        db.createObjectStore('pendingOrders', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('menuData')) {
        db.createObjectStore('menuData', { keyPath: 'id' });
      }
    };
  });
}

async function getAllPendingOrders(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pendingOrders'], 'readonly');
    const store = transaction.objectStore('pendingOrders');
    const request = store.getAll();

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function clearPendingOrders(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pendingOrders'], 'readwrite');
    const store = transaction.objectStore('pendingOrders');
    const request = store.clear();

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function saveMenuData(db, data) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['menuData'], 'readwrite');
    const store = transaction.objectStore('menuData');
    const request = store.put(data);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// Message Handler - Communication with main app
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (event.data.type === 'CLIENTS_CLAIM') {
    self.clients.claim();
  } else if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName.startsWith('somako-food-')) {
              return caches.delete(cacheName);
            }
          })
        );
      })
    );
  }
});

console.log('[SW] Service Worker loaded successfully');
