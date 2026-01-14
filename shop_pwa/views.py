"""
Shop PWA Views - Progressive Web App specific views
Optimized for mobile-first experience with touch-friendly interfaces
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from shop.models import (
    Product, ProductVariant, ProductImage, Category, Shop,
    Cart, CartItem, Order, OrderItem, Review,
    Wishlist, WishlistItem
)


# ============================================
# SHOP VIEWS
# ============================================

@login_required
def pwa_shop_list(request):
    """PWA Shop List - Browse all shops"""
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'shop'

    shops = Shop.objects.filter(status='active').annotate(
        product_count_annotated=Count('products', filter=Q(products__is_active=True))
    ).select_related('owner')

    # Search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        shops = shops.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(business_type__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # Filter by city
    city = request.GET.get('city', '').strip()
    if city:
        shops = shops.filter(city__iexact=city)

    # Filter by business type
    business_type = request.GET.get('type', '').strip()
    if business_type:
        shops = shops.filter(business_type__icontains=business_type)

    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'rating':
        shops = shops.order_by('-average_rating', '-is_featured')
    elif sort_by == 'name':
        shops = shops.order_by('name')
    elif sort_by == 'newest':
        shops = shops.order_by('-created_at')
    else:
        shops = shops.order_by('-is_featured', '-average_rating')

    # Get unique cities and business types
    cities = Shop.objects.filter(status='active').values_list('city', flat=True).distinct().order_by('city')
    business_types = Shop.objects.filter(status='active').exclude(
        business_type=''
    ).values_list('business_type', flat=True).distinct().order_by('business_type')

    # Pagination
    paginator = Paginator(shops, 10)
    page = request.GET.get('page', 1)
    try:
        shops_page = paginator.page(page)
    except PageNotAnInteger:
        shops_page = paginator.page(1)
    except EmptyPage:
        shops_page = paginator.page(paginator.num_pages)

    context = {
        'shops': shops_page,
        'cities': cities,
        'business_types': business_types,
        'search_query': search_query,
        'selected_city': city,
        'selected_type': business_type,
        'selected_sort': sort_by,
    }
    return render(request, 'shop/pwa/shop_list.html', context)


@login_required
def pwa_shop_detail(request, pk):
    """PWA Shop Detail - View shop and its products"""
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'shop'

    shop = get_object_or_404(Shop, pk=pk, status='active')

    # Get products for this shop
    products = Product.objects.filter(
        shop=shop,
        is_active=True
    ).select_related('category').prefetch_related(
        'images',
        'variants',
    ).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )

    # Search within shop
    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )

    # Filter by category
    category_slug = request.GET.get('category', '').strip()
    selected_category = None
    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug, is_active=True)
            products = products.filter(category=selected_category)
        except Category.DoesNotExist:
            pass

    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'price_low':
        products = products.order_by('base_price')
    elif sort_by == 'price_high':
        products = products.order_by('-base_price')
    elif sort_by == 'rating':
        products = products.order_by('-avg_rating')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('-is_featured', '-created_at')

    # Get categories with products in this shop
    categories = Category.objects.filter(
        products__shop=shop,
        products__is_active=True,
        is_active=True
    ).distinct().order_by('name')

    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    context = {
        'shop': shop,
        'products': products_page,
        'categories': categories,
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_sort': sort_by,
    }
    return render(request, 'shop/pwa/shop_detail.html', context)


# ============================================
# CUSTOMER VIEWS
# ============================================

@login_required
def pwa_dashboard(request):
    """PWA Shop Dashboard - Role-based (Customer/Seller)"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'shop'

    user = request.user
    # Check if user has seller role and has products
    is_seller = user.has_role('seller') and Product.objects.filter(created_by=user).exists()

    if is_seller:
        return redirect('shop_pwa:owner_dashboard')

    # Customer dashboard
    context = {
        'featured_products': Product.objects.filter(
            is_active=True, is_featured=True
        ).order_by('-created_at')[:6],
        'recent_products': Product.objects.filter(
            is_active=True
        ).order_by('-created_at')[:8],
        'recent_orders': Order.objects.filter(
            user=user
        ).order_by('-created_at')[:3],
        'cart_count': CartItem.objects.filter(cart__user=user).count(),
        'wishlist_count': WishlistItem.objects.filter(wishlist__user=user).count(),
    }
    return render(request, 'shop/pwa/dashboard.html', context)


@login_required
def pwa_product_list(request):
    """Browse all products"""
    products = Product.objects.filter(is_active=True).select_related('category')

    # Filters
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'newest')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=category)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )

    # Sorting
    if sort == 'price_low':
        products = products.order_by('base_price')
    elif sort == 'price_high':
        products = products.order_by('-base_price')
    elif sort == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:  # newest
        products = products.order_by('-created_at')

    context = {
        'products': products,
        'categories': Category.objects.filter(is_active=True, parent__isnull=True),
        'selected_category': category_slug,
        'selected_sort': sort,
        'search_query': search_query,
    }
    return render(request, 'shop/pwa/product_list.html', context)


@login_required
def pwa_product_detail(request, pk):
    """Product details page"""
    product = get_object_or_404(Product, pk=pk, is_active=True)

    # Get product variants and images
    variants = ProductVariant.objects.filter(product=product, is_active=True)
    images = ProductImage.objects.filter(product=product)
    reviews = Review.objects.filter(product=product, is_approved=True).order_by('-created_at')[:10]

    # Check if in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            in_wishlist = WishlistItem.objects.filter(wishlist=wishlist, product=product).exists()

    context = {
        'product': product,
        'variants': variants,
        'images': images,
        'reviews': reviews,
        'in_wishlist': in_wishlist,
        'avg_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
        'review_count': reviews.count(),
    }
    return render(request, 'shop/pwa/product_detail.html', context)


@login_required
def pwa_category_products(request, category):
    """Products filtered by category"""
    category_obj = get_object_or_404(Category, slug=category, is_active=True)
    products = Product.objects.filter(category=category_obj, is_active=True).order_by('-created_at')

    context = {
        'category': category_obj,
        'products': products,
    }
    return render(request, 'shop/pwa/category_products.html', context)


@login_required
def pwa_cart_view(request):
    """View shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('variant__product')

    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    shipping_fee = Decimal('10.00')  # You can make this dynamic
    tax = subtotal * Decimal('0.15')  # 15% tax
    total = subtotal + shipping_fee + tax

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'tax': tax,
        'total': total,
        'can_checkout': cart_items.exists(),
    }
    return render(request, 'shop/pwa/cart.html', context)


@login_required
def pwa_add_to_cart(request, product_id):
    """Add item to cart (AJAX)"""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        variant_id = request.POST.get('variant_id')

        cart, created = Cart.objects.get_or_create(user=request.user)

        # Get variant if specified
        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, pk=variant_id, product=product)
        else:
            # If no variant specified, attempt sensible default
            active_variants = product.variants.filter(is_active=True)
            if active_variants.count() == 1:
                variant = active_variants.first()
            else:
                msg = 'Please select a product option before adding to cart.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('shop_pwa:product_detail', pk=product.id)

        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f'{product.name} added to cart!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': CartItem.objects.filter(cart=cart).count(),
                'message': f'{product.name} added to cart!'
            })

        return redirect('shop_pwa:cart')

    return redirect('shop_pwa:product_list')


@login_required
def pwa_update_cart_item(request, cart_item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart__user=request.user)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated!')
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart!')

    return redirect('shop_pwa:cart')


@login_required
def pwa_remove_from_cart(request, cart_item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('shop_pwa:cart')


@login_required
def pwa_clear_cart(request):
    """Clear entire cart"""
    CartItem.objects.filter(cart__user=request.user).delete()
    messages.success(request, 'Cart cleared!')
    return redirect('shop_pwa:cart')


@login_required
def pwa_checkout(request):
    """Checkout page"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('variant__product')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('shop_pwa:product_list')

    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    shipping_fee = Decimal('10.00')
    tax = subtotal * Decimal('0.15')  # 15% tax
    total = subtotal + shipping_fee + tax

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'tax': tax,
        'total': total,
        'user': request.user,
    }
    return render(request, 'shop/pwa/checkout.html', context)


@login_required
def pwa_confirm_order(request):
    """Process order confirmation"""
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty!')
            return redirect('shop_pwa:product_list')

        # Get delivery details
        shipping_address = request.POST.get('shipping_address')
        shipping_phone = request.POST.get('shipping_phone')
        payment_method = request.POST.get('payment_method', 'cash')
        notes = request.POST.get('notes', '')

        # Calculate totals
        subtotal = sum(item.total_price for item in cart_items)
        shipping_cost = Decimal('10.00')
        tax = subtotal * Decimal('0.15')
        total = subtotal + shipping_cost + tax

        # Generate order number
        import uuid
        order_number = f"SHO-{uuid.uuid4().hex[:8].upper()}"

        # Create order
        order = Order.objects.create(
            order_number=order_number,
            user=request.user,
            shipping_address=shipping_address,
            shipping_city='Accra',  # Default city
            shipping_state='Greater Accra',  # Default state
            shipping_postal_code='00233',  # Default postal code
            shipping_country='Ghana',  # Default country
            billing_address=shipping_address,  # Same as shipping
            billing_city='Accra',
            billing_state='Greater Accra',
            billing_postal_code='00233',
            billing_country='Ghana',
            customer_phone=shipping_phone,
            customer_email=request.user.email,
            payment_method=payment_method,
            notes=notes,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax,
            total_amount=total,
            status='pending'
        )

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                price=cart_item.variant.price if cart_item.variant else cart_item.product.base_price
            )

        # Clear cart
        cart_items.delete()

        messages.success(request, f'Order placed successfully! Order #{order.order_number}')
        return redirect('shop_pwa:order_detail', order_number=order.order_number)

    return redirect('shop_pwa:checkout')


@login_required
def pwa_order_list(request):
    """View order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'shop/pwa/order_list.html', context)


@login_required
def pwa_order_detail(request, order_number):
    """View order details"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    context = {
        'order': order,
        'order_items': order.items.all(),
        'can_cancel': order.status in ['pending', 'processing'],
    }
    return render(request, 'shop/pwa/order_detail.html', context)


@login_required
def pwa_track_order(request, order_number):
    """Track order status"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    # Order progress stages
    stages = [
        {'status': 'pending', 'label': 'Order Placed', 'icon': 'fa-check-circle'},
        {'status': 'processing', 'label': 'Processing', 'icon': 'fa-cog'},
        {'status': 'shipped', 'label': 'Shipped', 'icon': 'fa-truck'},
        {'status': 'out_for_delivery', 'label': 'Out for Delivery', 'icon': 'fa-shipping-fast'},
        {'status': 'delivered', 'label': 'Delivered', 'icon': 'fa-home'},
    ]

    context = {
        'order': order,
        'stages': stages,
    }
    return render(request, 'shop/pwa/track_order.html', context)


@login_required
def pwa_cancel_order(request, order_number):
    """Cancel an order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status in ['pending', 'processing']:
        order.status = 'cancelled'
        order.save()
        messages.success(request, 'Order cancelled successfully!')
    else:
        messages.error(request, 'This order cannot be cancelled.')

    return redirect('shop_pwa:order_detail', order_number=order_number)


@login_required
def pwa_search(request):
    """Search products"""
    query = request.GET.get('q', '')

    products = []
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(brand__icontains=query),
            is_active=True
        )[:20]

    context = {
        'query': query,
        'products': products,
    }
    return render(request, 'shop/pwa/search.html', context)


@login_required
def pwa_favorites(request):
    """View favorite products"""
    wishlist = Wishlist.objects.filter(user=request.user).first()
    wishlist_items = []

    if wishlist:
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product')

    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'shop/pwa/favorites.html', context)


@login_required
def pwa_toggle_favorite(request, product_id):
    """Toggle product favorite status"""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()

    if wishlist_item:
        wishlist_item.delete()
        messages.success(request, f'{product.name} removed from favorites!')
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        messages.success(request, f'{product.name} added to favorites!')

    return redirect('shop_pwa:product_detail', pk=product_id)


# ============================================
# SELLER/OWNER VIEWS
# ============================================

@login_required
def pwa_owner_dashboard(request):
    """Shop seller dashboard - comprehensive statistics for product sellers"""
    # Check if user has seller role
    if not request.user.has_role('seller'):
        messages.error(request, 'You need to be a seller to access this page.')
        return redirect('shop_pwa:dashboard')
    
    # Get user's products
    user_products = Product.objects.filter(created_by=request.user)
    
    if not user_products.exists():
        messages.info(request, 'You haven\'t created any products yet. Start selling by adding your first product!')
        return redirect('shop_pwa:add_product')
    
    today = date.today()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # Week and month dates
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))
    
    month_start = today.replace(day=1)
    month_start_dt = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))
    
    # ============================================
    # ORDER STATISTICS
    # ============================================
    
    # Get all orders containing user's products
    all_orders = Order.objects.filter(items__variant__product__created_by=request.user).distinct()
    total_orders = all_orders.count()
    
    # Today's orders
    today_orders = all_orders.filter(
        created_at__range=(today_start, today_end)
    ).count()
    
    # Orders by status
    pending_orders = all_orders.filter(status__in=['pending', 'processing']).count()
    shipped_orders = all_orders.filter(status='shipped').count()
    delivered_orders = all_orders.filter(status='delivered').count()
    
    # Active orders needing attention
    active_orders = pending_orders + all_orders.filter(status='out_for_delivery').count()
    
    # Completed today
    completed_today = all_orders.filter(
        created_at__range=(today_start, today_end),
        status='delivered'
    ).count()
    
    # ============================================
    # REVENUE STATISTICS
    # ============================================
    
    # Calculate revenue from order items (seller's portion only)
    from django.db.models import Sum, Count, Avg
    
    def calculate_seller_revenue(orders_qs):
        """Calculate total revenue from seller's products in orders"""
        items = OrderItem.objects.filter(
            order__in=orders_qs,
            variant__product__created_by=request.user
        )
        total = items.aggregate(
            revenue=Sum('total_price')
        )['revenue'] or Decimal('0.00')
        return total
    
    # Today's revenue
    today_orders_qs = all_orders.filter(created_at__range=(today_start, today_end))
    today_revenue = calculate_seller_revenue(today_orders_qs)
    
    # Week revenue
    week_orders_qs = all_orders.filter(created_at__gte=week_start_dt)
    week_revenue = calculate_seller_revenue(week_orders_qs)
    
    # Month revenue
    month_orders_qs = all_orders.filter(created_at__gte=month_start_dt)
    month_revenue = calculate_seller_revenue(month_orders_qs)
    
    # Total revenue
    total_revenue = calculate_seller_revenue(all_orders)
    
    # Average order value (for seller's items)
    avg_order_value = OrderItem.objects.filter(
        variant__product__created_by=request.user
    ).aggregate(
        avg=Avg('total_price')
    )['avg'] or Decimal('0.00')
    
    # ============================================
    # PRODUCT STATISTICS
    # ============================================
    
    total_products = user_products.count()
    active_products = user_products.filter(is_active=True).count()
    inactive_products = total_products - active_products
    featured_products = user_products.filter(is_featured=True).count()
    
    # ============================================
    # POPULAR PRODUCTS
    # ============================================
    
    # Popular products (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    popular_products = OrderItem.objects.filter(
        variant__product__created_by=request.user,
        order__created_at__gte=thirty_days_ago
    ).values(
        'variant__product__name',
        'variant__product__id'
    ).annotate(
        quantity_sold=Sum('quantity'),
        times_ordered=Count('id'),
        revenue=Sum('total_price')
    ).order_by('-quantity_sold')[:5]
    
    # Popular products today
    popular_products_today = OrderItem.objects.filter(
        variant__product__created_by=request.user,
        order__created_at__range=(today_start, today_end)
    ).values(
        'variant__product__name'
    ).annotate(
        quantity_sold=Sum('quantity')
    ).order_by('-quantity_sold')[:5]
    
    # ============================================
    # RECENT ORDERS
    # ============================================
    
    recent_orders = all_orders.select_related(
        'user'
    ).prefetch_related('items__variant__product').order_by('-created_at')[:10]
    
    # ============================================
    # CONTEXT
    # ============================================
    
    context = {
        # User info
        'seller_name': request.user.get_full_name() or request.user.username,
        
        # Order counts
        'total_orders': total_orders,
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'active_orders': active_orders,
        'completed_today': completed_today,
        
        # Revenue
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        
        # Products
        'total_products': total_products,
        'active_products': active_products,
        'inactive_products': inactive_products,
        'featured_products': featured_products,
        
        # Popular products
        'popular_products': popular_products,
        'popular_products_today': popular_products_today,
        
        # Orders
        'recent_orders': recent_orders,
        
        # Dates
        'today': today,
        'week_start': week_start,
        'month_start': month_start,
    }
    return render(request, 'shop/pwa/owner/dashboard.html', context)


@login_required
def pwa_manage_orders(request):
    """Manage shop orders containing seller's products"""
    # Get orders containing user's products
    orders = Order.objects.filter(
        items__variant__product__created_by=request.user
    ).distinct().order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'shop/pwa/owner/manage_orders.html', context)


@login_required
def pwa_order_detail_owner(request, order_id):
    """View order details (owner perspective) - shows only seller's items in the order"""
    order = get_object_or_404(
        Order.objects.filter(items__variant__product__created_by=request.user).distinct(),
        pk=order_id
    )
    
    # Get only the items that belong to this seller
    seller_items = order.items.filter(variant__product__created_by=request.user)

    context = {
        'order': order,
        'order_items': seller_items,
        'seller_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'shop/pwa/owner/order_detail.html', context)


@login_required
def pwa_update_order_status(request, order_id):
    """Update order status (for orders with seller's products)"""
    order = get_object_or_404(
        Order.objects.filter(items__variant__product__created_by=request.user).distinct(),
        pk=order_id
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = ['pending', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled']

        if new_status in valid_statuses:
            order.status
            order.status = new_status
            order.save()
            
            # Send SMS notification to customer
            try:
                from utils.sms_utils import send_custom_sms
                customer_phone = getattr(order, 'customer_phone', None)
                if customer_phone:
                    message = (
                        f"SOMA KO SHOP - Order #{order.order_number} status updated to {new_status.upper()}. "
                        f"Track your order in the app."
                    )
                    send_custom_sms(customer_phone, message)
                    messages.success(request, f'Order status updated to {new_status}. Customer notified via SMS.')
                else:
                    messages.success(request, f'Order status updated to {new_status}.')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send SMS: {str(e)}")
                messages.success(request, f'Order status updated to {new_status}. SMS notification failed.')
            
            return redirect('shop_pwa:order_detail_owner', order_id=order_id)

    return redirect('shop_pwa:manage_orders')


@login_required
def pwa_manage_products(request):
    """Manage products"""
    # Get user's products
    products = Product.objects.filter(created_by=request.user).order_by('-created_at')

    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)

    categories = Category.objects.filter(is_active=True)

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
        'products': products,
        'categories': categories,
        'category_filter': category_slug,
        'status_filter': status_filter,
    }
    return render(request, 'shop/pwa/owner/manage_products.html', context)


@login_required
def pwa_add_product(request):
    """Add new product"""
    if request.method == 'POST':
        # Process form - simplified version
        name = request.POST.get('name')
        description = request.POST.get('description')
        base_price = request.POST.get('base_price')
        category_id = request.POST.get('category')
        image_url = request.POST.get('image_url')

        category = get_object_or_404(Category, pk=category_id)

        product = Product.objects.create(
            created_by=request.user,  # Set creator
            name=name,
            description=description or '',
            base_price=base_price,
            category=category,
            is_active=True
        )

        # Optionally add a product image by URL
        if image_url:
            try:
                ProductImage.objects.create(
                    product=product,
                    image=image_url,
                    is_primary=True,
                    order=0
                )
            except Exception:
                pass

        messages.success(request, 'Product added successfully!')
        return redirect('shop_pwa:manage_products')

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'shop/pwa/owner/add_product.html', context)


@login_required
def pwa_edit_product(request, product_id):
    """Edit product"""
    product = get_object_or_404(Product, pk=product_id, created_by=request.user)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description') or ''
        product.base_price = request.POST.get('base_price')
        category_id = request.POST.get('category')
        product.category = get_object_or_404(Category, pk=category_id)
        product.save()

        messages.success(request, 'Product updated!')
        return redirect('shop_pwa:manage_products')

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
        'product': product,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'shop/pwa/owner/edit_product.html', context)


@login_required
def pwa_toggle_product(request, product_id):
    """Toggle product availability"""
    product = get_object_or_404(Product, pk=product_id, created_by=request.user)

    product.is_active = not product.is_active
    product.save()

    status = 'active' if product.is_active else 'inactive'
    messages.success(request, f'{product.name} is now {status}!')

    return redirect('shop_pwa:manage_products')


@login_required
def pwa_delete_product(request, product_id):
    """Delete product"""
    product = get_object_or_404(Product, pk=product_id, created_by=request.user)

    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'{product_name} deleted successfully!')
        return redirect('shop_pwa:manage_products')

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
        'product': product,
    }
    return render(request, 'shop/pwa/owner/delete_product.html', context)


@login_required
def pwa_analytics(request):
    """Shop analytics dashboard"""
    # Get user's products
    user_products = Product.objects.filter(created_by=request.user)

    # Get orders containing user's products
    user_orders = Order.objects.filter(
        items__variant__product__created_by=request.user
    ).distinct()

    # Calculate revenue from seller's items in orders
    def calculate_seller_revenue(orders_qs):
        """Calculate revenue from seller's products in orders"""
        items = OrderItem.objects.filter(
            order__in=orders_qs,
            variant__product__created_by=request.user
        )
        return items.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')

    paid_orders = user_orders.filter(status__in=['confirmed', 'processing', 'shipped', 'delivered'])

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
        'total_revenue': calculate_seller_revenue(paid_orders),
        'total_orders': user_orders.count(),
        'avg_order_value': (calculate_seller_revenue(paid_orders) / paid_orders.count()) if paid_orders.count() > 0 else 0,
        'popular_products': user_products.annotate(
            order_count=Count('variants__order_items')
        ).order_by('-order_count')[:5],
        'total_products': user_products.count(),
        'active_products': user_products.filter(is_active=True).count(),
    }
    return render(request, 'shop/pwa/owner/analytics.html', context)


@login_required
def pwa_shop_settings(request):
    """Shop settings"""
    if request.method == 'POST':
        # Update user profile settings
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        # You can add phone number if you have a profile model
        messages.success(request, 'Settings updated successfully!')
        return redirect('shop_pwa:shop_settings')

    context = {
        'seller_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'shop/pwa/owner/settings.html', context)


@login_required
def pwa_notifications(request):
    """View notifications"""
    # Implement notifications logic
    context = {
        'notifications': [],
    }
    return render(request, 'shop/pwa/notifications.html', context)
