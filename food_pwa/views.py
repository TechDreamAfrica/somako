"""
Food PWA Views - Progressive Web App specific views
Optimized for mobile-first experience with touch-friendly interfaces
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, date
from decimal import Decimal
import uuid

from food.models import Restaurant, MenuItem, Order, OrderItem, Cart, CartItem, FoodCategory, Review
from core.pwa_decorators import pwa_login_required


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_user_restaurant(user):
    """Get the restaurant owned by the user"""
    if hasattr(user, 'restaurants') and user.restaurants.exists():
        return user.restaurants.first()
    return None


# ============================================
# CUSTOMER VIEWS
# ============================================

@pwa_login_required(pwa_app='food')
def pwa_dashboard(request):
    """PWA Food Dashboard - Role-based (Customer/Owner)"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'food'

    user = request.user
    # Check if user has restaurant_owner role and has a restaurant
    restaurant = get_user_restaurant(user)

    if user.has_role('restaurant_owner') and restaurant:
        return redirect('food_pwa:owner_dashboard')

    # Customer dashboard
    context = {
        'featured_restaurants': Restaurant.objects.filter(
            status='active', is_featured=True
        ).order_by('-average_rating')[:6],
        'recent_restaurants': Restaurant.objects.filter(
            status='active'
        ).order_by('-created_at')[:4],
        'recent_orders': Order.objects.filter(
            customer=user
        ).order_by('-created_at')[:3],
        'cart_count': CartItem.objects.filter(cart__user=user).count(),
    }
    return render(request, 'food/pwa/dashboard.html', context)


@pwa_login_required(pwa_app='food')
def pwa_restaurant_list(request):
    """Browse all restaurants"""
    restaurants = Restaurant.objects.filter(status='active')

    # Filters
    city = request.GET.get('city')
    category = request.GET.get('category')
    sort = request.GET.get('sort', 'featured')

    if city:
        restaurants = restaurants.filter(city__icontains=city)

    if category:
        restaurants = restaurants.filter(menu_items__category__icontains=category).distinct()

    # Sorting
    if sort == 'rating':
        restaurants = restaurants.order_by('-average_rating')
    elif sort == 'delivery_time':
        restaurants = restaurants.order_by('delivery_time')
    else:  # featured
        restaurants = restaurants.order_by('-is_featured', '-average_rating')

    context = {
        'restaurants': restaurants,
        'cities': Restaurant.objects.values_list('city', flat=True).distinct(),
        'selected_city': city,
        'selected_sort': sort,
    }
    return render(request, 'food/pwa/restaurant_list.html', context)


@pwa_login_required(pwa_app='food')
def pwa_restaurant_detail(request, pk):
    """Restaurant details page"""
    restaurant = get_object_or_404(Restaurant, pk=pk, status='active')

    # Get all available menu items
    menu_items = MenuItem.objects.filter(
        restaurant=restaurant,
        is_available=True
    ).select_related('category').order_by('category', 'name')

    # Get categories with menu items
    categories = FoodCategory.objects.filter(
        menu_items__restaurant=restaurant,
        menu_items__is_available=True
    ).distinct()

    # Get total completed orders for this restaurant
    total_orders = Order.objects.filter(
        restaurant=restaurant,
        status='delivered'
    ).count()

    # Calculate total revenue
    total_revenue = Order.objects.filter(
        restaurant=restaurant,
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Get pending orders count
    pending_orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=['pending', 'confirmed', 'preparing']
    ).count()

    # Get today's statistics
    today = date.today()
    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    ).count()
    
    today_revenue = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today,
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Get recent reviews (top 5)
    reviews = Review.objects.filter(
        restaurant=restaurant
    ).select_related('customer').order_by('-created_at')[:5]

    # Calculate average rating and total reviews
    rating_data = Review.objects.filter(restaurant=restaurant).aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )

    context = {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'categories': categories,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'reviews': reviews,
        'average_rating': rating_data['avg_rating'] or 0,
        'total_reviews': rating_data['total_reviews'] or 0,
    }
    return render(request, 'food/pwa/restaurant_detail.html', context)


@pwa_login_required(pwa_app='food')
def pwa_restaurant_menu(request, pk):
    """Restaurant full menu - redirects to restaurant detail"""
    return redirect('food_pwa:restaurant_detail', pk=pk)


@pwa_login_required(pwa_app='food')
def pwa_cart_view(request):
    """View shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('menu_item__restaurant')

    # Calculate totals
    subtotal = sum(item.get_total_price() for item in cart_items)
    delivery_fee = Decimal('5.00')  # You can make this dynamic based on restaurant
    total = subtotal + delivery_fee

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'can_checkout': cart_items.exists(),
    }
    return render(request, 'food/pwa/cart.html', context)


@pwa_login_required(pwa_app='food')
def pwa_add_to_cart(request, menu_item_id):
    """Add item to cart (AJAX)"""
    if request.method == 'POST':
        menu_item = get_object_or_404(MenuItem, pk=menu_item_id, is_available=True)
        quantity = int(request.POST.get('quantity', 1))
        special_instructions = request.POST.get('special_instructions', '')

        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            defaults={'quantity': quantity, 'special_instructions': special_instructions}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f'{menu_item.name} added to cart!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': CartItem.objects.filter(cart=cart).count(),
                'message': f'{menu_item.name} added to cart!'
            })

        return redirect('food_pwa:cart')

    return redirect('food_pwa:restaurant_list')


@pwa_login_required(pwa_app='food')
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

    return redirect('food_pwa:cart')


@pwa_login_required(pwa_app='food')
def pwa_remove_from_cart(request, cart_item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('food_pwa:cart')


@pwa_login_required(pwa_app='food')
def pwa_clear_cart(request):
    """Clear entire cart"""
    CartItem.objects.filter(cart__user=request.user).delete()
    messages.success(request, 'Cart cleared!')
    return redirect('food_pwa:cart')


@pwa_login_required(pwa_app='food')
def pwa_checkout(request):
    """Checkout page"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('menu_item__restaurant')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('food_pwa:restaurant_list')

    # Calculate totals
    subtotal = sum(item.get_total_price() for item in cart_items)
    delivery_fee = Decimal('5.00')
    tax = subtotal * Decimal('0.15')  # 15% tax
    total = subtotal + delivery_fee + tax

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'tax': tax,
        'total': total,
        'user': request.user,
    }
    return render(request, 'food/pwa/checkout.html', context)


@pwa_login_required(pwa_app='food')
def pwa_confirm_order(request):
    """Process order confirmation"""
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty!')
            return redirect('food_pwa:restaurant_list')

        # Get delivery details
        delivery_address = request.POST.get('delivery_address', '')
        delivery_city = request.POST.get('delivery_city', 'Accra')
        delivery_phone = request.POST.get('delivery_phone', '')
        payment_method = request.POST.get('payment_method', 'cash_on_delivery')
        special_instructions = request.POST.get('special_instructions', '')

        # Validate required fields
        if not delivery_address or not delivery_phone:
            messages.error(request, 'Please provide delivery address and phone number')
            return redirect('food_pwa:checkout')

        # Calculate totals
        subtotal = sum(item.get_total_price() for item in cart_items)
        delivery_fee = Decimal('5.00')
        tax = subtotal * Decimal('0.15')
        total = subtotal + delivery_fee + tax

        # Generate unique order number
        order_number = f'FO-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'

        # Create order
        order = Order.objects.create(
            order_number=order_number,
            customer=request.user,
            restaurant=cart_items.first().menu_item.restaurant,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_phone=delivery_phone,
            payment_method=payment_method,
            delivery_instructions=special_instructions,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            tax=tax,
            total_amount=total,
            status='pending'
        )

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menu_item=cart_item.menu_item,
                quantity=cart_item.quantity,
                price=cart_item.menu_item.get_display_price(),
                special_instructions=cart_item.special_instructions
            )

        # Clear cart
        cart_items.delete()

        # Check payment method and redirect accordingly
        if payment_method not in ['cash_on_delivery', 'cash']:
            # Store order ID in session for post-payment reference
            request.session['pending_order_id'] = order.id
            
            # Prepare Paystack initiation via auto-post (payment:initiate expects POST)
            context = {
                'action_url_name': 'payment:initiate',
                'amount': str(total),  # Convert to string for template
                'source_app': 'food',
                'order_id': order.order_number,
                'description': f'Food Order #{order.order_number} from {order.restaurant.name}',
                'payment_method': payment_method,  # 'card' or 'mobile_money'
            }
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Redirecting to payment for order {order.order_number} - Amount: {total} GHS - Method: {payment_method}")
            
            return render(request, 'payment/auto_post.html', context)

        # For cash payments, send notifications immediately
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

        messages.success(request, f'Order placed successfully! Order #{order.order_number}')
        return redirect('food_pwa:order_detail', order_number=order.order_number)

    return redirect('food_pwa:checkout')


@pwa_login_required(pwa_app='food')
def pwa_order_list(request):
    """View order history"""
    orders = Order.objects.filter(
        customer=request.user,
        order_number__isnull=False
    ).exclude(order_number='').order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'food/pwa/order_list.html', context)


@pwa_login_required(pwa_app='food')
def pwa_order_detail(request, order_number):
    """View order details"""
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)

    context = {
        'order': order,
        'order_items': order.items.all(),
        'can_cancel': order.status in ['pending', 'confirmed'],
    }
    return render(request, 'food/pwa/order_detail.html', context)


@pwa_login_required(pwa_app='food')
def pwa_track_order(request, order_number):
    """Track order status"""
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)

    # Order progress stages
    stages = [
        {'status': 'pending', 'label': 'Order Placed', 'icon': 'fa-check-circle'},
        {'status': 'confirmed', 'label': 'Confirmed', 'icon': 'fa-clipboard-check'},
        {'status': 'preparing', 'label': 'Preparing', 'icon': 'fa-utensils'},
        {'status': 'ready', 'label': 'Ready', 'icon': 'fa-box'},
        {'status': 'out_for_delivery', 'label': 'Out for Delivery', 'icon': 'fa-motorcycle'},
        {'status': 'delivered', 'label': 'Delivered', 'icon': 'fa-home'},
    ]

    context = {
        'order': order,
        'stages': stages,
    }
    return render(request, 'food/pwa/track_order.html', context)


@pwa_login_required(pwa_app='food')
def pwa_cancel_order(request, order_number):
    """Cancel an order"""
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)

    if order.status in ['pending', 'confirmed']:
        order.status = 'cancelled'
        order.save()
        messages.success(request, 'Order cancelled successfully!')
    else:
        messages.error(request, 'This order cannot be cancelled.')

    return redirect('food_pwa:order_detail', order_number=order_number)


@pwa_login_required(pwa_app='food')
def pwa_reorder(request, order_number):
    """Reorder items from a previous order"""
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Add order items to cart
    for order_item in order.items.all():
        if order_item.menu_item.is_available:
            CartItem.objects.create(
                cart=cart,
                menu_item=order_item.menu_item,
                quantity=order_item.quantity,
                special_instructions=order_item.special_instructions
            )

    messages.success(request, 'Items added to cart!')
    return redirect('food_pwa:cart')


@pwa_login_required(pwa_app='food')
def pwa_search(request):
    """Search restaurants and menu items - redirects to restaurant list with query"""
    query = request.GET.get('q', '')
    if query:
        return redirect(f"{reverse('food_pwa:restaurant_list')}?search={query}")
    return redirect('food_pwa:restaurant_list')


@pwa_login_required(pwa_app='food')
def pwa_category_filter(request, category):
    """Filter restaurants by category - redirects to restaurant list"""
    return redirect(f"{reverse('food_pwa:restaurant_list')}?category={category}")


@pwa_login_required(pwa_app='food')
def pwa_favorites(request):
    """View favorite restaurants - placeholder, redirects to dashboard"""
    messages.info(request, 'Favorites feature coming soon!')
    return redirect('food_pwa:dashboard')


@pwa_login_required(pwa_app='food')
def pwa_toggle_favorite(request, restaurant_id):
    """Toggle restaurant favorite status - placeholder"""
    messages.info(request, 'Favorites feature coming soon!')
    return redirect('food_pwa:restaurant_detail', pk=restaurant_id)


# ============================================
# RESTAURANT OWNER VIEWS
# ============================================

@pwa_login_required(pwa_app='food')
def pwa_owner_dashboard(request):
    """Restaurant owner dashboard with comprehensive statistics"""
    # Check if user has restaurant_owner role
    if not request.user.has_role('restaurant_owner'):
        messages.error(request, 'You need to be a restaurant owner to access this page.')
        return redirect('food_pwa:dashboard')
    
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        messages.error(request, 'You do not have a restaurant profile.')
        return redirect('food_pwa:dashboard')
    
    today = date.today()
    timezone.now()
    
    import logging
    logger = logging.getLogger(__name__)
    
    # ============================================
    # ORDER COUNTS
    # ============================================
    
    # All orders
    all_orders = Order.objects.filter(restaurant=restaurant)
    total_orders = all_orders.count()
    
    # Today's orders - using timezone-aware datetime for accuracy
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    today_orders_qs = all_orders.filter(created_at__range=(today_start, today_end))
    today_orders = today_orders_qs.count()
    
    # Pending/Active orders (requiring attention)
    pending_orders = all_orders.filter(
        status__in=['pending', 'confirmed', 'preparing']
    ).count()
    
    # Completed orders today
    completed_today = all_orders.filter(
        created_at__range=(today_start, today_end),
        status='delivered'
    ).count()
    
    logger.info(f"Restaurant {restaurant.name} - Date: {today}")
    logger.info(f"Today's orders: {today_orders} | Pending: {pending_orders} | Completed today: {completed_today}")
    
    # ============================================
    # REVENUE STATISTICS
    # ============================================
    
    # Today's revenue - all paid orders today
    today_revenue = all_orders.filter(
        created_at__range=(today_start, today_end),
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # This week's revenue
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))
    week_revenue = all_orders.filter(
        created_at__gte=week_start_dt,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # This month's revenue
    month_start = today.replace(day=1)
    month_start_dt = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))
    month_revenue = all_orders.filter(
        created_at__gte=month_start_dt,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Total revenue (all time)
    total_revenue = all_orders.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    logger.info(f"Revenue - Today: {today_revenue} | Week: {week_revenue} | Month: {month_revenue} | Total: {total_revenue}")
    
    # ============================================
    # MENU ITEMS STATISTICS
    # ============================================
    
    all_menu_items = MenuItem.objects.filter(restaurant=restaurant)
    total_menu_items = all_menu_items.count()
    active_menu_items = all_menu_items.filter(is_available=True).count()
    inactive_menu_items = total_menu_items - active_menu_items
    
    # ============================================
    # POPULAR ITEMS (Today)
    # ============================================
    
    popular_items_today = OrderItem.objects.filter(
        order__restaurant=restaurant,
        order__created_at__range=(today_start, today_end)
    ).values(
        'menu_item__name',
        'menu_item__id'
    ).annotate(
        quantity_sold=Sum('quantity'),
        times_ordered=Count('id')
    ).order_by('-quantity_sold')[:5]
    
    # ============================================
    # RECENT ORDERS
    # ============================================
    
    recent_orders = all_orders.select_related('customer').prefetch_related(
        'items__menu_item'
    ).order_by('-created_at')[:10]
    
    # ============================================
    # AVERAGE ORDER VALUE
    # ============================================
    
    avg_order_value = all_orders.filter(
        payment_status='paid'
    ).aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0.00')
    
    # ============================================
    # ORDER STATUS BREAKDOWN
    # ============================================
    
    orders_by_status = {
        'pending': all_orders.filter(status='pending').count(),
        'confirmed': all_orders.filter(status='confirmed').count(),
        'preparing': all_orders.filter(status='preparing').count(),
        'ready': all_orders.filter(status='ready').count(),
        'on_the_way': all_orders.filter(status='on_the_way').count(),
        'delivered': all_orders.filter(status='delivered').count(),
        'cancelled': all_orders.filter(status='cancelled').count(),
    }
    
    # ============================================
    # CONTEXT
    # ============================================
    
    context = {
        'restaurant': restaurant,
        
        # Order counts
        'total_orders': total_orders,
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'completed_today': completed_today,
        
        # Revenue
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        
        # Menu items
        'total_menu_items': total_menu_items,
        'active_menu_items': active_menu_items,
        'inactive_menu_items': inactive_menu_items,
        
        # Popular items
        'popular_items_today': popular_items_today,
        
        # Orders
        'recent_orders': recent_orders,
        'orders_by_status': orders_by_status,
        
        # Date context
        'today': today,
        'week_start': week_start,
        'month_start': month_start,
    }
    
    return render(request, 'food/pwa/owner/dashboard.html', context)


@pwa_login_required(pwa_app='food')
def pwa_manage_orders(request):
    """Manage restaurant orders"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'restaurant': restaurant,
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'food/pwa/owner/manage_orders.html', context)


@pwa_login_required(pwa_app='food')
def pwa_order_detail_owner(request, order_id):
    """View order details (owner perspective)"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    order = get_object_or_404(Order, pk=order_id, restaurant=restaurant)

    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    return render(request, 'food/pwa/owner/order_detail.html', context)


@pwa_login_required(pwa_app='food')
def pwa_update_order_status(request, order_id):
    """Update order status"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    order = get_object_or_404(Order, pk=order_id, restaurant=restaurant)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES).keys():
            old_status = order.get_status_display()
            order.status = new_status
            order.save()

            # Send SMS notification to CUSTOMER on status change
            try:
                from utils.sms_utils import send_customer_order_status_update
                result = send_customer_order_status_update(order, new_status)
                if result.get('success'):
                    messages.info(request, 'Customer notified via SMS')
                else:
                    messages.warning(request, 'Status updated but SMS notification failed')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send customer SMS notification: {str(e)}")
                messages.warning(request, 'Status updated but SMS notification failed')

            messages.success(request, f'Order #{order.id} status changed from {old_status} to {order.get_status_display()}!')

        # Redirect back to owner dashboard
        return redirect('food_pwa:owner_dashboard')

    return redirect('food_pwa:owner_dashboard')


@pwa_login_required(pwa_app='food')
def pwa_manage_menu(request):
    """Manage menu items"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    menu_items = MenuItem.objects.filter(restaurant=restaurant).order_by('category', 'name')

    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        menu_items = menu_items.filter(category=category_filter)

    categories = MenuItem.objects.filter(restaurant=restaurant).values_list('category', flat=True).distinct()

    context = {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'categories': categories,
        'category_filter': category_filter,
    }
    return render(request, 'food/pwa/owner/manage_menu.html', context)


@pwa_login_required(pwa_app='food')
def pwa_add_menu_item(request):
    """Add new menu item"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')


    if request.method == 'POST':
        # Process form - simplified version
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        image = request.POST.get('image')
        is_available = request.POST.get('is_available') == 'on'

        # Get category instance
        category = None
        if category_id:
            try:
                category = FoodCategory.objects.get(pk=category_id)
            except FoodCategory.DoesNotExist:
                pass

        MenuItem.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            base_price=price,
            category=category,
            image=image,
            is_available=is_available
        )

        messages.success(request, 'Menu item added successfully!')
        return redirect('food_pwa:manage_menu')

    # Get all active categories
    categories = FoodCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'restaurant': restaurant,
        'categories': categories,
    }
    return render(request, 'food/pwa/owner/add_menu_item.html', context)


@pwa_login_required(pwa_app='food')
def pwa_edit_menu_item(request, item_id):
    """Edit menu item"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    menu_item = get_object_or_404(MenuItem, pk=item_id, restaurant=restaurant)

    if request.method == 'POST':
        menu_item.name = request.POST.get('name')
        menu_item.description = request.POST.get('description')
        menu_item.base_price = request.POST.get('price')

        # Handle category
        category_id = request.POST.get('category')
        if category_id:
            try:
                menu_item.category = FoodCategory.objects.get(pk=category_id)
            except FoodCategory.DoesNotExist:
                menu_item.category = None
        else:
            menu_item.category = None

        # Handle image
        image = request.POST.get('image')
        if image:
            menu_item.image = image

        # Handle availability
        menu_item.is_available = request.POST.get('is_available') == 'on'

        menu_item.save()

        messages.success(request, 'Menu item updated!')
        return redirect('food_pwa:manage_menu')

    # Get all active categories
    categories = FoodCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'restaurant': restaurant,
        'menu_item': menu_item,
        'categories': categories,
    }
    return render(request, 'food/pwa/owner/edit_menu_item.html', context)


@pwa_login_required(pwa_app='food')
def pwa_toggle_menu_item(request, item_id):
    """Toggle menu item availability"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    menu_item = get_object_or_404(MenuItem, pk=item_id, restaurant=restaurant)

    menu_item.is_available = not menu_item.is_available
    menu_item.save()

    status = 'available' if menu_item.is_available else 'unavailable'
    messages.success(request, f'{menu_item.name} is now {status}!')

    return redirect('food_pwa:manage_menu')


@pwa_login_required(pwa_app='food')
def pwa_delete_menu_item(request, item_id):
    """Delete menu item"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')

    menu_item = get_object_or_404(MenuItem, pk=item_id, restaurant=restaurant)

    if request.method == 'POST':
        menu_item_name = menu_item.name
        menu_item.delete()
        messages.success(request, f'{menu_item_name} deleted successfully!')
        return redirect('food_pwa:manage_menu')

    return redirect('food_pwa:manage_menu')


@pwa_login_required(pwa_app='food')
def pwa_analytics(request):
    """Restaurant analytics dashboard"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')


    # Calculate analytics
    last_7_days = timezone.now() - timedelta(days=7)
    last_30_days = timezone.now() - timedelta(days=30)

    context = {
        'restaurant': restaurant,
        'total_revenue': Order.objects.filter(
            restaurant=restaurant, status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_orders': Order.objects.filter(restaurant=restaurant).count(),
        'avg_order_value': Order.objects.filter(
            restaurant=restaurant, status='delivered'
        ).aggregate(avg=Avg('total_amount'))['avg'] or 0,
        'popular_items': MenuItem.objects.filter(
            restaurant=restaurant
        ).annotate(order_count=Count('orderitem')).order_by('-order_count')[:5],
    }
    return render(request, 'food/pwa/owner/analytics.html', context)


@pwa_login_required(pwa_app='food')
def pwa_restaurant_settings(request):
    """Restaurant settings"""
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return redirect('food_pwa:dashboard')


    if request.method == 'POST':
        # Update restaurant settings
        restaurant.phone = request.POST.get('phone')
        restaurant.email = request.POST.get('email')
        restaurant.address = request.POST.get('address')
        restaurant.delivery_time = request.POST.get('delivery_time')
        restaurant.minimum_order_amount = request.POST.get('minimum_order_amount')
        restaurant.save()

        messages.success(request, 'Settings updated successfully!')
        return redirect('food_pwa:restaurant_settings')

    context = {
        'restaurant': restaurant,
    }
    return render(request, 'food/pwa/owner/settings.html', context)


@pwa_login_required(pwa_app='food')
def pwa_notifications(request):
    """View notifications - placeholder, redirects to dashboard"""
    messages.info(request, 'Notifications feature coming soon!')
    return redirect('food_pwa:dashboard')


@pwa_login_required(pwa_app='food')
def pwa_mark_notification_read(request, notification_id):
    """Mark notification as read - placeholder"""
    return redirect('food_pwa:dashboard')
