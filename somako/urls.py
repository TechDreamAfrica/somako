
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('messages/', include('messaging.urls')),  # Cross-app messaging
    path('rent/', include('rent.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('shop/', include('shop.urls')),
    path('food/', include('food.urls')),
    path('ride/', include('ride.urls')),
    path('payment/', include('payment.urls')),

    # PWA-specific routes
    path('pwa/food/', include('food_pwa.urls')),
    path('pwa/shop/', include('shop_pwa.urls')),
    path('pwa/pharmacy/', include('pharmacy_pwa.urls')),
    path('pwa/rent/', include('rent_pwa.urls')),
    path('pwa/ride/', include('ride_pwa.urls')),
    path('pwa/express/', include('express_pwa.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files from STATICFILES_DIRS in development
    from django.contrib.staticfiles.views import serve as static_serve
    from django.urls import re_path
    import os
    
    # Add proper static file serving for development
    for static_dir in settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=static_dir)
