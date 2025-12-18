"""
PWA-specific authentication decorators
Handles login redirects for Progressive Web Apps
"""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode


def pwa_login_required(pwa_app=None):
    """
    Decorator for PWA views that require authentication.
    Redirects to PWA login page instead of main login page.

    Usage:
        @pwa_login_required(pwa_app='food')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # Determine PWA app from path if not specified
                app = pwa_app
                if not app:
                    path = request.path
                    if '/pwa/food/' in path:
                        app = 'food'
                    elif '/pwa/shop/' in path:
                        app = 'shop'
                    elif '/pwa/pharmacy/' in path:
                        app = 'pharmacy'
                    elif '/pwa/rent/' in path:
                        app = 'rent'
                    elif '/pwa/ride/' in path:
                        app = 'ride'
                    else:
                        app = 'food'  # default

                # Build PWA login URL with app parameter and next URL
                login_url = reverse('accounts:pwa_login')
                params = urlencode({
                    'app': app,
                    'next': request.get_full_path()
                })
                return redirect(f'{login_url}?{params}')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def detect_pwa_app(request):
    """
    Helper function to detect which PWA app from the request path
    Returns the app name (food, shop, pharmacy, rent, ride) or None
    """
    path = request.path

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


def get_pwa_login_url(app_name, next_url=None):
    """
    Helper function to generate PWA login URL for a specific app

    Args:
        app_name: Name of the PWA app (food, shop, pharmacy, rent, ride)
        next_url: URL to redirect to after login (optional)

    Returns:
        Complete PWA login URL with parameters
    """
    login_url = reverse('accounts:pwa_login')
    params = {'app': app_name}

    if next_url:
        params['next'] = next_url

    return f'{login_url}?{urlencode(params)}'


def get_pwa_home_url(app_name):
    """
    Helper function to get the home URL for a specific PWA app

    Args:
        app_name: Name of the PWA app (food, shop, pharmacy, rent, ride)

    Returns:
        Home URL for the specified PWA app
    """
    pwa_homes = {
        'food': '/pwa/food/',
        'shop': '/pwa/shop/',
        'pharmacy': '/pwa/pharmacy/',
        'rent': '/pwa/rent/',
        'ride': '/pwa/ride/',
    }

    return pwa_homes.get(app_name, '/pwa/food/')
