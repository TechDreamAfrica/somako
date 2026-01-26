from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Prefetch, Count, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal
import uuid

from .models import (
    Product, ProductVariant, ProductImage, Category, Shop,
    Cart, CartItem, Wishlist, WishlistItem,
    Order, OrderItem, OrderStatusHistory, Payment,
    Review
)


# ============================================================================
# SHOP VIEWS
# ============================================================================

def shop_list(request):
    """
    Display list of shops with search, filters, and pagination.
    """
    shops = Shop.objects.filter(status='active').annotate(
        product_count_annotated=Count('products', filter=Q(products__is_active=True))
    ).select_related('owner')

    # Search functionality
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

    # Filter by minimum rating
    min_rating = request.GET.get('rating', '').strip()
    if min_rating:
        try:
            shops = shops.filter(average_rating__gte=float(min_rating))
        except ValueError:
            pass

    # Filter by featured
    if request.GET.get('featured') == 'true':
        shops = shops.filter(is_featured=True)

    # Filter by verified
    if request.GET.get('verified') == 'true':
        shops = shops.filter(is_verified=True)

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

    # Get unique cities for filter dropdown
    cities = Shop.objects.filter(status='active').values_list('city', flat=True).distinct().order_by('city')

    # Get unique business types for filter dropdown
    business_types = Shop.objects.filter(status='active').exclude(
        business_type=''
    ).values_list('business_type', flat=True).distinct().order_by('business_type')

    # Pagination
    paginator = Paginator(shops, 12)
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
    return render(request, 'shop/shop_list.html', context)


def shop_detail(request, slug):
    """
    Display shop details with products listing.
    """
    shop = get_object_or_404(Shop, slug=slug, status='active')

    # Get products for this shop
    products = Product.objects.filter(
        shop=shop,
        is_active=True
    ).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True)),
        Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True)),
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
    return render(request, 'shop/shop_detail.html', context)


# ============================================================================
# PRODUCT VIEWS
# ============================================================================

def product_list(request):
    """
    Display list of products with search, filters, and pagination.
    Supports filtering by category, price range, brand, and search query.
    """
    # Base queryset with optimizations
    products = Product.objects.filter(is_active=True).select_related(
        'category'
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True)),
        Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True)),
        Prefetch('reviews', queryset=Review.objects.filter(is_approved=True))
    ).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )

    # Search functionality
    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(sku__icontains=search_query)
        )

    # Category filter
    category_param = request.GET.get('category')
    selected_category = None
    if category_param:
        # Try to get category by slug first, then by ID (for backwards compatibility)
        try:
            selected_category = Category.objects.get(slug=category_param, is_active=True)
        except Category.DoesNotExist:
            # Try by ID if slug lookup fails
            try:
                selected_category = Category.objects.get(id=int(category_param), is_active=True)
            except (Category.DoesNotExist, ValueError):
                # Invalid category parameter, skip filter
                pass

        if selected_category:
            # Include products from subcategories
            categories = [selected_category]
            categories.extend(selected_category.children.filter(is_active=True))
            products = products.filter(category__in=categories)

    # Brand filter
    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand=brand)

    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(base_price__gte=Decimal(min_price))
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            products = products.filter(base_price__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass

    # Featured filter
    if request.GET.get('featured') == 'true':
        products = products.filter(is_featured=True)

    # In stock filter
    if request.GET.get('in_stock') == 'true':
        products = products.filter(variants__stock_quantity__gt=0).distinct()

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'name': 'name',
        '-name': '-name',
        'price': 'base_price',
        '-price': '-base_price',
        'newest': '-created_at',
        'oldest': 'created_at',
        'rating': '-avg_rating',
    }
    sort_field = valid_sorts.get(sort_by, '-created_at')
    products = products.order_by(sort_field)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 20)  # 20 products per page

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # Get all categories for sidebar
    categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).prefetch_related('children')

    # Get all brands for filter
    brands = Product.objects.filter(
        is_active=True
    ).values_list('brand', flat=True).distinct().order_by('brand')

    context = {
        'products': products_page,
        'categories': categories,
        'brands': brands,
        'selected_category': selected_category,
        'search_query': search_query,
        'current_sort': sort_by,
        'filters': {
            'category': selected_category.slug if selected_category else None,
            'brand': brand,
            'min_price': min_price,
            'max_price': max_price,
        }
    }

    return render(request, 'shop/product_list.html', context)


def product_detail(request, slug):
    """
    Display detailed product information with variants and reviews.
    """
    # Get product with related data
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related(
            'images',
            Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True)),
            Prefetch(
                'reviews',
                queryset=Review.objects.filter(is_approved=True).select_related(
                    'user'
                ).prefetch_related('images').order_by('-created_at')
            )
        ),
        slug=slug,
        is_active=True
    )

    # Calculate review statistics
    reviews = product.reviews.filter(is_approved=True)
    review_stats = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id'),
        five_star=Count('id', filter=Q(rating=5)),
        four_star=Count('id', filter=Q(rating=4)),
        three_star=Count('id', filter=Q(rating=3)),
        two_star=Count('id', filter=Q(rating=2)),
        one_star=Count('id', filter=Q(rating=1)),
    )

    # Check if user has purchased this product (for review eligibility)
    user_can_review = False
    if request.user.is_authenticated:
        user_can_review = OrderItem.objects.filter(
            order__user=request.user,
            variant__product=product,
            order__status='delivered'
        ).exists() and not Review.objects.filter(
            product=product,
            user=request.user
        ).exists()

    # Check if product is in user's wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = WishlistItem.objects.filter(
            wishlist__user=request.user,
            product=product
        ).exists()

    # Get related products (same category)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )[:6]

    context = {
        'product': product,
        'review_stats': review_stats,
        'user_can_review': user_can_review,
        'in_wishlist': in_wishlist,
        'related_products': related_products,
    }

    return render(request, 'shop/product_detail.html', context)


def category_products(request, slug):
    """
    Display products filtered by category.
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # Get all subcategories
    categories = [category]
    categories.extend(category.children.filter(is_active=True))

    # Get products in this category and subcategories
    products = Product.objects.filter(
        category__in=categories,
        is_active=True
    ).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True)),
        Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True))
    ).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
    )

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'name': 'name',
        '-name': '-name',
        'price': 'base_price',
        '-price': '-base_price',
        'newest': '-created_at',
    }
    products = products.order_by(valid_sorts.get(sort_by, '-created_at'))

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 20)

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    context = {
        'category': category,
        'products': products_page,
        'subcategories': category.children.filter(is_active=True),
        'current_sort': sort_by,
    }

    return render(request, 'shop/product_list.html', context)


# ============================================================================
# CART VIEWS
# ============================================================================

def get_or_create_cart(request):
    """
    Helper function to get or create cart for user or session.
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Use session key for anonymous users
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


@require_POST
def add_to_cart(request, variant_id):
    """
    Add a product variant to the cart.
    """
    variant = get_object_or_404(
        ProductVariant.objects.select_related('product'),
        id=variant_id,
        is_active=True
    )

    # Check if product is active
    if not variant.product.is_active:
        messages.error(request, 'This product is no longer available.')
        return redirect('shop:product_list')

    # Get quantity from request
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    # Check stock availability
    if variant.stock_quantity < quantity:
        messages.error(
            request,
            f'Only {variant.stock_quantity} units available in stock.'
        )
        return redirect('shop:product_detail', slug=variant.product.slug)

    # Get or create cart
    cart = get_or_create_cart(request)

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={'quantity': quantity}
    )

    if not created:
        # Update quantity if item already exists
        new_quantity = cart_item.quantity + quantity
        if new_quantity > variant.stock_quantity:
            messages.error(
                request,
                f'Cannot add more items. Only {variant.stock_quantity} units available.'
            )
            return redirect('shop:cart_view')
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f'Updated {variant.product.name} quantity in cart.')
    else:
        messages.success(request, f'Added {variant.product.name} to cart.')

    # Redirect based on request
    next_url = request.POST.get('next', 'shop:cart_view')
    return redirect(next_url)


def cart_view(request):
    """
    Display shopping cart with all items.
    """
    cart = get_or_create_cart(request)

    # Get cart items with related data
    cart_items = cart.items.select_related(
        'variant__product',
        'variant__product__category'
    ).prefetch_related(
        'variant__product__images'
    )

    # Calculate totals
    subtotal = cart.subtotal
    shipping_cost = Decimal('25.00') if subtotal > 0 else Decimal('0.00')  # Default door delivery
    total = subtotal + shipping_cost

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    }

    return render(request, 'shop/cart.html', context)


@require_POST
def update_cart(request, item_id):
    """
    Update cart item quantity or remove item.
    """
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    action = request.POST.get('action')

    if action == 'remove':
        product_name = cart_item.variant.product.name
        cart_item.delete()
        messages.success(request, f'Removed {product_name} from cart.')
    elif action == 'update':
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1:
                cart_item.delete()
                messages.success(request, 'Item removed from cart.')
            elif quantity > cart_item.variant.stock_quantity:
                messages.error(
                    request,
                    f'Only {cart_item.variant.stock_quantity} units available.'
                )
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Cart updated successfully.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity.')

    return redirect('shop:cart_view')


# ============================================================================
# CHECKOUT & ORDER VIEWS
# ============================================================================

@login_required
def checkout(request):
    """
    Checkout process - collect shipping and payment information.
    """
    cart = get_or_create_cart(request)

    # Check if cart is empty
    if cart.items.count() == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('shop:cart_view')

    # Get cart items with related data
    cart_items = cart.items.select_related(
        'variant__product'
    ).prefetch_related('variant__product__images')

    # Check stock availability for all items
    stock_issues = []
    for item in cart_items:
        if item.quantity > item.variant.stock_quantity:
            stock_issues.append(
                f'{item.variant.product.name}: Only {item.variant.stock_quantity} available'
            )

    if stock_issues:
        for issue in stock_issues:
            messages.error(request, issue)
        return redirect('shop:cart_view')

    # Calculate totals
    subtotal = cart.subtotal

    # Default to door delivery shipping cost
    shipping_cost = Decimal('25.00')
    total = subtotal + shipping_cost

    if request.method == 'POST':
        # Process checkout form
        try:
            # Get delivery and payment methods
            delivery_method = request.POST.get('delivery_method', 'door_delivery')
            payment_method = request.POST.get('payment_method', 'online_payment')

            # Calculate shipping cost based on delivery method
            if delivery_method == 'pickup':
                shipping_cost = Decimal('0.00')
            else:
                shipping_cost = Decimal('25.00')

            # Recalculate total
            total = subtotal + shipping_cost

            # Generate unique order number and payment reference
            order_number = f'ORD-{uuid.uuid4().hex[:12].upper()}'
            payment_reference = f'SHOP-{uuid.uuid4().hex[:12].upper()}'

            # Create order
            order = Order.objects.create(
                order_number=order_number,
                user=request.user,
                status='pending' if payment_method == 'online_payment' else 'confirmed',
                delivery_method=delivery_method,
                payment_method=payment_method,
                subtotal=subtotal,
                tax_amount=Decimal('0.00'),  # No tax
                shipping_cost=shipping_cost,
                total_amount=total,
                # Shipping information
                shipping_address=request.POST.get('shipping_address'),
                shipping_city=request.POST.get('shipping_city'),
                shipping_state=request.POST.get('shipping_state'),
                shipping_postal_code=request.POST.get('shipping_postal_code', ''),
                shipping_country=request.POST.get('shipping_country', 'Ghana'),
                # Billing information
                billing_address=request.POST.get('billing_address') or request.POST.get('shipping_address'),
                billing_city=request.POST.get('billing_city') or request.POST.get('shipping_city'),
                billing_state=request.POST.get('billing_state') or request.POST.get('shipping_state'),
                billing_postal_code=request.POST.get('billing_postal_code') or request.POST.get('shipping_postal_code', ''),
                billing_country=request.POST.get('billing_country') or request.POST.get('shipping_country', 'Ghana'),
                # Contact information
                customer_email=request.POST.get('email', request.user.email),
                customer_phone=request.POST.get('phone'),
                notes=request.POST.get('notes', ''),
            )

            # Create order items (don't reduce stock yet - wait for payment)
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=cart_item.variant,
                    product_name=cart_item.variant.product.name,
                    variant_name=cart_item.variant.name,
                    sku=cart_item.variant.sku,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    total_price=cart_item.total_price,
                )

            # Create order status history
            OrderStatusHistory.objects.create(
                order=order,
                status='pending' if payment_method == 'online_payment' else 'confirmed',
                notes='Order created - Awaiting payment' if payment_method == 'online_payment' else 'Order confirmed - Cash on Delivery',
                changed_by=request.user
            )

            # Handle payment method
            if payment_method == 'cash_on_delivery':
                # Cash on delivery - no online payment needed
                # Clear cart
                cart.items.all().delete()
                
                # Send SMS notification to shop owner(s)
                try:
                    from utils.sms_utils import send_shop_order_notification_to_seller
                    send_shop_order_notification_to_seller(order)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send shop order notification: {e}")

                messages.success(
                    request,
                    f'Order placed successfully! Your order number is {order.order_number}. Please pay {total} GHS when you receive your order.'
                )
                return redirect('shop:order_detail', order_number=order.order_number)
            else:
                # Online payment - Initialize Paystack transaction
                from payment.models import Payment as PaymentModel
                from payment.paystack import PaystackAPI

                payment = PaymentModel.objects.create(
                    user=request.user,
                    amount=total,
                    currency='GHS',
                    payment_method='paystack',
                    status='pending',
                    source_app='shop',
                    order_id=order_number,
                    paystack_reference=payment_reference,
                    customer_email=order.customer_email,
                    customer_phone=order.customer_phone,
                    description=f'Shop Order {order_number}',
                    metadata={
                        'order_number': order_number,
                        'order_id': order.id,
                        'user_id': request.user.id,
                        'username': request.user.username,
                    }
                )

                # Initialize Paystack transaction
                paystack = PaystackAPI()
                from django.urls import reverse
                callback_url = request.build_absolute_uri(reverse('shop:payment_verify', args=[payment_reference]))

                result = paystack.initialize_transaction(
                    email=order.customer_email,
                    amount=total,
                    reference=payment_reference,
                    callback_url=callback_url,
                    metadata=payment.metadata
                )

                if result['status']:
                    # Update payment with Paystack details
                    payment.paystack_access_code = result['data'].get('access_code')
                    payment.paystack_authorization_url = result['data'].get('authorization_url')
                    payment.save()

                    # Redirect to Paystack payment page
                    return redirect(result['data'].get('authorization_url'))
                else:
                    # Payment initialization failed
                    order.delete()
                    payment.delete()
                    messages.error(request, f'Payment initialization failed: {result["message"]}')
                    return redirect('shop:checkout')

        except Exception as e:
            messages.error(request, f'Error processing order: {str(e)}')
            return redirect('shop:checkout')

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    }

    return render(request, 'shop/checkout.html', context)


@login_required
def order_list(request):
    """
    Display list of user's orders.
    """
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.select_related('variant__product')
        )
    ).order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    context = {
        'orders': orders_page,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    }

    return render(request, 'shop/order_list.html', context)


@login_required
def order_detail(request, order_number):
    """
    Display detailed order information.
    """
    # Try to determine if order_number is actually an ID (numeric)
    try:
        order_id = int(order_number)
        # If it's numeric, search by ID
        order = get_object_or_404(
            Order.objects.prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related(
                        'variant__product'
                    ).prefetch_related('variant__product__images')
                ),
                Prefetch(
                    'payments',
                    queryset=Payment.objects.order_by('-created_at')
                ),
                Prefetch(
                    'status_history',
                    queryset=OrderStatusHistory.objects.select_related(
                        'changed_by'
                    ).order_by('-created_at')
                )
            ),
            id=order_id,
            user=request.user
        )
    except ValueError:
        # If it's not numeric, search by order_number
        order = get_object_or_404(
            Order.objects.prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related(
                        'variant__product'
                    ).prefetch_related('variant__product__images')
                ),
                Prefetch(
                    'payments',
                    queryset=Payment.objects.order_by('-created_at')
                ),
                Prefetch(
                    'status_history',
                    queryset=OrderStatusHistory.objects.select_related(
                        'changed_by'
                    ).order_by('-created_at')
                )
            ),
            order_number=order_number,
            user=request.user
        )

    context = {
        'order': order,
    }

    return render(request, 'shop/order_detail.html', context)


# ============================================================================
# WISHLIST VIEWS
# ============================================================================

@login_required
def wishlist_view(request):
    """
    Display user's wishlist.
    """
    # Get or create default wishlist
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user,
        name="My Wishlist"
    )

    # Get wishlist items with related data
    wishlist_items = wishlist.items.select_related(
        'product__category',
        'variant'
    ).prefetch_related(
        Prefetch(
            'product__images',
            queryset=ProductImage.objects.filter(is_primary=True)
        ),
        'product__variants'
    )

    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist_items,
    }

    return render(request, 'shop/wishlist.html', context)


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    """
    Add or remove product from wishlist.
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)

    # Get or create default wishlist
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user,
        name="My Wishlist"
    )

    # Get variant if specified
    variant_id = request.POST.get('variant_id')
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    # Check if item exists in wishlist
    wishlist_item = WishlistItem.objects.filter(
        wishlist=wishlist,
        product=product,
        variant=variant
    ).first()

    if wishlist_item:
        # Remove from wishlist
        wishlist_item.delete()
        messages.success(request, f'Removed {product.name} from wishlist.')
        in_wishlist = False
    else:
        # Add to wishlist
        WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            variant=variant
        )
        messages.success(request, f'Added {product.name} to wishlist.')
        in_wishlist = True

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'total_items': wishlist.total_items
        })

    # Redirect for normal requests
    next_url = request.POST.get('next', 'shop:wishlist_view')
    return redirect(next_url)

# ============================================================================
# PAYMENT VERIFICATION
# ============================================================================

@login_required
def payment_verify(request, reference):
    """
    Verify Paystack payment and update order status
    """
    from payment.models import Payment as PaymentModel
    from payment.paystack import PaystackAPI
    from shop.models import Order, OrderStatusHistory

    try:
        # Get payment record
        payment = get_object_or_404(PaymentModel, paystack_reference=reference, user=request.user)

        # Verify with Paystack
        paystack = PaystackAPI()
        result = paystack.verify_transaction(reference)

        if result['status'] and result['data'].get('status') == 'success':
            # Payment successful
            payment.status = 'completed'
            payment.paid_at = timezone.now()
            payment.save()

            # Get order
            order = Order.objects.get(order_number=payment.order_id)
            order.status = 'confirmed'
            order.save()

            # Reduce stock quantities
            for order_item in order.items.all():
                order_item.variant.stock_quantity -= order_item.quantity
                order_item.variant.save()

            # Update order history
            OrderStatusHistory.objects.create(
                order=order,
                status='confirmed',
                notes='Payment verified successfully',
                changed_by=request.user
            )

            # Clear cart
            from shop.models import Cart
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart.items.all().delete()
            
            # Send SMS notification to shop owner(s)
            try:
                from utils.sms_utils import send_shop_order_notification_to_seller
                send_shop_order_notification_to_seller(order)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send shop order notification: {e}")

            messages.success(
                request,
                f'Payment successful! Your order {order.order_number} has been confirmed.'
            )
            return redirect('shop:order_detail', order_number=order.order_number)
        else:
            # Payment failed
            payment.status = 'failed'
            payment.save()

            # Update order
            order = Order.objects.get(order_number=payment.order_id)
            order.status = 'cancelled'
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status='cancelled',
                notes='Payment verification failed',
                changed_by=request.user
            )

            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('shop:checkout')

    except PaymentModel.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('shop:product_list')
    except Exception as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
        return redirect('shop:product_list')

