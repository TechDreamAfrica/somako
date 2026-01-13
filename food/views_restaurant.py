"""
Restaurant Owner Views for Food App
Handles restaurant management, menu management, and order management for restaurant owners
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    Restaurant,
    MenuItem,
    FoodCategory,
    Order,
    OrderItem,
    Review
)


# ========================
# Restaurant Dashboard
# ========================

@login_required
def restaurant_dashboard(request):
    """
    Main dashboard for restaurant owners showing comprehensive metrics and recent orders
    """
    # Get restaurants owned by current user
    restaurants = Restaurant.objects.filter(owner=request.user)

    if not restaurants.exists():
        messages.info(request, 'You don\'t have any restaurants yet. Create one to get started!')
        return redirect('food:create_restaurant')

    # Get the active restaurant (first one or selected)
    restaurant_id = request.GET.get('restaurant_id')
    if restaurant_id:
        restaurant = get_object_or_404(restaurants, id=restaurant_id)
    else:
        restaurant = restaurants.first()

    # Date ranges
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # Week and month dates
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))
    
    month_start = today.replace(day=1)
    month_start_dt = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))
    
    # Last 30 days for trends
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # ============================================
    # ORDER STATISTICS
    # ============================================
    
    # All orders for this restaurant
    all_orders = Order.objects.filter(restaurant=restaurant)
    total_orders = all_orders.count()
    
    # Today's orders
    today_orders = all_orders.filter(
        created_at__range=(today_start, today_end)
    ).count()
    
    # Orders by status
    pending_orders = all_orders.filter(status='pending').count()
    confirmed_orders = all_orders.filter(status='confirmed').count()
    preparing_orders = all_orders.filter(status='preparing').count()
    ready_orders = all_orders.filter(status='ready').count()
    delivered_orders = all_orders.filter(status='delivered').count()
    
    # Active orders needing attention
    active_orders = pending_orders + confirmed_orders + preparing_orders
    
    # Completed today
    completed_today = all_orders.filter(
        created_at__range=(today_start, today_end),
        status='delivered'
    ).count()

    # ============================================
    # REVENUE STATISTICS
    # ============================================
    
    # Today's revenue
    today_revenue = all_orders.filter(
        created_at__range=(today_start, today_end),
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # This week's revenue
    week_revenue = all_orders.filter(
        created_at__gte=week_start_dt,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # This month's revenue
    month_revenue = all_orders.filter(
        created_at__gte=month_start_dt,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Total revenue (all time)
    total_revenue = all_orders.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Last 30 days revenue (for trends)
    revenue_last_30_days = all_orders.filter(
        created_at__gte=thirty_days_ago,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Average order value
    avg_order_value = all_orders.filter(
        payment_status='paid'
    ).aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0.00')

    # ============================================
    # POPULAR MENU ITEMS
    # ============================================
    
    # Popular items (last 30 days)
    popular_items = OrderItem.objects.filter(
        order__restaurant=restaurant,
        order__created_at__gte=thirty_days_ago
    ).values(
        'menu_item__name',
        'menu_item__id'
    ).annotate(
        total_orders=Count('id'),
        total_quantity=Sum('quantity'),
        revenue=Sum(F('quantity') * F('price'))
    ).order_by('-total_quantity')[:5]
    
    # Popular items today
    popular_items_today = OrderItem.objects.filter(
        order__restaurant=restaurant,
        order__created_at__range=(today_start, today_end)
    ).values(
        'menu_item__name'
    ).annotate(
        quantity_sold=Sum('quantity')
    ).order_by('-quantity_sold')[:5]

    # ============================================
    # MENU ITEMS STATISTICS
    # ============================================
    
    all_menu_items = MenuItem.objects.filter(restaurant=restaurant)
    menu_items_count = all_menu_items.count()
    available_items = all_menu_items.filter(is_available=True).count()
    unavailable_items = menu_items_count - available_items

    # ============================================
    # REVIEWS
    # ============================================
    
    recent_reviews = Review.objects.filter(
        restaurant=restaurant,
        is_approved=True
    ).select_related('customer', 'order').order_by('-created_at')[:5]

    # ============================================
    # RECENT ORDERS
    # ============================================
    
    latest_orders = all_orders.select_related(
        'customer'
    ).prefetch_related('items__menu_item').order_by('-created_at')[:10]
    
    # Recent orders (last 30 days) for detailed view
    recent_orders = all_orders.filter(
        created_at__gte=thirty_days_ago
    ).select_related('customer').prefetch_related('items')

    # ============================================
    # CONTEXT
    # ============================================
    
    context = {
        'restaurant': restaurant,
        'restaurants': restaurants,
        
        # Order counts
        'total_orders': total_orders,
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'delivered_orders': delivered_orders,
        'active_orders': active_orders,
        'completed_today': completed_today,
        
        # Revenue
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'total_revenue': total_revenue,
        'revenue_last_30_days': revenue_last_30_days,
        'avg_order_value': avg_order_value,
        
        # Menu items
        'menu_items_count': menu_items_count,
        'available_items': available_items,
        'unavailable_items': unavailable_items,
        
        # Popular items
        'popular_items': popular_items,
        'popular_items_today': popular_items_today,
        
        # Reviews
        'recent_reviews': recent_reviews,
        'average_rating': restaurant.average_rating,
        'total_reviews': restaurant.total_reviews,
        
        # Orders
        'latest_orders': latest_orders,
        'recent_orders': recent_orders,
        
        # Dates
        'today': today,
        'week_start': week_start,
        'month_start': month_start,
    }

    return render(request, 'food/restaurant/dashboard.html', context)


# ========================
# Order Management
# ========================

@login_required
def manage_orders(request):
    """
    View and manage restaurant orders
    """
    restaurants = Restaurant.objects.filter(owner=request.user)

    if not restaurants.exists():
        messages.error(request, 'No restaurants found.')
        return redirect('food:dashboard')

    restaurant_id = request.GET.get('restaurant_id')
    if restaurant_id:
        restaurant = get_object_or_404(restaurants, id=restaurant_id)
    else:
        restaurant = restaurants.first()

    # Get orders
    orders = Order.objects.filter(restaurant=restaurant).select_related(
        'customer', 'driver', 'delivery_zone'
    ).prefetch_related('items__menu_item')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        try:
            date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass

    # Search by order number or customer name
    search = request.GET.get('search', '').strip()
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__email__icontains=search)
        )

    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = ['-created_at', 'created_at', '-total_amount', 'total_amount']
    if sort_by in valid_sorts:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-created_at')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(orders, 15)
    orders_page = paginator.get_page(page)

    context = {
        'restaurant': restaurant,
        'restaurants': restaurants,
        'orders': orders_page,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'sort_by': sort_by,
        'status_choices': Order.STATUS_CHOICES,
    }

    return render(request, 'food/restaurant/manage_orders.html', context)


@login_required
@require_POST
def update_order_status(request, order_id):
    """
    Update order status (restaurant owner only)
    """
    order = get_object_or_404(
        Order.objects.select_related('restaurant', 'customer'),
        id=order_id,
        restaurant__owner=request.user
    )

    new_status = request.POST.get('status')

    # Validate status transition
    valid_statuses = dict(Order.STATUS_CHOICES).keys()
    if new_status not in valid_statuses:
        messages.error(request, 'Invalid status.')
        return redirect('food:manage_orders')

    # Update status
    order.status
    order.status = new_status

    # Update timestamps based on status
    if new_status == 'confirmed' and not order.confirmed_at:
        order.confirmed_at = timezone.now()
    elif new_status == 'cancelled' and not order.cancelled_at:
        order.cancelled_at = timezone.now()
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        if cancellation_reason:
            order.cancellation_reason = cancellation_reason
    elif new_status == 'delivered' and not order.actual_delivery_time:
        order.actual_delivery_time = timezone.now()

    order.save()

    # Send SMS notification to customer for all status changes
    try:
        from utils.sms_utils import send_customer_order_status_update
        sms_result = send_customer_order_status_update(order, new_status)
        if sms_result.get('success'):
            messages.success(
                request,
                f'Order #{order.order_number} status updated to "{new_status}". SMS sent to customer.'
            )
        else:
            messages.success(
                request,
                f'Order #{order.order_number} status updated to "{new_status}". SMS failed: {sms_result.get("message")}'
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send SMS notification: {str(e)}")
        messages.success(
            request,
            f'Order #{order.order_number} status updated to "{new_status}". SMS notification failed.'
        )

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Status updated successfully',
            'new_status': new_status
        })

    return redirect('food:manage_orders')


# ========================
# Menu Management
# ========================

@login_required
def manage_menu(request):
    """
    View and manage restaurant menu items
    """
    restaurants = Restaurant.objects.filter(owner=request.user)

    if not restaurants.exists():
        messages.error(request, 'No restaurants found.')
        return redirect('food:dashboard')

    restaurant_id = request.GET.get('restaurant_id')
    if restaurant_id:
        restaurant = get_object_or_404(restaurants, id=restaurant_id)
    else:
        restaurant = restaurants.first()

    # Get menu items
    menu_items = MenuItem.objects.filter(restaurant=restaurant).select_related('category')

    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        menu_items = menu_items.filter(category_id=category_id)

    # Filter by availability
    availability = request.GET.get('availability', '')
    if availability == 'available':
        menu_items = menu_items.filter(is_available=True)
    elif availability == 'unavailable':
        menu_items = menu_items.filter(is_available=False)

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        menu_items = menu_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # Sort
    sort_by = request.GET.get('sort', 'name')
    valid_sorts = ['name', '-name', 'price', '-price', '-average_rating', '-created_at']
    if sort_by in valid_sorts:
        menu_items = menu_items.order_by(sort_by)
    else:
        menu_items = menu_items.order_by('name')

    # Get categories for filter
    categories = FoodCategory.objects.filter(is_active=True)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(menu_items, 20)
    menu_page = paginator.get_page(page)

    context = {
        'restaurant': restaurant,
        'restaurants': restaurants,
        'menu_items': menu_page,
        'categories': categories,
        'category_id': category_id,
        'availability': availability,
        'search': search,
        'sort_by': sort_by,
    }

    return render(request, 'food/restaurant/manage_menu.html', context)


@login_required
@require_POST
def toggle_menu_item_availability(request, item_id):
    """
    Toggle menu item availability
    """
    menu_item = get_object_or_404(
        MenuItem.objects.select_related('restaurant'),
        id=item_id,
        restaurant__owner=request.user
    )

    menu_item.is_available = not menu_item.is_available
    menu_item.save()

    status_text = 'available' if menu_item.is_available else 'unavailable'
    messages.success(request, f'{menu_item.name} is now {status_text}.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_available': menu_item.is_available
        })

    return redirect('food:manage_menu')


# ========================
# Analytics & Reports
# ========================

@login_required
def restaurant_analytics(request):
    """
    Detailed analytics and reports for restaurant owners
    """
    restaurants = Restaurant.objects.filter(owner=request.user)

    if not restaurants.exists():
        messages.error(request, 'No restaurants found.')
        return redirect('food:dashboard')

    restaurant_id = request.GET.get('restaurant_id')
    if restaurant_id:
        restaurant = get_object_or_404(restaurants, id=restaurant_id)
    else:
        restaurant = restaurants.first()

    # Date range selection
    period = request.GET.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get orders in period
    orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__gte=start_date
    )

    # Revenue analytics
    revenue_by_status = orders.values('payment_status').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    # Orders by status
    orders_by_status = orders.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Daily revenue (for chart)
    daily_revenue = orders.filter(
        payment_status='paid'
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    ).order_by('day')

    # Top selling items
    top_items = OrderItem.objects.filter(
        order__restaurant=restaurant,
        order__created_at__gte=start_date
    ).values(
        'menu_item__name',
        'menu_item__id'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-quantity_sold')[:10]

    # Customer analytics
    total_customers = orders.values('customer').distinct().count()
    repeat_customers = orders.values('customer').annotate(
        order_count=Count('id')
    ).filter(order_count__gt=1).count()

    # Average order value
    avg_order_value = orders.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0.00')

    # Review stats
    recent_reviews = Review.objects.filter(
        restaurant=restaurant,
        created_at__gte=start_date
    )

    avg_ratings = recent_reviews.aggregate(
        overall=Avg('rating'),
        food_quality=Avg('food_quality_rating'),
        delivery=Avg('delivery_rating'),
        service=Avg('service_rating')
    )

    context = {
        'restaurant': restaurant,
        'restaurants': restaurants,
        'period': days,
        'start_date': start_date,
        'end_date': end_date,
        'revenue_by_status': revenue_by_status,
        'orders_by_status': orders_by_status,
        'daily_revenue': daily_revenue,
        'top_items': top_items,
        'total_customers': total_customers,
        'repeat_customers': repeat_customers,
        'avg_order_value': avg_order_value,
        'avg_ratings': avg_ratings,
        'total_reviews': recent_reviews.count(),
    }

    return render(request, 'food/restaurant/analytics.html', context)
