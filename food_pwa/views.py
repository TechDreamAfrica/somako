"""
Food PWA Views - Progressive Web App specific views
Optimized for mobile-first experience with touch-friendly interfaces
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q, Prefetch
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from datetime import timedelta, date
from decimal import Decimal
import uuid
import logging

from food.models import (
    Restaurant, MenuItem, Order, OrderItem, Cart, CartItem, 
    FoodCategory, Review, DeliveryZone, OrderItemAddon
)
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
    try:
        # Models already imported at top
        
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
            messages.warning(request, 'Your cart is empty!')
            return redirect('food_pwa:restaurant_list')

        # Check if all items are from the same restaurant
        restaurants = list(set(item.menu_item.restaurant for item in cart_items))
        if len(restaurants) > 1:
            messages.error(
                request,
                'You can only order from one restaurant at a time. '
                'Please remove items from other restaurants.'
            )
            return redirect('food_pwa:cart')

        restaurant = restaurants[0]

        # Get available delivery zones for the restaurant
        delivery_zones = DeliveryZone.objects.filter(
            Q(restaurant=restaurant) | Q(restaurant__isnull=True),
            is_active=True
        )

        # Calculate totals to match main food app
        subtotal = cart.get_total()
        delivery_fee = Decimal('25.00')  # Default door delivery fee to match main app
        total = subtotal + delivery_fee  # No tax to match main app


        context = {
            'cart': cart,
            'cart_items': cart_items,
            'restaurant': restaurant,
            'delivery_zones': delivery_zones,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': total,
            'user': request.user,
            'PAYSTACK_PUBLIC_KEY': getattr(settings, 'PAYSTACK_PUBLIC_KEY', ''),
        }
        return render(request, 'food/pwa/checkout.html', context)

    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty!')
        return redirect('food_pwa:restaurant_list')


@pwa_login_required(pwa_app='food')
def pwa_confirm_order(request):
    """Process order confirmation"""
    if request.method == 'POST':
        try:

            
            # Try to import payment helpers, handle if not available
            try:
                from payment.helpers import create_payment, initialize_paystack_payment
                payment_available = True
            except ImportError:
                payment_available = False
                logger = logging.getLogger(__name__)
                logger.warning("Payment helpers not available - online payments will not work")
            
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
                messages.error(request, 'Your cart is empty!')
                return redirect('food_pwa:restaurant_list')

            # Check if all items are from the same restaurant
            restaurants = list(set(item.menu_item.restaurant for item in cart_items))
            if len(restaurants) > 1:
                messages.error(
                    request,
                    'You can only order from one restaurant at a time. '
                    'Please remove items from other restaurants.'
                )
                return redirect('food_pwa:cart')

            restaurant = restaurants[0]

            # Get form data
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
                return redirect('food_pwa:checkout')

            # Get delivery zone
            delivery_zone = None
            if delivery_zone_id:
                try:
                    delivery_zone = DeliveryZone.objects.get(id=delivery_zone_id, is_active=True)
                except DeliveryZone.DoesNotExist:
                    pass

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
            if restaurant.minimum_order_amount and restaurant.minimum_order_amount > subtotal:
                messages.error(
                    request,
                    f'Minimum order amount is GHS {restaurant.minimum_order_amount}. '
                    f'Please add more items.'
                )
                return redirect('food_pwa:cart')

            # Generate unique order number
            order_number = f'PWA-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'

            # Create order - always create the order first, then handle payment
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
                status='pending',  # Start as pending, update based on payment method
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
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send SMS notification: {str(e)}")

            # Handle payment based on method
            if payment_method == 'online_payment':
                if not payment_available:
                    # Payment system not available - create order anyway
                    order.status = 'confirmed'
                    order.payment_status = 'failed'
                    order.save()
                    
                    messages.warning(
                        request,
                        f'Order created successfully (#{order_number}) but online payment is currently unavailable. Please contact us to complete payment.'
                    )
                    return redirect('food_pwa:order_detail', order_number=order_number)
                
                # Initialize Paystack payment for online payments
                try:
                    payment = create_payment(
                        user=request.user,
                        amount=total_amount,
                        currency='GHS',
                        source_app='food',
                        order_id=order_number,
                        description=f'PWA Food Order {order_number} from {restaurant.name}',
                        payment_method='paystack'
                    )

                    # Initialize Paystack transaction
                    result = initialize_paystack_payment(payment)

                    if result.get('status'):
                        # Update order status to pending payment
                        order.status = 'pending'
                        order.payment_status = 'pending'
                        order.save()
                        
                        # Redirect to Paystack payment page
                        return redirect(result['authorization_url'])
                    else:
                        # Payment initialization failed - still create order but mark payment as failed
                        order.payment_status = 'failed'
                        order.status = 'confirmed'
                        order.save()
                        
                        messages.error(request, f"Payment initialization failed. Order created but please contact us to complete payment.")
                        return redirect('food_pwa:order_detail', order_number=order_number)
                        
                except Exception as e:
                    # Log the error but still create the order
                    logger = logging.getLogger(__name__)
                    logger.error(f"Payment initialization error for PWA order {order_number}: {str(e)}", exc_info=True)

                    # Mark payment as failed but order as confirmed
                    order.payment_status = 'failed' 
                    order.status = 'confirmed'
                    order.save()

                    messages.warning(
                        request,
                        f"Order created successfully (#{order_number}) but payment setup failed. Please contact us to complete payment."
                    )
                    return redirect('food_pwa:order_detail', order_number=order_number)
            else:
                # Cash on delivery or other payment methods - confirm order immediately
                order.status = 'confirmed'
                order.payment_status = 'pending' if payment_method == 'cash_on_delivery' else 'completed'
                order.save()
                
                success_message = f'Order placed successfully! Your order number is {order_number}.'
                if payment_method == 'cash_on_delivery':
                    success_message += f' Please pay GHS {total_amount} when you receive your order.'
                    
                messages.success(request, success_message)
                return redirect('food_pwa:order_detail', order_number=order_number)

        except Cart.DoesNotExist:
            messages.warning(request, 'Your cart is empty!')
            return redirect('food_pwa:restaurant_list')
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing PWA order: {str(e)}", exc_info=True)
            
            # More specific error messages based on the exception
            error_msg = str(e)
            if "DeliveryZone" in error_msg:
                messages.error(request, 'Please select a valid delivery zone.')
            elif "minimum_order_amount" in error_msg:
                messages.error(request, 'Your order does not meet the minimum order requirement.')
            elif "payment" in error_msg.lower():
                messages.error(request, 'There was an issue with payment processing. Your order may still have been created.')
            elif "Cart.DoesNotExist" in error_msg:
                messages.error(request, 'Your cart is empty. Please add items before checking out.')
            elif "ValidationError" in error_msg:
                messages.error(request, 'Please check all required fields and try again.')
            else:
                messages.error(request, f'An error occurred while processing your order: {error_msg}. Please contact support if this persists.')
            
            return redirect('food_pwa:checkout')

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
            image=image if image else None,  # Use image field for both files and URLs
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
