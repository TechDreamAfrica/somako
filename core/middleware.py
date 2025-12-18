from django.shortcuts import redirect
from django.urls import reverse


class PWAAccessMiddleware:
    """
    Middleware to enforce PWA-only access for users who accessed via PWA.
    Once a user accesses any PWA dashboard, they are restricted to PWA routes only.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Define PWA-allowed URL patterns
        self.pwa_allowed_paths = [
            '/pwa/',  # All PWA routes
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/profile/',
            '/accounts/password/',
            '/api/',  # API endpoints for PWA
            '/static/',
            '/media/',
        ]

        # Define app-specific allowed paths
        self.app_specific_paths = {
            'food': [
                '/food/restaurant/',
                '/food/menu/',
                '/food/order/',
            ],
            'shop': [
                '/shop/product/',
                '/shop/order/',
                '/shop/cart/',
            ],
            'pharmacy': [
                '/pharmacy/medicine/',
                '/pharmacy/order/',
                '/pharmacy/cart/',
            ],
            'ride': [
                '/ride/book/',
                '/ride/history/',
                '/ride/driver/',
            ],
            'rent': [
                '/rent/property/',
                '/rent/booking/',
                '/rent/equipment/',
            ],
        }

    def __call__(self, request):
        # Check if user is marked as PWA user
        is_pwa_user = request.session.get('is_pwa_user', False)
        pwa_app = request.session.get('pwa_app')

        if is_pwa_user and pwa_app:
            # Get the current path
            current_path = request.path

            # Check if path is allowed
            is_allowed = False

            # Check general PWA allowed paths
            for allowed_path in self.pwa_allowed_paths:
                if current_path.startswith(allowed_path):
                    is_allowed = True
                    break

            # Check app-specific paths
            if not is_allowed and pwa_app in self.app_specific_paths:
                for app_path in self.app_specific_paths[pwa_app]:
                    if current_path.startswith(app_path):
                        is_allowed = True
                        break

            # If trying to access web-only routes, redirect to PWA dashboard
            if not is_allowed:
                # Redirect to appropriate PWA dashboard
                pwa_urls = {
                    'food': reverse('food_pwa:dashboard'),
                    'shop': reverse('shop:product_list'),
                    'pharmacy': reverse('pharmacy:medicine_list'),
                    'ride': reverse('ride:book_ride'),
                    'rent': reverse('rent:property_list'),
                }

                if pwa_app in pwa_urls:
                    return redirect(pwa_urls[pwa_app])

        response = self.get_response(request)
        return response
