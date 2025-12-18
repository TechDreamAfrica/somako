# Soma Ko PWA Features Documentation

## Overview

This directory contains a comprehensive Progressive Web App (PWA) implementation for all Soma Ko applications (Food, Rent, Shop, Pharmacy, and Ride). The PWA features enable offline functionality, push notifications, background sync, and native app-like experiences.

## Features Implemented

### 1. **Service Worker (Enhanced)**
- ✅ Advanced caching strategies:
  - Network First (for API requests)
  - Cache First (for images and static assets)
  - Stale While Revalidate (for dynamic content)
  - Network First with Offline Fallback (for HTML pages)
- ✅ Automatic cache versioning and cleanup
- ✅ Offline page fallback
- ✅ IndexedDB integration for offline data persistence

### 2. **Background Sync**
- ✅ Queue failed requests when offline
- ✅ Auto-sync when connection is restored
- ✅ Form submission queuing
- ✅ Order/cart synchronization

### 3. **Push Notifications**
- ✅ Web Push API integration
- ✅ VAPID key support
- ✅ Rich notifications with actions
- ✅ Smart notification routing
- ✅ Notification click handling

### 4. **Periodic Background Sync**
- ✅ Automatic data updates in background
- ✅ Order status checking
- ✅ Menu/inventory updates
- ✅ Configurable sync intervals

### 5. **App Manifest (Enhanced)**
- ✅ App shortcuts for quick actions
- ✅ Share Target API integration
- ✅ File handler support
- ✅ Protocol handlers
- ✅ Multiple display modes
- ✅ Screenshot support
- ✅ Launch handler configuration

### 6. **Offline Capabilities**
- ✅ Offline page with custom UI
- ✅ Offline indicator
- ✅ Form data persistence
- ✅ Local data caching with IndexedDB

### 7. **Install Experience**
- ✅ Custom install prompt UI
- ✅ Install prompt timing control
- ✅ A2HS (Add to Home Screen) support
- ✅ Install analytics tracking

### 8. **Update Management**
- ✅ Automatic update detection
- ✅ Update notification UI
- ✅ Skip waiting functionality
- ✅ Periodic update checks

### 9. **UI Components**
- ✅ Install prompt banner
- ✅ Update notification
- ✅ Offline indicator
- ✅ Toast notifications
- ✅ Loading spinners
- ✅ Badge notifications

### 10. **Additional Features**
- ✅ Web Share API integration
- ✅ Badging API for unread counts
- ✅ Cache size monitoring
- ✅ Performance monitoring
- ✅ PWA detection (standalone mode)
- ✅ App shortcuts handling
- ✅ Safe area support for notched devices

## File Structure

```
static/pwa/
├── README.md                    # This file
├── pwa-utils.js                # PWA Manager class (core functionality)
├── pwa-ui.js                   # UI Components (install prompt, toasts, etc.)
├── pwa-init.js                 # Auto-initialization script
├── sw-template.js              # Service worker template for new apps
├── food/
│   ├── manifest.json           # Enhanced manifest with all features
│   ├── sw.js                   # Enhanced service worker
│   └── icons/                  # App icons
├── rent/
│   ├── manifest.json
│   ├── sw.js
│   └── icons/
├── shop/
│   ├── manifest.json
│   ├── sw.js
│   └── icons/
├── pharmacy/
│   ├── manifest.json
│   ├── sw.js
│   └── icons/
└── ride/
    ├── manifest.json
    ├── sw.js
    └── icons/
```

## Usage

### Basic Setup

1. **Include PWA scripts in your template:**

```html
<!-- Load PWA utilities -->
<script src="{% static 'pwa/pwa-utils.js' %}"></script>
<script src="{% static 'pwa/pwa-ui.js' %}"></script>
<script src="{% static 'pwa/pwa-init.js' %}"></script>
```

2. **Link manifest in head:**

```html
<link rel="manifest" href="/static/pwa/food/manifest.json">
```

3. **Register service worker (auto-handled by pwa-init.js)**

The initialization script automatically detects the current app and registers the appropriate service worker.

### Manual Initialization

If you need manual control:

```javascript
// Initialize PWA Manager
const pwaManager = new PWAManager({
  swPath: '/static/pwa/food/sw.js',
  scope: '/food/',
  enableNotifications: true,
  enableBackgroundSync: true
});

// Initialize UI Components
const pwaUI = new PWAUIComponents({
  themeColor: '#ef4444',
  accentColor: '#f87171'
});

// Initialize both
await pwaManager.init();
pwaUI.init();
```

### Using PWA Features

#### 1. Install Prompt

```javascript
// Show install prompt
window.addEventListener('show-install-prompt', () => {
  // Prompt is shown automatically by UI component
});

// Handle install
pwaManager.install().then(installed => {
  if (installed) {
    console.log('App installed!');
  }
});
```

#### 2. Push Notifications

```javascript
// Request permission
const granted = await pwaManager.requestNotificationPermission();

// Subscribe to push
await pwaManager.subscribeToPush();

// Unsubscribe
await pwaManager.unsubscribeFromPush();
```

#### 3. Background Sync

```javascript
// Store data for sync when offline
await pwaManager.storeForSync('syncQueue', {
  type: 'order',
  data: orderData,
  timestamp: Date.now()
});

// Register sync tag
if ('sync' in navigator.serviceWorker.registration) {
  await navigator.serviceWorker.registration.sync.register('sync-orders');
}
```

#### 4. Offline Form Handling

Forms are automatically queued when offline. The user sees a toast notification, and the data is synced when the connection is restored.

#### 5. Share API

```html
<button data-share
        data-share-title="Check this out!"
        data-share-text="Amazing restaurant"
        data-share-url="/food/restaurant/123/">
  Share
</button>
```

#### 6. Notifications & Toasts

```javascript
// Show toast
pwaUI.showToast('Order placed successfully!', 'success');
pwaUI.showToast('Error occurred', 'error');
pwaUI.showToast('Warning message', 'warning');
pwaUI.showToast('Info message', 'info');

// Show loading
const spinner = pwaUI.showLoading();
// ... do work
pwaUI.hideLoading(spinner);
```

#### 7. Badge API

```javascript
// Set app badge
await pwaManager.setBadge(5); // Shows "5" on app icon

// Clear badge
await pwaManager.clearBadge();
```

#### 8. Cache Management

```javascript
// Get cache size
const size = await pwaManager.getCacheSize();
console.log(`Using ${size.percentage}% of quota`);

// Clear cache
await pwaManager.clearCache();

// Clear specific cache
await pwaManager.clearCache('somako-food-v2');
```

#### 9. Check if PWA is installed

```javascript
if (pwaManager.isInstalled()) {
  console.log('Running as installed PWA');
} else {
  console.log('Running in browser');
}
```

### Service Worker Events

Listen to custom events:

```javascript
// Update available
window.addEventListener('pwa-update-available', () => {
  // Show update UI
});

// Online/Offline
window.addEventListener('online', () => {
  console.log('Back online');
});

window.addEventListener('offline', () => {
  console.log('Gone offline');
});

// App installed
window.addEventListener('app-installed', () => {
  console.log('App installed successfully');
});
```

## Creating Service Worker for New App

Use the template to create a new service worker:

1. Copy `sw-template.js`
2. Replace placeholders:
   - `{{APP_NAME}}` → 'myapp'
   - `{{APP_TITLE}}` → 'My App'
   - `{{THEME_COLOR}}` → '#123456'
3. Customize `STATIC_RESOURCES` array
4. Save as `static/pwa/myapp/sw.js`

## Manifest Configuration

Key manifest features:

```json
{
  "name": "App Name",
  "short_name": "App",
  "start_url": "/app/dashboard/?source=pwa",
  "display": "standalone",
  "shortcuts": [...],          // Quick actions
  "share_target": {...},        // Share API
  "file_handlers": [...],       // File handling
  "protocol_handlers": [...],   // URL protocols
  "screenshots": [...]          // App store screenshots
}
```

## Testing PWA Features

### Chrome DevTools

1. Open DevTools → Application tab
2. Check:
   - Manifest
   - Service Workers
   - Cache Storage
   - IndexedDB
   - Push notifications

### Lighthouse

Run Lighthouse audit for PWA score:

```bash
lighthouse https://yoursite.com --view
```

### Manual Testing

1. **Offline Mode:**
   - Open DevTools → Network tab
   - Set to "Offline"
   - Navigate site (should work)

2. **Install:**
   - Look for install prompt
   - Install app
   - Check home screen

3. **Push Notifications:**
   - Grant permission
   - Trigger test notification from backend

4. **Background Sync:**
   - Go offline
   - Submit form
   - Go online
   - Check if synced

## Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Service Worker | ✅ | ✅ | ✅ | ✅ |
| Push Notifications | ✅ | ✅ | ❌ | ✅ |
| Background Sync | ✅ | ❌ | ❌ | ✅ |
| Periodic Sync | ✅ | ❌ | ❌ | ✅ |
| Badging API | ✅ | ❌ | ✅ | ✅ |
| Share Target | ✅ | ❌ | ✅ | ✅ |
| File Handlers | ✅ | ❌ | ❌ | ✅ |

## Best Practices

1. **Cache Strategy:**
   - Use Network First for API requests
   - Use Cache First for static assets
   - Provide offline fallbacks

2. **Update Strategy:**
   - Check for updates regularly
   - Notify users of available updates
   - Apply updates on user consent

3. **Notifications:**
   - Request permission at appropriate time
   - Don't spam users
   - Make notifications actionable

4. **Performance:**
   - Minimize cache size
   - Clean up old caches
   - Use IndexedDB for large data

5. **User Experience:**
   - Show offline indicators
   - Queue actions when offline
   - Provide feedback for all actions

## Debugging

### Console Logs

All PWA logs are prefixed with `[PWA]` or `[SW]`:

```javascript
console.log('[PWA] Initialized');
console.log('[SW] Caching resources');
```

### Service Worker Logs

View service worker logs in Chrome DevTools:
- Application → Service Workers → Console

### Common Issues

1. **Service Worker not updating:**
   - Clear cache manually
   - Use "Update on reload" in DevTools
   - Increment CACHE_VERSION

2. **Push notifications not working:**
   - Check VAPID keys
   - Verify notification permission
   - Check browser support

3. **Offline mode not working:**
   - Check service worker registration
   - Verify cache strategy
   - Check network requests in DevTools

## Security Considerations

1. **HTTPS Required:**
   - PWA features require HTTPS
   - Localhost is exempt for testing

2. **VAPID Keys:**
   - Keep private key secure
   - Rotate keys periodically

3. **Data Storage:**
   - Encrypt sensitive data in IndexedDB
   - Clear storage on logout

## Performance Tips

1. **Precache Critical Resources:**
   - Only cache essential files
   - Use versioning for cache busting

2. **Lazy Load Non-Critical:**
   - Load features on demand
   - Use dynamic imports

3. **Monitor Cache Size:**
   - Check quota usage
   - Clean up periodically

## Future Enhancements

- [ ] App badge notifications with counts
- [ ] Advanced offline data sync strategies
- [ ] Web Bluetooth integration
- [ ] Web NFC support
- [ ] Contact Picker API
- [ ] File System Access API
- [ ] Screen Wake Lock API
- [ ] Web Authentication (WebAuthn)

## Support

For issues or questions:
- Check browser console for errors
- Review service worker status in DevTools
- Test with Lighthouse PWA audit
- Check this documentation

## License

Part of Soma Ko Platform - All Rights Reserved
