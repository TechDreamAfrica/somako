/**
 * PWA Utilities Module
 * Reusable functions for PWA functionality across all Soma Ko apps
 */

class PWAManager {
  constructor(config = {}) {
    this.config = {
      swPath: config.swPath || '/sw.js',
      scope: config.scope || '/',
      updateCheckInterval: config.updateCheckInterval || 60000, // 1 minute
      enableNotifications: config.enableNotifications !== false,
      enableBackgroundSync: config.enableBackgroundSync !== false,
      enablePeriodicSync: config.enablePeriodicSync !== false,
      ...config
    };

    this.registration = null;
    this.updateAvailable = false;
    this.deferredPrompt = null;
  }

  /**
   * Initialize PWA features
   */
  async init() {
    if ('serviceWorker' in navigator) {
      await this.registerServiceWorker();
      this.setupInstallPrompt();
      this.setupOnlineOfflineDetection();
      this.setupUpdateChecker();

      if (this.config.enableNotifications) {
        this.setupPushNotifications();
      }

      if (this.config.enablePeriodicSync) {
        this.setupPeriodicSync();
      }
    }
  }

  /**
   * Register Service Worker
   */
  async registerServiceWorker() {
    try {
      this.registration = await navigator.serviceWorker.register(
        this.config.swPath,
        { scope: this.config.scope }
      );

      console.log('[PWA] Service Worker registered:', this.registration);

      // Handle updates
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration.installing;

        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            this.updateAvailable = true;
            this.notifyUpdate();
          }
        });
      });

      // Listen for controlling service worker changes
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        window.location.reload();
      });

      return this.registration;
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error);
      throw error;
    }
  }

  /**
   * Setup install prompt
   */
  setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;

      // Check if user has dismissed before
      if (!localStorage.getItem('pwa-install-dismissed')) {
        setTimeout(() => {
          this.showInstallPrompt();
        }, 3000);
      }
    });

    // Track installation
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App installed successfully');
      this.deferredPrompt = null;
      this.triggerEvent('app-installed');
    });
  }

  /**
   * Show install prompt
   */
  showInstallPrompt() {
    const event = new CustomEvent('show-install-prompt', {
      detail: { deferredPrompt: this.deferredPrompt }
    });
    window.dispatchEvent(event);
  }

  /**
   * Trigger install
   */
  async install() {
    if (!this.deferredPrompt) {
      console.warn('[PWA] Install prompt not available');
      return false;
    }

    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;

    console.log(`[PWA] User response: ${outcome}`);
    this.deferredPrompt = null;

    return outcome === 'accepted';
  }

  /**
   * Dismiss install prompt
   */
  dismissInstall() {
    localStorage.setItem('pwa-install-dismissed', 'true');
    this.deferredPrompt = null;
  }

  /**
   * Setup online/offline detection
   */
  setupOnlineOfflineDetection() {
    window.addEventListener('online', () => {
      console.log('[PWA] Back online');
      this.triggerEvent('online');
      this.syncWhenOnline();
    });

    window.addEventListener('offline', () => {
      console.log('[PWA] Gone offline');
      this.triggerEvent('offline');
    });

    // Check initial state
    if (!navigator.onLine) {
      this.triggerEvent('offline');
    }
  }

  /**
   * Setup update checker
   */
  setupUpdateChecker() {
    if (!this.registration) return;

    setInterval(() => {
      this.registration.update().catch(err => {
        console.error('[PWA] Update check failed:', err);
      });
    }, this.config.updateCheckInterval);
  }

  /**
   * Notify about available update
   */
  notifyUpdate() {
    const event = new CustomEvent('pwa-update-available');
    window.dispatchEvent(event);
  }

  /**
   * Apply update
   */
  applyUpdate() {
    if (!this.registration || !this.registration.waiting) return;

    this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
  }

  /**
   * Setup Push Notifications
   */
  async setupPushNotifications() {
    if (!('Notification' in window) || !('PushManager' in window)) {
      console.warn('[PWA] Push notifications not supported');
      return;
    }

    if (Notification.permission === 'granted') {
      await this.subscribeToPush();
    }
  }

  /**
   * Request notification permission
   */
  async requestNotificationPermission() {
    const permission = await Notification.requestPermission();

    if (permission === 'granted') {
      console.log('[PWA] Notification permission granted');
      await this.subscribeToPush();
      return true;
    } else {
      console.log('[PWA] Notification permission denied');
      return false;
    }
  }

  /**
   * Subscribe to push notifications
   */
  async subscribeToPush() {
    if (!this.registration) return;

    try {
      // Get VAPID public key from server
      const response = await fetch('/api/pwa/vapid-public-key/');
      const { publicKey } = await response.json();

      const subscription = await this.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(publicKey)
      });

      // Send subscription to server
      await fetch('/api/pwa/subscribe/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription)
      });

      console.log('[PWA] Push subscription successful');
      return subscription;
    } catch (error) {
      console.error('[PWA] Push subscription failed:', error);
      throw error;
    }
  }

  /**
   * Unsubscribe from push notifications
   */
  async unsubscribeFromPush() {
    if (!this.registration) return;

    try {
      const subscription = await this.registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();

        // Notify server
        await fetch('/api/pwa/unsubscribe/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ endpoint: subscription.endpoint })
        });
      }

      console.log('[PWA] Push unsubscription successful');
    } catch (error) {
      console.error('[PWA] Push unsubscription failed:', error);
      throw error;
    }
  }

  /**
   * Setup periodic background sync
   */
  async setupPeriodicSync() {
    if (!this.registration || !('periodicSync' in this.registration)) {
      console.warn('[PWA] Periodic Sync not supported');
      return;
    }

    try {
      const status = await navigator.permissions.query({
        name: 'periodic-background-sync',
      });

      if (status.state === 'granted') {
        // Register periodic sync tags
        await this.registration.periodicSync.register('update-data', {
          minInterval: 24 * 60 * 60 * 1000, // 24 hours
        });

        console.log('[PWA] Periodic sync registered');
      }
    } catch (error) {
      console.error('[PWA] Periodic sync registration failed:', error);
    }
  }

  /**
   * Sync data when online
   */
  async syncWhenOnline() {
    if (!this.registration || !('sync' in this.registration)) {
      console.warn('[PWA] Background Sync not supported');
      return;
    }

    try {
      await this.registration.sync.register('sync-data');
      console.log('[PWA] Background sync registered');
    } catch (error) {
      console.error('[PWA] Background sync registration failed:', error);
    }
  }

  /**
   * Store data for offline sync
   */
  async storeForSync(storeName, data) {
    const db = await this.openIndexedDB();
    const transaction = db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);

    return new Promise((resolve, reject) => {
      const request = store.add(data);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Open IndexedDB
   */
  openIndexedDB(dbName = 'SomaKoDB', version = 1) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(dbName, version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        if (!db.objectStoreNames.contains('syncQueue')) {
          db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
        }

        if (!db.objectStoreNames.contains('offlineData')) {
          db.createObjectStore('offlineData', { keyPath: 'id' });
        }
      };
    });
  }

  /**
   * Clear cache
   */
  async clearCache(cacheName = null) {
    if (cacheName) {
      await caches.delete(cacheName);
    } else {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
    }

    console.log('[PWA] Cache cleared');
  }

  /**
   * Get cache size
   */
  async getCacheSize() {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return {
        usage: estimate.usage,
        quota: estimate.quota,
        percentage: (estimate.usage / estimate.quota * 100).toFixed(2)
      };
    }
    return null;
  }

  /**
   * Share content using Web Share API
   */
  async share(data) {
    if (!navigator.share) {
      console.warn('[PWA] Web Share API not supported');
      return false;
    }

    try {
      await navigator.share(data);
      console.log('[PWA] Share successful');
      return true;
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('[PWA] Share failed:', error);
      }
      return false;
    }
  }

  /**
   * Check if app is installed
   */
  isInstalled() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone === true;
  }

  /**
   * Get app badge count
   */
  async setBadge(count) {
    if ('setAppBadge' in navigator) {
      try {
        if (count > 0) {
          await navigator.setAppBadge(count);
        } else {
          await navigator.clearAppBadge();
        }
      } catch (error) {
        console.error('[PWA] Set badge failed:', error);
      }
    }
  }

  /**
   * Clear app badge
   */
  async clearBadge() {
    await this.setBadge(0);
  }

  /**
   * Trigger custom event
   */
  triggerEvent(eventName, detail = {}) {
    const event = new CustomEvent(eventName, { detail });
    window.dispatchEvent(event);
  }

  /**
   * Convert VAPID key
   */
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PWAManager;
}

// Make available globally
window.PWAManager = PWAManager;
