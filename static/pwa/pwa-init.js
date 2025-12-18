/**
 * PWA Initialization Script
 * Auto-initialize PWA features for Soma Ko apps
 */

(function() {
  'use strict';

  // Configuration based on current app
  const appConfig = detectAppConfig();

  // Initialize PWA Manager
  const pwaManager = new PWAManager({
    swPath: appConfig.swPath,
    scope: appConfig.scope,
    updateCheckInterval: 60000,
    enableNotifications: true,
    enableBackgroundSync: true,
    enablePeriodicSync: true
  });

  // Initialize UI Components
  const pwaUI = new PWAUIComponents({
    themeColor: appConfig.themeColor,
    accentColor: appConfig.accentColor
  });

  /**
   * Detect current app configuration
   */
  function detectAppConfig() {
    const path = window.location.pathname;
    const configs = {
      food: {
        name: 'food',
        swPath: '/static/pwa/food/sw.js',
        scope: '/food/',
        themeColor: '#ef4444',
        accentColor: '#f87171'
      },
      rent: {
        name: 'rent',
        swPath: '/static/pwa/rent/sw.js',
        scope: '/rent/',
        themeColor: '#3b82f6',
        accentColor: '#60a5fa'
      },
      shop: {
        name: 'shop',
        swPath: '/static/pwa/shop/sw.js',
        scope: '/shop/',
        themeColor: '#8b5cf6',
        accentColor: '#a78bfa'
      },
      pharmacy: {
        name: 'pharmacy',
        swPath: '/static/pwa/pharmacy/sw.js',
        scope: '/pharmacy/',
        themeColor: '#10b981',
        accentColor: '#34d399'
      },
      ride: {
        name: 'ride',
        swPath: '/static/pwa/ride/sw.js',
        scope: '/ride/',
        themeColor: '#f59e0b',
        accentColor: '#fbbf24'
      }
    };

    for (const [key, config] of Object.entries(configs)) {
      if (path.includes(`/${key}/`)) {
        return config;
      }
    }

    // Default configuration
    return {
      name: 'default',
      swPath: '/sw.js',
      scope: '/',
      themeColor: '#059669',
      accentColor: '#10b981'
    };
  }

  /**
   * Initialize PWA features
   */
  async function initPWA() {
    try {
      // Initialize manager and UI
      await pwaManager.init();
      pwaUI.init();

      setupEventHandlers();
      setupOfflineFormHandling();
      setupBeforeUnload();

      console.log('[PWA] Initialized successfully');
    } catch (error) {
      console.error('[PWA] Initialization failed:', error);
    }
  }

  /**
   * Setup event handlers
   */
  function setupEventHandlers() {
    // Install prompt
    window.addEventListener('pwa-install-clicked', async () => {
      const installed = await pwaManager.install();
      if (installed) {
        pwaUI.showToast('App installed successfully!', 'success');
        pwaUI.hideInstallPrompt();
      }
    });

    window.addEventListener('pwa-install-dismissed', () => {
      pwaManager.dismissInstall();
    });

    // Update prompt
    window.addEventListener('pwa-update-clicked', () => {
      pwaManager.applyUpdate();
      pwaUI.showToast('Updating app...', 'info');
    });

    // Online/Offline
    window.addEventListener('online', () => {
      pwaUI.showToast('Back online!', 'success', 2000);
    });

    window.addEventListener('offline', () => {
      pwaUI.showToast('You are offline', 'warning', 2000);
    });

    // App installed
    window.addEventListener('app-installed', () => {
      pwaUI.showToast('App installed successfully!', 'success');
    });
  }

  /**
   * Setup offline form handling
   */
  function setupOfflineFormHandling() {
    document.addEventListener('submit', async (e) => {
      if (!navigator.onLine) {
        e.preventDefault();

        const form = e.target;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
          // Store form data for later sync
          await pwaManager.storeForSync('syncQueue', {
            type: 'form-submission',
            url: form.action,
            method: form.method || 'POST',
            data: data,
            timestamp: Date.now(),
            tag: 'sync-forms'
          });

          pwaUI.showToast('Saved! Will sync when online', 'info');

          // Register background sync
          if ('sync' in navigator.serviceWorker.registration) {
            await navigator.serviceWorker.registration.sync.register('sync-forms');
          }
        } catch (error) {
          console.error('[PWA] Failed to queue form:', error);
          pwaUI.showToast('Failed to save form data', 'error');
        }
      }
    });
  }

  /**
   * Setup before unload handler
   */
  function setupBeforeUnload() {
    window.addEventListener('beforeunload', (e) => {
      // Check for unsaved changes
      const unsavedForms = document.querySelectorAll('form[data-changed="true"]');
      if (unsavedForms.length > 0) {
        e.preventDefault();
        e.returnValue = '';
      }
    });

    // Track form changes
    document.addEventListener('input', (e) => {
      if (e.target.form) {
        e.target.form.dataset.changed = 'true';
      }
    });

    document.addEventListener('submit', (e) => {
      if (e.target.tagName === 'FORM') {
        delete e.target.dataset.changed;
      }
    });
  }

  /**
   * Setup notification permission request
   */
  function setupNotificationRequest() {
    // Request after user interaction
    const requestNotificationBtn = document.querySelector('[data-request-notifications]');
    if (requestNotificationBtn) {
      requestNotificationBtn.addEventListener('click', async () => {
        const granted = await pwaManager.requestNotificationPermission();
        if (granted) {
          pwaUI.showToast('Notifications enabled!', 'success');
        } else {
          pwaUI.showToast('Notifications denied', 'error');
        }
      });
    }

    // Auto-request after 30 seconds if not decided
    if (Notification.permission === 'default') {
      setTimeout(() => {
        if (Notification.permission === 'default') {
          pwaManager.requestNotificationPermission();
        }
      }, 30000);
    }
  }

  /**
   * Setup share functionality
   */
  function setupShareButtons() {
    document.addEventListener('click', async (e) => {
      const shareBtn = e.target.closest('[data-share]');
      if (!shareBtn) return;

      const shareData = {
        title: shareBtn.dataset.shareTitle || document.title,
        text: shareBtn.dataset.shareText || '',
        url: shareBtn.dataset.shareUrl || window.location.href
      };

      const shared = await pwaManager.share(shareData);
      if (shared) {
        pwaUI.showToast('Shared successfully!', 'success');
      }
    });
  }

  /**
   * Setup badge API
   */
  function setupBadgeUpdates() {
    // Update badge when notifications arrive
    window.addEventListener('notification-received', (e) => {
      const count = e.detail.unreadCount || 1;
      pwaManager.setBadge(count);
    });

    // Clear badge when user views notifications
    window.addEventListener('notifications-viewed', () => {
      pwaManager.clearBadge();
    });
  }

  /**
   * Setup performance monitoring
   */
  function setupPerformanceMonitoring() {
    // Log performance metrics
    if ('performance' in window && 'PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'navigation') {
              console.log('[PWA] Page load time:', entry.loadEventEnd - entry.fetchStart, 'ms');
            }
          }
        });

        observer.observe({ entryTypes: ['navigation'] });
      } catch (error) {
        console.error('[PWA] Performance monitoring failed:', error);
      }
    }
  }

  /**
   * Setup cache management UI
   */
  function setupCacheManagement() {
    const clearCacheBtn = document.querySelector('[data-clear-cache]');
    if (clearCacheBtn) {
      clearCacheBtn.addEventListener('click', async () => {
        const spinner = pwaUI.showLoading();

        try {
          await pwaManager.clearCache();
          pwaUI.showToast('Cache cleared successfully', 'success');
        } catch (error) {
          pwaUI.showToast('Failed to clear cache', 'error');
        } finally {
          pwaUI.hideLoading(spinner);
        }
      });
    }

    // Show cache size
    const cacheSizeEl = document.querySelector('[data-cache-size]');
    if (cacheSizeEl) {
      pwaManager.getCacheSize().then(size => {
        if (size) {
          cacheSizeEl.textContent = `${(size.usage / 1024 / 1024).toFixed(2)} MB / ${(size.quota / 1024 / 1024).toFixed(0)} MB (${size.percentage}%)`;
        }
      });
    }
  }

  /**
   * Setup app shortcuts
   */
  function setupAppShortcuts() {
    // Handle shortcut navigation
    const urlParams = new URLSearchParams(window.location.search);
    const action = urlParams.get('action');

    if (action) {
      console.log('[PWA] Launched from shortcut:', action);
      // Handle specific actions
      window.dispatchEvent(new CustomEvent('pwa-shortcut-action', {
        detail: { action }
      }));
    }
  }

  /**
   * Check if running as PWA
   */
  function checkPWAMode() {
    if (pwaManager.isInstalled()) {
      document.documentElement.classList.add('pwa-mode');
      console.log('[PWA] Running in standalone mode');
    } else {
      document.documentElement.classList.add('browser-mode');
    }
  }

  /**
   * Initialize everything on DOM ready
   */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initPWA();
      setupNotificationRequest();
      setupShareButtons();
      setupBadgeUpdates();
      setupPerformanceMonitoring();
      setupCacheManagement();
      setupAppShortcuts();
      checkPWAMode();
    });
  } else {
    initPWA();
    setupNotificationRequest();
    setupShareButtons();
    setupBadgeUpdates();
    setupPerformanceMonitoring();
    setupCacheManagement();
    setupAppShortcuts();
    checkPWAMode();
  }

  // Make managers available globally for debugging
  window.pwaManager = pwaManager;
  window.pwaUI = pwaUI;

  console.log('[PWA] Initialization script loaded');
})();
