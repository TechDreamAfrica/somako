"""
CRUD views for Restaurant Owners to manage Restaurants and Menu Items
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Restaurant, MenuItem
from .forms import RestaurantForm, MenuItemForm


def get_user_subscription(user):
    """Get user's active subscription or None"""
    try:
        subscription = user.subscription
        if subscription.is_active():
            return subscription
    except:
        pass
    return None


def can_create_restaurant(user):
    """
    Check if user can create a new restaurant based on subscription.
    Returns (can_create, message, subscription)
    """
    subscription = get_user_subscription(user)
    
    if not subscription:
        return False, "You need an active subscription to create a restaurant. Please subscribe to a plan first.", None
    
    # Get current restaurant count for this user
    current_count = Restaurant.objects.filter(owner=user).count()
    max_allowed = subscription.plan.max_listings
    
    # -1 means unlimited
    if max_allowed == -1:
        return True, None, subscription
    
    if current_count >= max_allowed:
        return False, f"You have reached the maximum number of restaurants ({max_allowed}) allowed on your {subscription.plan.display_name} plan. Please upgrade to add more restaurants.", subscription
    
    return True, None, subscription


# ============================================
# Restaurant CRUD Operations
# ============================================

@login_required
def restaurant_list(request):
    """List all restaurants owned by the logged-in restaurant owner"""
    restaurants = Restaurant.objects.filter(owner=request.user).order_by('-created_at')
    subscription = get_user_subscription(request.user)
    
    # Calculate remaining slots
    max_allowed = 0
    remaining_slots = 0
    if subscription and subscription.plan:
        max_allowed = subscription.plan.max_listings
        if max_allowed == -1:
            remaining_slots = -1  # Unlimited
        else:
            remaining_slots = max(0, max_allowed - restaurants.count())
    
    context = {
        'restaurants': restaurants,
        'total_restaurants': restaurants.count(),
        'active_restaurants': restaurants.filter(status='active').count(),
        'subscription': subscription,
        'max_allowed': max_allowed,
        'remaining_slots': remaining_slots,
    }
    return render(request, 'food/owner/restaurant_list.html', context)


@login_required
def restaurant_create(request):
    """Create a new restaurant"""
    # Check subscription limits
    can_create, error_message, subscription = can_create_restaurant(request.user)
    
    if not can_create:
        messages.error(request, error_message)
        if not subscription:
            return redirect('accounts:subscription_plans')
        return redirect('food:owner_restaurant_list')
    
    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES)
        if form.is_valid():
            restaurant = form.save(commit=False)
            restaurant.owner = request.user
            restaurant.save()
            
            # Update subscription listing count
            if subscription:
                subscription.current_listings_count = Restaurant.objects.filter(owner=request.user).count()
                subscription.save()
            
            messages.success(request, 'Restaurant created successfully!')
            return redirect('food:owner_restaurant_detail', pk=restaurant.pk)
    else:
        form = RestaurantForm()

    context = {
        'form': form, 
        'action': 'Create',
        'subscription': subscription,
    }
    return render(request, 'food/owner/restaurant_form.html', context)


@login_required
def restaurant_detail(request, pk):
    """View restaurant details with menu items"""
    restaurant = get_object_or_404(Restaurant, pk=pk, owner=request.user)
    menu_items = restaurant.menu_items.all()

    context = {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'total_items': menu_items.count(),
        'available_items': menu_items.filter(is_available=True).count(),
    }
    return render(request, 'food/owner/restaurant_detail.html', context)


@login_required
def restaurant_update(request, pk):
    """Update an existing restaurant"""
    restaurant = get_object_or_404(Restaurant, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Restaurant updated successfully!')
            return redirect('food:owner_restaurant_detail', pk=restaurant.pk)
    else:
        form = RestaurantForm(instance=restaurant)

    context = {'form': form, 'restaurant': restaurant, 'action': 'Update'}
    return render(request, 'food/owner/restaurant_form.html', context)


@login_required
def restaurant_delete(request, pk):
    """Delete a restaurant"""
    restaurant = get_object_or_404(Restaurant, pk=pk, owner=request.user)

    if request.method == 'POST':
        restaurant_name = restaurant.name
        restaurant.delete()
        messages.success(request, f'Restaurant "{restaurant_name}" deleted successfully!')
        return redirect('food:owner_restaurant_list')

    context = {'restaurant': restaurant}
    return render(request, 'food/owner/restaurant_confirm_delete.html', context)


@login_required
def restaurant_toggle_status(request, pk):
    """Toggle restaurant status (active/inactive)"""
    restaurant = get_object_or_404(Restaurant, pk=pk, owner=request.user)

    if restaurant.status == 'active':
        restaurant.status = 'inactive'
    else:
        restaurant.status = 'active'

    restaurant.save()
    messages.success(request, f'Restaurant status changed to {restaurant.status}!')
    return redirect('food:owner_restaurant_detail', pk=restaurant.pk)


# ============================================
# MenuItem CRUD Operations
# ============================================

@login_required
def menu_item_create(request, restaurant_pk):
    """Create a new menu item for a restaurant"""
    restaurant = get_object_or_404(Restaurant, pk=restaurant_pk, owner=request.user)

    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.restaurant = restaurant
            menu_item.save()
            messages.success(request, f'Menu item "{menu_item.name}" created successfully!')
            return redirect('food:owner_restaurant_detail', pk=restaurant.pk)
    else:
        form = MenuItemForm()

    context = {
        'form': form,
        'restaurant': restaurant,
        'action': 'Create',
    }
    return render(request, 'food/owner/menu_item_form.html', context)


@login_required
def menu_item_update(request, pk):
    """Update an existing menu item"""
    menu_item = get_object_or_404(MenuItem, pk=pk, restaurant__owner=request.user)

    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Menu item "{menu_item.name}" updated successfully!')
            return redirect('food:owner_restaurant_detail', pk=menu_item.restaurant.pk)
    else:
        form = MenuItemForm(instance=menu_item)

    context = {
        'form': form,
        'menu_item': menu_item,
        'restaurant': menu_item.restaurant,
        'action': 'Update',
    }
    return render(request, 'food/owner/menu_item_form.html', context)


@login_required
def menu_item_delete(request, pk):
    """Delete a menu item"""
    menu_item = get_object_or_404(MenuItem, pk=pk, restaurant__owner=request.user)
    restaurant_pk = menu_item.restaurant.pk

    if request.method == 'POST':
        menu_item_name = menu_item.name
        menu_item.delete()
        messages.success(request, f'Menu item "{menu_item_name}" deleted successfully!')
        return redirect('food:owner_restaurant_detail', pk=restaurant_pk)

    context = {'menu_item': menu_item, 'restaurant': menu_item.restaurant}
    return render(request, 'food/owner/menu_item_confirm_delete.html', context)


@login_required
def menu_item_toggle_availability(request, pk):
    """Toggle menu item availability"""
    menu_item = get_object_or_404(MenuItem, pk=pk, restaurant__owner=request.user)
    menu_item.is_available = not menu_item.is_available
    menu_item.save()

    status = 'available' if menu_item.is_available else 'unavailable'
    messages.success(request, f'Menu item marked as {status}!')

    return redirect('food:owner_restaurant_detail', pk=menu_item.restaurant.pk)
