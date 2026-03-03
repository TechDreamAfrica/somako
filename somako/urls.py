
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from core.sitemaps import sitemaps

urlpatterns = [
    # SEO: Sitemap and robots.txt
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),

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
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
