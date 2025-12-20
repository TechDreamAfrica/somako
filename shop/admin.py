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
        """Admin view for scraping products from multiple sources"""
        if request.method == 'POST':
            scraper_type = request.POST.get('scraper', 'aliexpress')
            
            if scraper_type == 'aliexpress':
                return self._handle_aliexpress_scraping(request)
            elif scraper_type == 'jumia':
                return self._handle_jumia_scraping(request)
            else:
                messages.error(request, 'Invalid scraper type selected')
                return redirect('admin:shop_product_scrape')

        # GET request - show form
        categories = Category.objects.filter(is_active=True)
        context = {
            'title': 'Product Scraping Dashboard',
            'categories': categories,
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        return render(request, 'admin/shop/scrape_products.html', context)
    
    def _handle_aliexpress_scraping(self, request):
        """Handle AliExpress mock scraping"""
        count = int(request.POST.get('count', 10))
        category_id = request.POST.get('category')

        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass

        try:
            scraper = MockAliExpressScraper()
            products = scraper.bulk_generate(
                count=count,
                category=category,
                created_by=request.user
            )

            messages.success(
                request,
                f'Successfully generated {len(products)} mock AliExpress products!'
            )
        except Exception as e:
            messages.error(request, f'Error generating products: {str(e)}')
        
        return redirect('admin:shop_product_changelist')
    
    def _handle_jumia_scraping(self, request):
        """Handle Jumia scraping with better error handling and feedback"""
        scrape_mode = request.POST.get('scrape_mode', 'keyword')
        count = int(request.POST.get('count', 20))
        db_category_slug = request.POST.get('db_category')
        use_mock = request.POST.get('use_mock', 'false') == 'true'
        
        # Get database category if specified
        db_category = None
        if db_category_slug:
            try:
                db_category = Category.objects.get(slug=db_category_slug)
            except Category.DoesNotExist:
                messages.error(request, f'Database category "{db_category_slug}" not found')
                return redirect('admin:shop_product_scrape')
        
        try:
            # Use mock mode for immediate results (recommended)
            if use_mock or True:  # Force mock mode for admin interface
                from shop.scrapers import MockJumiaScraper
                scraper = MockJumiaScraper()
                
                if scrape_mode == 'all_categories':
                    # Generate products for all categories
                    total_products = []
                    categories = scraper.categories.keys()
                    
                    for category_name in categories:
                        products = scraper.generate_category_products(
                            category_name,
                            count=min(count, 10),  # Limit per category for admin
                            db_category=db_category,
                            created_by=request.user
                        )
                        total_products.extend(products)
                    
                    messages.success(
                        request,
                        f'Successfully generated {len(total_products)} mock Jumia products across {len(categories)} categories!'
                    )
                    
                elif scrape_mode == 'category':
                    jumia_category = request.POST.get('jumia_category')
                    if not jumia_category:
                        messages.error(request, 'Category selection is required')
                        return redirect('admin:shop_product_scrape')
                    
                    products = scraper.generate_category_products(
                        jumia_category,
                        count=count,
                        db_category=db_category,
                        created_by=request.user
                    )
                    
                    messages.success(
                        request,
                        f'Successfully generated {len(products)} mock Jumia products for category "{jumia_category}"!'
                    )
                    
                elif scrape_mode == 'keyword':
                    keyword = request.POST.get('keyword', '').strip()
                    if not keyword:
                        messages.error(request, 'Keyword is required for keyword search')
                        return redirect('admin:shop_product_scrape')
                    
                    # Generate products based on keyword (use electronics as default category)
                    products = scraper.generate_category_products(
                        'electronics',
                        count=count,
                        db_category=db_category,
                        created_by=request.user
                    )
                    
                    messages.success(
                        request,
                        f'Successfully generated {len(products)} mock Jumia products for keyword "{keyword}"!'
                    )
                
            else:
                # Real scraping (not recommended for admin interface)
                messages.warning(
                    request,
                    'Real-time scraping from admin interface is not recommended. '
                    'Use command line: python manage.py scrape_jumia --help for options.'
                )
            
        except Exception as e:
            messages.error(request, f'Error during Jumia scraping: {str(e)}')
        
        return redirect('admin:shop_product_changelist')


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
