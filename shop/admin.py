from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import (
    Category, Product, ProductImage, ProductVariant, Order,
    Payment, Review
)
from .scrapers import MockAliExpressScraper


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'order']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['sku', 'name', 'size', 'color', 'price_adjustment', 'stock_quantity', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'base_price', 'is_featured', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'sku', 'description', 'brand')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    inlines = [ProductImageInline, ProductVariantInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('scrape-products/', self.admin_site.admin_view(self.scrape_products_view), name='shop_product_scrape'),
        ]
        return custom_urls + urls

    def scrape_products_view(self, request):
        """Admin view for scraping products"""
        if request.method == 'POST':
            count = int(request.POST.get('count', 10))
            category_id = request.POST.get('category')

            category = None
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    pass

            scraper = MockAliExpressScraper()
            products = scraper.bulk_generate(
                count=count,
                category=category,
                created_by=request.user
            )

            messages.success(
                request,
                f'Successfully imported {len(products)} products!'
            )
            return redirect('admin:shop_product_changelist')

        # GET request - show form
        categories = Category.objects.filter(is_active=True)
        context = {
            'title': 'Scrape Products from AliExpress',
            'categories': categories,
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        return render(request, 'admin/shop/scrape_products.html', context)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text', 'is_primary', 'order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'sku', 'stock_quantity', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__name', 'sku', 'name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    list_per_page = 25


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('order__order_number', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'helpful_count', 'created_at')
    list_filter = ('rating', 'is_approved', 'is_verified_purchase', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
