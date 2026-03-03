from django.shortcuts import render
from django.db.models import Avg
from django.http import HttpResponse
from accounts.models import User

# Import models from service apps
from rent.models import Equipment, RentalBooking
from pharmacy.models import Medicine, Order as PharmacyOrder
from shop.models import Product, Order as ShopOrder
from food.models import Restaurant, MenuItem, Order as FoodOrder
from ride.models import Ride, DriverProfile


def home(request):
    """Home page view with featured content and statistics from all service apps"""

    # RENT APP DATA
    featured_equipment = Equipment.objects.filter(
        is_available=True
    ).order_by('-created_at')[:6]

    featured_equipment = Equipment.objects.filter(
        is_available=True
    ).order_by('-created_at')[:4]

    total_equipment = Equipment.objects.filter(is_available=True).count()
    total_equipment = Equipment.objects.filter(is_available=True).count()
    total_rentals = RentalBooking.objects.filter(status__in=['confirmed', 'active']).count()

    # PHARMACY APP DATA
    featured_medicines = Medicine.objects.filter(
        is_active=True
    ).order_by('-created_at')[:6]

    total_medicines = Medicine.objects.filter(is_active=True).count()
    total_pharmacy_orders = PharmacyOrder.objects.filter(status='delivered').count()

    # SHOP APP DATA
    featured_products = Product.objects.filter(
        is_active=True
    ).order_by('-created_at')[:6]

    total_products = Product.objects.filter(is_active=True).count()
    total_shop_orders = ShopOrder.objects.count()

    # FOOD APP DATA
    featured_restaurants = Restaurant.objects.filter(
        status='active'
    ).annotate(
        avg_rating=Avg('reviews__rating')
    ).order_by('-avg_rating', '-created_at')[:6]

    featured_menu_items = MenuItem.objects.filter(
        is_available=True,
        is_featured=True
    ).order_by('-created_at')[:6]

    total_restaurants = Restaurant.objects.filter(status='active').count()
    total_food_orders = FoodOrder.objects.filter(status='delivered').count()

    # RIDE APP DATA
    total_drivers = DriverProfile.objects.filter(
        status='APPROVED',
        availability='ONLINE'
    ).count()

    total_rides = Ride.objects.filter(status='completed').count()
    active_rides = Ride.objects.filter(status__in=['accepted', 'arrived', 'in_progress']).count()

    # AGGREGATE STATISTICS
    total_users = User.objects.count()
    total_orders = total_pharmacy_orders + total_shop_orders + total_food_orders + total_rides

    # Count unique cities from properties, restaurants, etc.
    equipment_cities = Equipment.objects.values_list('city', flat=True).distinct()
    restaurant_cities = Restaurant.objects.values_list('city', flat=True).distinct()
    unique_cities = len(set(list(equipment_cities) + list(restaurant_cities)))

    context = {
        # Rent data
        'featured_equipment': featured_equipment,
        'total_equipment': total_equipment,
        'total_rentals': total_rentals,

        # Pharmacy data
        'featured_medicines': featured_medicines,
        'total_medicines': total_medicines,
        'total_pharmacy_orders': total_pharmacy_orders,

        # Shop data
        'featured_products': featured_products,
        'total_products': total_products,
        'total_shop_orders': total_shop_orders,

        # Food data
        'featured_restaurants': featured_restaurants,
        'featured_menu_items': featured_menu_items,
        'total_restaurants': total_restaurants,
        'total_food_orders': total_food_orders,

        # Ride data
        'total_drivers': total_drivers,
        'total_rides': total_rides,
        'active_rides': active_rides,

        # Aggregate statistics
        'total_users': total_users,
        'total_orders': total_orders,
        'unique_cities': unique_cities,
    }
    return render(request, 'core/home.html', context)


def downloads(request):
    """Downloads page for Soma Ko mobile app"""
    context = {
        'ios_url': 'http://www.somako.org/pwa/express',
        'android_url': 'http://www.somako.org/pwa/express',
        'apk_filename': 'soma-ko-app.apk'  # Adjust this to match your actual APK filename
    }
    return render(request, 'core/downloads.html', context)


def download_apk(request):
    """Serve APK file with proper headers for download"""
    from django.http import HttpResponse, Http404
    from django.conf import settings
    import os
    
    apk_filename = 'soma-ko-app.apk'
    apk_path = os.path.join(settings.BASE_DIR, 'static', 'apk', apk_filename)
    
    if not os.path.exists(apk_path):
        raise Http404("APK file not found")
    
    try:
        with open(apk_path, 'rb') as apk_file:
            response = HttpResponse(apk_file.read(), content_type='application/vnd.android.package-archive')
            response['Content-Disposition'] = f'attachment; filename="{apk_filename}"'
            response['Content-Length'] = os.path.getsize(apk_path)
            return response
    except Exception as e:
        raise Http404(f"Error serving APK file: {str(e)}")


def about(request):
    """About Us page for SEO and company information"""
    context = {
        'page_title': 'About Soma Ko Ghana',
        'meta_description': 'Learn about Soma Ko Ghana - your all-in-one marketplace platform for shopping, food delivery, pharmacy, equipment rental, and ride-hailing services across Ghana.',
    }
    return render(request, 'core/about.html', context)


def contact(request):
    """Contact page for customer inquiries"""
    context = {
        'page_title': 'Contact Soma Ko Ghana',
        'meta_description': 'Get in touch with Soma Ko Ghana. Contact our support team for assistance with orders, deliveries, or any questions about our services.',
    }
    return render(request, 'core/contact.html', context)


def privacy_policy(request):
    """Privacy Policy page"""
    context = {
        'page_title': 'Privacy Policy - Soma Ko Ghana',
        'meta_description': 'Read the Soma Ko Ghana privacy policy. Learn how we collect, use, and protect your personal information.',
    }
    return render(request, 'core/privacy_policy.html', context)


def terms_of_service(request):
    """Terms of Service page"""
    context = {
        'page_title': 'Terms of Service - Soma Ko Ghana',
        'meta_description': 'Read the Soma Ko Ghana terms of service. Understand the rules and guidelines for using our platform.',
    }
    return render(request, 'core/terms_of_service.html', context)