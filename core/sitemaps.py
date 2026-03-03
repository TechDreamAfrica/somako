"""
Sitemaps for SEO optimization
Generates XML sitemaps for search engines to index all public pages
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from shop.models import Shop, Product, Category as ShopCategory
from food.models import Restaurant, MenuItem, FoodCategory
from rent.models import Equipment, EquipmentCategory
from pharmacy.models import Pharmacy, Medicine, MedicineCategory


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 1.0
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            'core:home',
            'core:downloads',
            'core:about',
            'core:contact',
            'core:privacy_policy',
            'core:terms_of_service',
            'shop:shop_list',
            'shop:product_list',
            'food:restaurant_list',
            'rent:equipment_list',
            'pharmacy:pharmacy_list',
            'pharmacy:medicine_list',
        ]

    def location(self, item):
        return reverse(item)


class ShopSitemap(Sitemap):
    """Sitemap for shops"""
    changefreq = 'daily'
    priority = 0.8
    protocol = 'https'

    def items(self):
        return Shop.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('shop:shop_detail', kwargs={'slug': obj.slug})


class ProductSitemap(Sitemap):
    """Sitemap for products"""
    changefreq = 'daily'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return Product.objects.filter(is_active=True, shop__is_active=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('shop:product_detail', kwargs={'slug': obj.slug})


class ShopCategorySitemap(Sitemap):
    """Sitemap for shop categories"""
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        return ShopCategory.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('shop:category_products', kwargs={'slug': obj.slug})


class RestaurantSitemap(Sitemap):
    """Sitemap for restaurants"""
    changefreq = 'daily'
    priority = 0.8
    protocol = 'https'

    def items(self):
        return Restaurant.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('food:restaurant_detail', kwargs={'slug': obj.slug})


class PharmacySitemap(Sitemap):
    """Sitemap for pharmacies"""
    changefreq = 'daily'
    priority = 0.8
    protocol = 'https'

    def items(self):
        return Pharmacy.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('pharmacy:pharmacy_detail', kwargs={'slug': obj.slug})


class MedicineSitemap(Sitemap):
    """Sitemap for medicines"""
    changefreq = 'daily'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return Medicine.objects.filter(is_active=True, pharmacy__is_active=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('pharmacy:medicine_detail', kwargs={'slug': obj.slug})


class EquipmentSitemap(Sitemap):
    """Sitemap for rental equipment"""
    changefreq = 'daily'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return Equipment.objects.filter(is_available=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('rent:equipment_detail', kwargs={'pk': obj.pk})


# Aggregate all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'shops': ShopSitemap,
    'products': ProductSitemap,
    'shop-categories': ShopCategorySitemap,
    'restaurants': RestaurantSitemap,
    'pharmacies': PharmacySitemap,
    'medicines': MedicineSitemap,
    'equipment': EquipmentSitemap,
}
