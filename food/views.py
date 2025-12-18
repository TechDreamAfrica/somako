from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Prefetch, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal
import uuid

from .models import (
    Restaurant,
    MenuItem,
    FoodCategory,
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderItemAddon,
    Review,
    DeliveryZone,
    Addon
)
from payment.helpers import create_payment, initialize_paystack_payment


# ========================
# Restaurant Views
# ========================

def restaurant_list(request):
    """
    Display list of restaurants with search, filters, and pagination.
    Supports filtering by city, category, rating, and search query.
    """
    restaurants = Restaurant.objects.filter(status='active').select_related('owner').prefetch_related(
        'operating_hours',
        Prefetch('menu_items', queryset=MenuItem.objects.filter(is_available=True))
    )

    # Search functionality
    search_query = request.GET.get('q', '').strip()
    if search_query:
        restaurants = restaurants.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # Filter by city
    city = request.GET.get('city', '').strip()
    if city:
        restaurants = restaurants.filter(city__iexact=city)

    # Filter by minimum rating
    min_rating = request.GET.get('min_rating', '').strip()
    if min_rating:
        try:
            min_rating = float(min_rating)
            restaurants = restaurants.filter(average_rating__gte=min_rating)
        except ValueError:
            pass

    # Filter by featured
    featured = request.GET.get('featured', '').strip()
    if featured == 'true':
        restaurants = restaurants.filter(is_featured=True)

    # Filter by food category
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        restaurants = restaurants.filter(
            menu_items__category__slug=category_slug
        ).distinct()

    # Sorting
    sort_by = request.GET.get('sort', '-is_featured')
    valid_sorts = {
        'rating': '-average_rating',
        'name': 'name',
        'delivery_time': 'delivery_time',
        'featured': '-is_featured'
    }
    sort_field = valid_sorts.get(sort_by, '-is_featured')
    restaurants = restaurants.order_by(sort_field, '-average_rating')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(restaurants, 12)  # 12 restaurants per page

    try:
        restaurants_page = paginator.page(page)
    except PageNotAnInteger:
        restaurants_page = paginator.page(1)
    except EmptyPage:
        restaurants_page = paginator.page(paginator.num_pages)

    # Get all cities for filter dropdown
    cities = Restaurant.objects.filter(status='active').values_list('city', flat=True).distinct().order_by('city')

    # Get all food categories for filter
    categories = FoodCategory.objects.filter(is_active=True)

    context = {
        'restaurants': restaurants_page,
        'cities': cities,
        'categories': categories,
        'search_query': search_query,
        'selected_city': city,
        'selected_category': category_slug,
        'min_rating': min_rating,
        'featured': featured,
        'sort_by': sort_by,
    }

    return render(request, 'food/restaurant_list.html', context)


def restaurant_detail(request, slug):
    """
    Display detailed restaurant information including menu and reviews.
    Optimized with select_related and prefetch_related for performance.
    """
    restaurant = get_object_or_404(
        Restaurant.objects.select_related('owner').prefetch_related(
            'operating_hours',
            'delivery_zones',
            Prefetch(
                'menu_items',
                queryset=MenuItem.objects.filter(is_available=True).select_related('category').prefetch_related('addons')
            ),
            Prefetch(
                'reviews',
                queryset=Review.objects.filter(
                    is_approved=True,
                    review_type='restaurant'
                ).select_related('customer').order_by('-created_at')
            )
        ),
        slug=slug,
        status='active'
    )

    # Get menu items grouped by category (fetch fresh to avoid slice issue)
    menu_items = MenuItem.objects.filter(
        restaurant=restaurant,
        is_available=True
    ).select_related('category').order_by('category__display_order', '-is_featured', 'name')

    # Get food categories for this restaurant
    categories = FoodCategory.objects.filter(
        menu_items__restaurant=restaurant,
        is_active=True
    ).distinct().order_by('display_order')

    # Filter by category if specified
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        menu_items = menu_items.filter(category__slug=category_slug)

    # Get reviews with pagination (fetch fresh to avoid slice issue)
    reviews = Review.objects.filter(
        restaurant=restaurant,
        is_approved=True,
        review_type='restaurant'
    ).select_related('customer').order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(reviews, 10)  # 10 reviews per page

    try:
        reviews_page = paginator.page(page)
    except PageNotAnInteger:
        reviews_page = paginator.page(1)
    except EmptyPage:
        reviews_page = paginator.page(paginator.num_pages)

    # Check if restaurant is currently open
    is_open = restaurant.is_open_now()

    context = {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'categories': categories,
        'selected_category': category_slug,
        'reviews': reviews_page,
        'is_open': is_open,
    }

    return render(request, 'food/restaurant_detail.html', context)


def restaurant_menu(request, slug):
    """
    Display full menu for a restaurant with category filtering.
    """
    restaurant = get_object_or_404(
        Restaurant.objects.prefetch_related(
            Prefetch(
                'menu_items',
                queryset=MenuItem.objects.filter(is_available=True).select_related('category').prefetch_related(
                    'addons__category'
                )
            )
        ),
        slug=slug,
        status='active'
    )

    # Get all menu items
    menu_items = restaurant.menu_items.filter(is_available=True)

    # Filter by category if specified
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        menu_items = menu_items.filter(category__slug=category_slug)

    # Filter by dietary preferences
    if request.GET.get('vegetarian') == 'true':
        menu_items = menu_items.filter(is_vegetarian=True)
    if request.GET.get('vegan') == 'true':
        menu_items = menu_items.filter(is_vegan=True)
    if request.GET.get('gluten_free') == 'true':
        menu_items = menu_items.filter(is_gluten_free=True)

    # Search in menu
    search_query = request.GET.get('q', '').strip()
    if search_query:
        menu_items = menu_items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Sorting
    sort_by = request.GET.get('sort', '-is_featured')
    valid_sorts = {
        'price_low': 'price',
        'price_high': '-price',
        'rating': '-average_rating',
        'popular': '-total_reviews',
        'featured': '-is_featured'
    }
    sort_field = valid_sorts.get(sort_by, '-is_featured')
    menu_items = menu_items.order_by(sort_field, 'name')

    # Get food categories for this restaurant
    categories = FoodCategory.objects.filter(
        menu_items__restaurant=restaurant,
        is_active=True
    ).distinct().order_by('display_order')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(menu_items, 20)  # 20 items per page

    try:
        menu_page = paginator.page(page)
    except PageNotAnInteger:
        menu_page = paginator.page(1)
    except EmptyPage:
        menu_page = paginator.page(paginator.num_pages)

    context = {
        'restaurant': restaurant,
        'menu_items': menu_page,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    return render(request, 'food/restaurant_menu.html', context)


# ========================
# Cart Views
# ========================

@login_required
@require_POST
def add_to_cart(request):
    """
    Add menu item to cart with optional addons.
    Handles AJAX requests and returns JSON response.
    """
    try:
        menu_item_id = request.POST.get('menu_item_id')
        quantity = int(request.POST.get('quantity', 1))
        special_instructions = request.POST.get('special_instructions', '').strip()
        addon_ids = request.POST.getlist('addons[]')

        # Validate menu item
        menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)

        # Validate quantity
        if quantity < 1:
            return JsonResponse({
                'success': False,
                'message': 'Quantity must be at least 1'
            }, status=400)

        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if item already exists in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            defaults={
                'quantity': quantity,
                'special_instructions': special_instructions
            }
        )

        if not item_created:
            # Update existing cart item
            cart_item.quantity = F('quantity') + quantity
            cart_item.special_instructions = special_instructions
            cart_item.save()
            cart_item.refresh_from_db()

        # Add addons if provided
        if addon_ids:
            addons = Addon.objects.filter(
                id__in=addon_ids,
                menu_item=menu_item,
                is_available=True
            )
            cart_item.addons.set(addons)

        messages.success(request, f'{menu_item.name} has been added to your cart.')

        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'{menu_item.name} added to cart',
                'cart_count': cart.get_item_count(),
                'cart_total': float(cart.get_total())
            })

        # Redirect for regular form submissions
        return redirect('food:cart_view')

    except MenuItem.DoesNotExist:
        messages.error(request, 'Menu item not found or unavailable.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Menu item not found'
            }, status=404)
        return redirect('food:restaurant_list')

    except ValueError:
        messages.error(request, 'Invalid quantity provided.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity'
            }, status=400)
        return redirect('food:restaurant_list')

    except Exception as e:
        messages.error(request, 'An error occurred while adding item to cart.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
        return redirect('food:restaurant_list')


@login_required
def cart_view(request):
    """
    Display shopping cart with all items.
    """
    try:
        cart = Cart.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=CartItem.objects.select_related(
                    'menu_item__restaurant',
                    'menu_item__category'
                ).prefetch_related('addons')
            )
        ).get(user=request.user)

        cart_items = cart.items.all()

        # Check if all items are from the same restaurant
        restaurants = set(item.menu_item.restaurant for item in cart_items)
        multiple_restaurants = len(restaurants) > 1

        if multiple_restaurants:
            messages.warning(
                request,
                'Your cart contains items from multiple restaurants. '
                'Please note that you can only checkout items from one restaurant at a time.'
            )

        # Calculate totals
        subtotal = cart.get_total()

        # Get delivery fee (simplified - in production, calculate based on delivery zone)
        delivery_fee = Decimal('5.00') if subtotal > 0 else Decimal('0.00')

        # Calculate tax (example: 10%)
        tax = subtotal * Decimal('0.10')

        # Calculate total
        total = subtotal + delivery_fee + tax

        context = {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'tax': tax,
            'total': total,
            'multiple_restaurants': multiple_restaurants,
        }

    except Cart.DoesNotExist:
        context = {
            'cart': None,
            'cart_items': [],
            'subtotal': Decimal('0.00'),
            'delivery_fee': Decimal('0.00'),
            'tax': Decimal('0.00'),
            'total': Decimal('0.00'),
        }

    return render(request, 'food/cart_view.html', context)


@login_required
@require_POST
def update_cart(request):
    """
    Update cart item quantity or remove item from cart.
    Handles AJAX requests.
    """
    try:
        action = request.POST.get('action')
        cart_item_id = request.POST.get('cart_item_id')

        cart_item = get_object_or_404(
            CartItem.objects.select_related('cart', 'menu_item'),
            id=cart_item_id,
            cart__user=request.user
        )

        # Get cart reference before any operations (in case item gets deleted)
        cart = cart_item.cart

        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'Updated {cart_item.menu_item.name} quantity.')

        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, f'Updated {cart_item.menu_item.name} quantity.')
            else:
                item_name = cart_item.menu_item.name
                cart_item.delete()
                messages.success(request, f'Removed {item_name} from cart.')

        elif action == 'remove':
            item_name = cart_item.menu_item.name
            cart_item.delete()
            messages.success(request, f'Removed {item_name} from cart.')

        elif action == 'update_quantity':
            new_quantity = int(request.POST.get('quantity', 1))
            if new_quantity < 1:
                item_name = cart_item.menu_item.name
                cart_item.delete()
                messages.success(request, f'Removed {item_name} from cart.')
            else:
                cart_item.quantity = new_quantity
                cart_item.save()
                messages.success(request, f'Updated {cart_item.menu_item.name} quantity.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': cart.get_item_count(),
                'cart_total': float(cart.get_total()),
                'item_subtotal': float(cart_item.get_subtotal()) if cart_item.id else 0
            })

        return redirect('food:cart_view')

    except CartItem.DoesNotExist:
        messages.error(request, 'Cart item not found.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Cart item not found'
            }, status=404)
        return redirect('food:cart_view')

    except ValueError:
        messages.error(request, 'Invalid quantity provided.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity'
            }, status=400)
        return redirect('food:cart_view')

    except Exception as e:
        messages.error(request, 'An error occurred while updating cart.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
        return redirect('food:cart_view')


# ========================
# Order Views
# ========================

@login_required
def checkout(request):
    """
    Process checkout and create order from cart items.
    """
    try:
        cart = Cart.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=CartItem.objects.select_related(
                    'menu_item__restaurant'
                ).prefetch_related('addons')
            )
        ).get(user=request.user)

        cart_items = cart.items.all()

        if not cart_items.exists():
            messages.warning(request, 'Your cart is empty.')
            return redirect('food:restaurant_list')

        # Check if all items are from the same restaurant
        restaurants = list(set(item.menu_item.restaurant for item in cart_items))
        if len(restaurants) > 1:
            messages.error(
                request,
                'You can only order from one restaurant at a time. '
                'Please remove items from other restaurants.'
            )
            return redirect('food:cart_view')

        restaurant = restaurants[0]

        # Get available delivery zones for the restaurant
        delivery_zones = DeliveryZone.objects.filter(
            Q(restaurant=restaurant) | Q(restaurant__isnull=True),
            is_active=True
        )

        if request.method == 'POST':
            # Process checkout
            delivery_address = request.POST.get('delivery_address', '').strip()
            delivery_city = request.POST.get('delivery_city', '').strip()
            delivery_phone = request.POST.get('delivery_phone', '').strip()
            delivery_instructions = request.POST.get('delivery_instructions', '').strip()
            payment_method = request.POST.get('payment_method')
            delivery_method = request.POST.get('delivery_method', 'door_delivery')
            delivery_zone_id = request.POST.get('delivery_zone')

            # Validate required fields
            if not all([delivery_address, delivery_city, delivery_phone, payment_method, delivery_method]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('food:checkout')

            # Get delivery zone
            delivery_zone = None
            if delivery_zone_id:
                delivery_zone = get_object_or_404(DeliveryZone, id=delivery_zone_id, is_active=True)

            # Calculate order totals
            subtotal = cart.get_total()

            # Calculate delivery fee based on delivery method
            if delivery_method == 'pickup':
                delivery_fee = Decimal('0.00')
            else:
                delivery_fee = delivery_zone.delivery_fee if delivery_zone else Decimal('25.00')

            # No tax
            tax = Decimal('0.00')
            total_amount = subtotal + delivery_fee

            # Check minimum order amount
            if restaurant.minimum_order_amount > subtotal:
                messages.error(
                    request,
                    f'Minimum order amount is {restaurant.minimum_order_amount}. '
                    f'Please add more items.'
                )
                return redirect('food:cart_view')

            # Generate unique order number
            order_number = f'ORD-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'

            # Create order
            order = Order.objects.create(
                order_number=order_number,
                customer=request.user,
                restaurant=restaurant,
                delivery_method=delivery_method,
                payment_method=payment_method,
                delivery_zone=delivery_zone,
                delivery_address=delivery_address,
                delivery_city=delivery_city,
                delivery_phone=delivery_phone,
                delivery_instructions=delivery_instructions,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                tax=tax,
                total_amount=total_amount,
                status='confirmed' if payment_method == 'cash_on_delivery' else 'pending',
                payment_status='pending'
            )

            # Create order items from cart items
            for cart_item in cart_items:
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.get_display_price(),
                    special_instructions=cart_item.special_instructions
                )

                # Add addons to order item
                for addon in cart_item.addons.all():
                    OrderItemAddon.objects.create(
                        order_item=order_item,
                        addon_name=addon.name,
                        addon_price=addon.price
                    )

            # Clear cart
            cart_items.delete()

            # Send SMS notifications
            try:
                from utils.sms_utils import send_order_notification, send_customer_order_confirmation
                
                # Notify restaurant owner
                send_order_notification(order, status_change=False)
                
                # Notify customer
                send_customer_order_confirmation(order)
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send SMS notification: {str(e)}")

            # Handle payment
            if payment_method == 'cash_on_delivery':
                # Cash on delivery - order is confirmed, payment on delivery
                messages.success(
                    request,
                    f'Order placed successfully! Your order number is {order_number}. Please pay GHS {total_amount} when you receive your order.'
                )
                return redirect('food:order_detail', order_number=order_number)
            elif payment_method == 'online_payment':
                # Create payment record and initialize Paystack
                try:
                    payment = create_payment(
                        user=request.user,
                        amount=total_amount,
                        source_app='food',
                        order_id=order_number,
                        description=f'Food Order {order_number} from {restaurant.name}',
                        payment_method='paystack'
                    )

                    # Initialize Paystack transaction
                    result = initialize_paystack_payment(payment)

                    if result['status']:
                        # Redirect to Paystack payment page
                        return redirect(result['authorization_url'])
                    else:
                        # Payment initialization failed
                        order.payment_status = 'failed'
                        order.save()
                        messages.error(request, f"Payment initialization failed: {result['message']}")
                        return redirect('food:order_detail', order_number=order_number)
                except Exception as e:
                    # Log the error
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Payment initialization error for order {order_number}: {str(e)}", exc_info=True)

                    # Update order status
                    order.payment_status = 'failed'
                    order.save()

                    # Show user-friendly error
                    messages.error(
                        request,
                        f"We encountered an error processing your payment. Please try again or contact support. Error: {str(e)}"
                    )
                    return redirect('food:order_detail', order_number=order_number)
            else:
                # Other payment methods
                messages.success(
                    request,
                    f'Order placed successfully! Your order number is {order_number}.'
                )
                return redirect('food:order_detail', order_number=order_number)

        # GET request - show checkout form
        from django.conf import settings
        subtotal = cart.get_total()
        delivery_fee = Decimal('25.00')  # Default door delivery fee
        total = subtotal + delivery_fee  # No tax

        context = {
            'cart': cart,
            'cart_items': cart_items,
            'restaurant': restaurant,
            'delivery_zones': delivery_zones,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': total,
            'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
        }

        return render(request, 'food/checkout.html', context)

    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty.')
        return redirect('food:restaurant_list')


@login_required
def order_list(request):
    """
    Display list of user's orders with filtering and pagination.
    """
    orders = Order.objects.filter(customer=request.user).select_related(
        'restaurant',
        'delivery_zone'
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.select_related('menu_item')
        )
    ).order_by('-created_at')

    # Filter by status
    status = request.GET.get('status', '').strip()
    if status:
        orders = orders.filter(status=status)

    # Filter by date range
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=date_to)
        except ValueError:
            pass

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # 10 orders per page

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    context = {
        'orders': orders_page,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Order.STATUS_CHOICES,
    }

    return render(request, 'food/order_list.html', context)


@login_required
def order_detail(request, order_number):
    """
    Display detailed order information.
    """
    order = get_object_or_404(
        Order.objects.select_related(
            'restaurant',
            'delivery_zone',
            'driver'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('menu_item').prefetch_related('addons')
            )
        ),
        order_number=order_number,
        customer=request.user
    )

    # Check if order can be cancelled
    can_cancel = order.can_cancel()

    # Check if order can be reviewed
    can_review = order.can_review()

    context = {
        'order': order,
        'can_cancel': can_cancel,
        'can_review': can_review,
    }

    return render(request, 'food/order_detail.html', context)


@login_required
def track_order(request, order_number):
    """
    Track order status and delivery progress in real-time.
    """
    order = get_object_or_404(
        Order.objects.select_related(
            'restaurant',
            'driver',
            'delivery_zone'
        ),
        order_number=order_number,
        customer=request.user
    )

    # Define order status timeline
    status_timeline = [
        {
            'status': 'pending',
            'label': 'Order Pending',
            'description': 'Your order is being processed',
            'icon': 'clock',
            'completed': order.status in ['confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way', 'delivered']
        },
        {
            'status': 'confirmed',
            'label': 'Order Confirmed',
            'description': 'Restaurant has confirmed your order',
            'icon': 'check-circle',
            'completed': order.status in ['preparing', 'ready', 'picked_up', 'on_the_way', 'delivered']
        },
        {
            'status': 'preparing',
            'label': 'Preparing Food',
            'description': 'Your food is being prepared',
            'icon': 'utensils',
            'completed': order.status in ['ready', 'picked_up', 'on_the_way', 'delivered']
        },
        {
            'status': 'ready',
            'label': 'Ready for Pickup',
            'description': 'Your order is ready',
            'icon': 'box',
            'completed': order.status in ['picked_up', 'on_the_way', 'delivered']
        },
        {
            'status': 'on_the_way',
            'label': 'On the Way',
            'description': 'Driver is on the way to deliver your order',
            'icon': 'truck',
            'completed': order.status == 'delivered'
        },
        {
            'status': 'delivered',
            'label': 'Delivered',
            'description': 'Order has been delivered',
            'icon': 'check',
            'completed': order.status == 'delivered'
        }
    ]

    # Calculate estimated delivery time if not set
    if not order.estimated_delivery_time and order.status in ['confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way']:
        preparation_time = order.restaurant.delivery_time
        if order.delivery_zone:
            preparation_time += order.delivery_zone.estimated_delivery_time
        order.estimated_delivery_time = order.created_at + timezone.timedelta(minutes=preparation_time)

    context = {
        'order': order,
        'status_timeline': status_timeline,
        'current_status': order.status,
    }

    return render(request, 'food/track_order.html', context)
