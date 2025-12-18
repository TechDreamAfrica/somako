"""
PWA Authentication Middleware
Automatically redirects unauthenticated PWA requests to PWA login
"""
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode


class PWAAuthMiddleware:
    """
    Middleware to handle authentication redirects for PWA apps.

    For any PWA URL that requires authentication, this middleware will
    redirect unauthenticated users to the PWA login page instead of
    the main login page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)

        # Check if this is a redirect to the main login page from a PWA path
        if (response.status_code == 302 and
            hasattr(response, 'url') and
            '/accounts/login/' in response.url and
            '/pwa/' in request.path and
            '/accounts/login/pwa/' not in response.url):

            # Detect which PWA app
            app = self._detect_pwa_app(request.path)

            if app:
                # Build PWA login URL
                login_url = reverse('accounts:pwa_login')
                params = urlencode({
                    'app': app,
                    'next': request.get_full_path()
                })
                return redirect(f'{login_url}?{params}')

        return response

    def _detect_pwa_app(self, path):
        """Detect PWA app from path"""
        if '/pwa/food/' in path:
            return 'food'
        elif '/pwa/shop/' in path:
            return 'shop'
        elif '/pwa/pharmacy/' in path:
            return 'pharmacy'
        elif '/pwa/rent/' in path:
            return 'rent'
        elif '/pwa/ride/' in path:
            return 'ride'
        return None
