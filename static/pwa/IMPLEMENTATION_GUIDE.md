# PWA Implementation Guide for Soma Ko

## Quick Start (5 Minutes)

### Step 1: Add Scripts to Your Base Template

Add these lines to your HTML template (e.g., `pwa_base.html` or `base.html`):

```html
<!-- In the <head> section -->
<link rel="manifest" href="/static/pwa/{{ app_name }}/manifest.json">
<meta name="theme-color" content="{{ theme_color }}">

<!-- Before closing </body> tag -->
<script src="{% static 'pwa/pwa-utils.js' %}"></script>
<script src="{% static 'pwa/pwa-ui.js' %}"></script>
<script src="{% static 'pwa/pwa-init.js' %}"></script>
```

**That's it!** The PWA will auto-initialize based on the current URL path.

### Step 2: Update Other Apps' Service Workers

I've already enhanced the Food app's service worker. To apply the same enhancements to other apps:

#### Option A: Use the Enhanced Template

1. Copy `/static/pwa/sw-template.js`
2. Replace these values:
   ```javascript
   const APP_NAME = 'rent';  // Change to: rent, shop, pharmacy, or ride
   const APP_TITLE = 'Rent'; // Change to: Rent, Shop, Pharmacy, or Ride
   const THEME_COLOR = '#3b82f6'; // Use app's theme color
   ```
3. Save as `/static/pwa/{app_name}/sw.js`

#### Option B: Copy Food's Enhanced SW

Simply copy the enhanced food service worker and modify the app-specific values.

### Step 3: Test Your PWA

1. **Open Chrome DevTools**
   - Go to Application tab
   - Check Service Workers (should be registered)
   - Check Manifest (should show app details)

2. **Test Offline Mode**
   - Go to Network tab
   - Set to "Offline"
   - Navigate your app (should still work!)

3. **Test Install**
   - Look for install prompt (appears after 3 seconds)
   - Click "Install"
   - Check your desktop/home screen

## Features Implemented

### ✅ Core PWA Features

1. **Service Worker with Advanced Caching**
   - Network First for API calls
   - Cache First for images/static files
   - Offline fallback pages
   - Auto cache cleanup

2. **Background Sync**
   - Queue failed requests when offline
   - Auto-sync when back online
   - Form submission queuing

3. **Push Notifications**
   - Web Push API ready
   - Rich notifications with actions
   - Click handling and routing

4. **App Manifest**
   - App shortcuts (quick actions)
   - Share Target API
   - File handlers
   - Multiple display modes

5. **Offline Support**
   - Offline indicator UI
   - Offline page fallback
   - IndexedDB storage

6. **Install Experience**
   - Custom install prompt
   - Install analytics
   - Update notifications

7. **UI Components**
   - Install banner
   - Update prompt
   - Offline indicator
   - Toast notifications
   - Loading spinners

8. **Additional APIs**
   - Web Share
   - Badging (unread counts)
   - Cache management
   - Performance monitoring

## Configuration Options

### Per-App Customization

The auto-initialization script detects your app automatically. Current configurations:

```javascript
{
  food: {
    swPath: '/static/pwa/food/sw.js',
    scope: '/food/',
    themeColor: '#ef4444',
    accentColor: '#f87171'
  },
  rent: {
    swPath: '/static/pwa/rent/sw.js',
    scope: '/rent/',
    themeColor: '#3b82f6',
    accentColor: '#60a5fa'
  },
  shop: {
    swPath: '/static/pwa/shop/sw.js',
    scope: '/shop/',
    themeColor: '#8b5cf6',
    accentColor: '#a78bfa'
  },
  pharmacy: {
    swPath: '/static/pwa/pharmacy/sw.js',
    scope: '/pharmacy/',
    themeColor: '#10b981',
    accentColor: '#34d399'
  },
  ride: {
    swPath: '/static/pwa/ride/sw.js',
    scope: '/ride/',
    themeColor: '#f59e0b',
    accentColor: '#fbbf24'
  }
}
```

### Manual Override

If you need custom configuration:

```html
<script>
  // Before loading pwa-init.js
  window.PWA_CONFIG = {
    swPath: '/custom/sw.js',
    scope: '/custom/',
    themeColor: '#custom',
    updateCheckInterval: 120000, // 2 minutes
    enableNotifications: false
  };
</script>
```

## Common Use Cases

### 1. Show Install Prompt on Button Click

```html
<button onclick="window.pwaManager.install()">
  Install App
</button>
```

### 2. Request Notification Permission

```html
<button data-request-notifications>
  Enable Notifications
</button>
```

### 3. Share Content

```html
<button data-share
        data-share-title="Check this!"
        data-share-text="Amazing restaurant"
        data-share-url="/food/restaurant/123/">
  Share
</button>
```

### 4. Show Toast Notification

```javascript
window.pwaUI.showToast('Success!', 'success');
window.pwaUI.showToast('Error occurred', 'error');
```

### 5. Check if PWA is Installed

```javascript
if (window.pwaManager.isInstalled()) {
  // Running as installed PWA
  document.body.classList.add('pwa-installed');
}
```

### 6. Handle Offline Form Submission

Forms are automatically queued when offline. No extra code needed!

### 7. Update App Badge

```javascript
// Show unread count
window.pwaManager.setBadge(5);

// Clear badge
window.pwaManager.clearBadge();
```

### 8. Clear Cache

```html
<button data-clear-cache>Clear Cache</button>
```

## Django Integration (Backend Support)

### 1. Add PWA URLs (Optional)

Create API endpoints for:

```python
# urls.py
urlpatterns = [
    path('api/pwa/vapid-public-key/', views.get_vapid_key),
    path('api/pwa/subscribe/', views.subscribe_push),
    path('api/pwa/unsubscribe/', views.unsubscribe_push),
]
```

### 2. Generate VAPID Keys (For Push Notifications)

```bash
pip install py-vapid
vapid --gen
```

Save the keys in your settings:

```python
# settings.py
VAPID_PUBLIC_KEY = 'your-public-key'
VAPID_PRIVATE_KEY = 'your-private-key'
VAPID_ADMIN_EMAIL = 'admin@somako.org'
```

### 3. Send Push Notifications

```python
from pywebpush import webpush

# Get user's push subscription from database
subscription_info = user.push_subscription

webpush(
    subscription_info=subscription_info,
    data=json.dumps({
        'title': 'New Order',
        'body': 'You have a new order!',
        'icon': '/static/pwa/food/icon-192x192.png',
        'url': '/food/orders/123/'
    }),
    vapid_private_key=settings.VAPID_PRIVATE_KEY,
    vapid_claims={
        'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'
    }
)
```

### 4. Handle Share Target (Optional)

```python
# views.py
@csrf_exempt
def handle_share(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        text = request.POST.get('text')
        url = request.POST.get('url')
        image = request.FILES.get('image')

        # Process shared content
        # ...

        return redirect('/food/dashboard/')
```

### 5. Serve Manifest Dynamically (Optional)

```python
from django.http import JsonResponse

def manifest(request, app_name):
    manifest_data = {
        'name': f'Soma Ko {app_name.title()}',
        'short_name': f'Soma {app_name.title()}',
        # ... rest of manifest
    }
    return JsonResponse(manifest_data)
```

## Deployment Checklist

### Before Going Live:

- [ ] All service workers are registered correctly
- [ ] Manifest files are accessible
- [ ] Icons are in place (all sizes)
- [ ] HTTPS is enabled (required for PWA)
- [ ] Test install on mobile devices
- [ ] Test offline functionality
- [ ] Set up push notification backend
- [ ] Configure VAPID keys
- [ ] Test update mechanism
- [ ] Run Lighthouse PWA audit (score > 90)

### Post-Deployment:

- [ ] Monitor service worker errors
- [ ] Track install metrics
- [ ] Monitor cache usage
- [ ] Test on different browsers
- [ ] Gather user feedback

## Troubleshooting

### Service Worker Not Registering

1. Check console for errors
2. Verify HTTPS is enabled
3. Check service worker path is correct
4. Clear browser cache and try again

### Install Prompt Not Showing

1. Ensure manifest is linked in HTML
2. Check manifest has required fields
3. Verify service worker is active
4. Clear "dismissed" flag: `localStorage.removeItem('pwa-install-dismissed')`

### Offline Mode Not Working

1. Check service worker fetch handler
2. Verify resources are cached
3. Check cache names match
4. Test with DevTools offline mode

### Push Notifications Not Working

1. Verify VAPID keys are correct
2. Check notification permission is granted
3. Ensure HTTPS is enabled
4. Check browser support

### Update Not Applying

1. Increment CACHE_VERSION in service worker
2. Use "Update on reload" in DevTools
3. Clear cache manually
4. Check skip waiting logic

## Performance Optimization

### Cache Strategy Tips:

1. **Precache Only Essentials**
   ```javascript
   const STATIC_CACHE = [
     '/app/dashboard/',
     '/static/css/app.css',
     '/static/js/app.js',
     // Only critical resources
   ];
   ```

2. **Use Appropriate Cache Strategies**
   - API: Network First
   - Images: Cache First
   - HTML: Network First with Fallback
   - Static Assets: Cache First

3. **Set Cache Limits**
   ```javascript
   // Limit cache entries
   const MAX_CACHE_SIZE = 50;
   ```

4. **Clean Up Regularly**
   ```javascript
   // Delete old caches on activate
   caches.keys().then(names => {
     return Promise.all(
       names.filter(name => name.startsWith('old-'))
         .map(name => caches.delete(name))
     );
   });
   ```

## Next Steps

1. **Customize for Each App**
   - Update service workers for rent, shop, pharmacy, ride
   - Customize manifest shortcuts per app
   - Add app-specific offline pages

2. **Add Backend Support**
   - Set up VAPID keys
   - Create push notification endpoints
   - Implement share target handler

3. **Monitor & Optimize**
   - Track PWA metrics
   - Monitor cache sizes
   - Optimize caching strategies

4. **Advanced Features**
   - Periodic background sync
   - Badge API for notifications
   - File handling
   - Protocol handlers

## Resources

- [PWA Documentation](static/pwa/README.md) - Full feature documentation
- [Service Worker Template](static/pwa/sw-template.js) - Template for new apps
- [MDN PWA Guide](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [web.dev PWA](https://web.dev/progressive-web-apps/)

## Support

For issues or questions:
- Check browser DevTools console
- Review service worker status
- Run Lighthouse audit
- Check documentation

---

**Your PWA is now ready! 🎉**

Users can now install your app, use it offline, receive push notifications, and enjoy a native app-like experience.
