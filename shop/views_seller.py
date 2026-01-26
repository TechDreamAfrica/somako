"""
CRUD views for Sellers to manage Shops and Products
Similar to restaurant owner functionality in food app
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product, ProductImage, Shop
from .forms import ProductForm, ProductImageForm, ShopForm


def get_user_subscription(user):
    """Get user's active subscription or None"""
    try:
        subscription = user.subscription
        if subscription.is_active():
            return subscription
    except:
        pass
    return None


def can_create_shop(user):
    """
    Check if user can create a new shop based on subscription.
    Returns (can_create, message, subscription)
    """
    subscription = get_user_subscription(user)
    
    if not subscription:
        # Allow creating one shop without subscription for now
        current_count = Shop.objects.filter(owner=user).count()
        if current_count >= 1:
            return False, "You need an active subscription to create more shops. Please subscribe to a plan first.", None
        return True, None, None
    
    # Get current shop count for this user
    current_count = Shop.objects.filter(owner=user).count()
    max_allowed = subscription.plan.max_listings
    
    # -1 means unlimited
    if max_allowed == -1:
        return True, None, subscription
    
    if current_count >= max_allowed:
        return False, f"You have reached the maximum number of shops ({max_allowed}) allowed on your {subscription.plan.display_name} plan. Please upgrade to add more shops.", subscription
    
    return True, None, subscription


# ============================================
# Seller Dashboard
# ============================================

@login_required
def seller_dashboard(request):
    """Main dashboard for sellers"""
    user = request.user
    shops = Shop.objects.filter(owner=user)
    products = Product.objects.filter(Q(shop__owner=user) | Q(created_by=user)).distinct()
    
    context = {
        'shops': shops,
        'total_shops': shops.count(),
        'active_shops': shops.filter(status='active').count(),
        'products': products.order_by('-created_at')[:10],
        'total_products': products.count(),
        'active_products': products.filter(is_active=True).count(),
        'subscription': get_user_subscription(user),
    }
    return render(request, 'shop/seller/dashboard.html', context)


# ============================================
# Shop CRUD Operations
# ============================================

@login_required
def shop_list(request):
    """List all shops owned by the logged-in seller"""
    shops = Shop.objects.filter(owner=request.user).order_by('-created_at')
    subscription = get_user_subscription(request.user)
    
    # Calculate remaining slots
    max_allowed = 1  # Default without subscription
    remaining_slots = 0
    if subscription and subscription.plan:
        max_allowed = subscription.plan.max_listings
        if max_allowed == -1:
            remaining_slots = -1  # Unlimited
        else:
            remaining_slots = max(0, max_allowed - shops.count())
    else:
        remaining_slots = max(0, 1 - shops.count())
    
    context = {
        'shops': shops,
        'total_shops': shops.count(),
        'active_shops': shops.filter(status='active').count(),
        'subscription': subscription,
        'max_allowed': max_allowed,
        'remaining_slots': remaining_slots,
    }
    return render(request, 'shop/seller/shop_list.html', context)


@login_required
def shop_create(request):
    """Create a new shop"""
    # Check subscription limits
    can_create, error_message, subscription = can_create_shop(request.user)
    
    if not can_create:
        messages.error(request, error_message)
        if not subscription:
            return redirect('accounts:subscription_plans')
        return redirect('shop:seller_shop_list')
    
    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.owner = request.user
            shop.save()
            
            messages.success(request, f'Shop "{shop.name}" created successfully!')
            return redirect('shop:seller_shop_detail', pk=shop.pk)
    else:
        form = ShopForm()
    
    return render(request, 'shop/seller/shop_form.html', {
        'form': form,
        'action': 'Create',
        'subscription': subscription,
    })


@login_required
def shop_detail(request, pk):
    """View shop details with its products"""
    shop = get_object_or_404(Shop, pk=pk, owner=request.user)
    products = shop.products.all().order_by('-created_at')
    
    context = {
        'shop': shop,
        'products': products,
        'total_products': products.count(),
        'active_products': products.filter(is_active=True).count(),
    }
    return render(request, 'shop/seller/shop_detail.html', context)


@login_required
def shop_update(request, pk):
    """Update an existing shop"""
    shop = get_object_or_404(Shop, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, f'Shop "{shop.name}" updated successfully!')
            return redirect('shop:seller_shop_detail', pk=shop.pk)
    else:
        form = ShopForm(instance=shop)
    
    return render(request, 'shop/seller/shop_form.html', {
        'form': form,
        'shop': shop,
        'action': 'Update',
    })


@login_required
def shop_delete(request, pk):
    """Delete a shop"""
    shop = get_object_or_404(Shop, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        shop_name = shop.name
        shop.delete()
        messages.success(request, f'Shop "{shop_name}" deleted successfully!')
        return redirect('shop:seller_shop_list')
    
    return render(request, 'shop/seller/shop_confirm_delete.html', {'shop': shop})


@login_required
def shop_toggle_status(request, pk):
    """Toggle shop active/inactive status"""
    shop = get_object_or_404(Shop, pk=pk, owner=request.user)
    
    if shop.status == 'active':
        shop.status = 'inactive'
    else:
        shop.status = 'active'
    shop.save()
    
    messages.success(request, f'Shop status changed to {shop.get_status_display()}!')
    return redirect('shop:seller_shop_detail', pk=shop.pk)


# ============================================
# Product CRUD Operations
# ============================================

@login_required
def product_list(request):
    """List all products owned by the logged-in seller"""
    user_shops = Shop.objects.filter(owner=request.user)
    products = Product.objects.filter(
        Q(shop__in=user_shops) | Q(created_by=request.user)
    ).distinct().order_by('-created_at')
    
    context = {
        'products': products,
        'total_products': products.count(),
        'active_products': products.filter(is_active=True).count(),
        'shops': user_shops,
    }
    return render(request, 'shop/seller/product_list.html', context)


@login_required
def product_create(request, shop_pk=None):
    """Create a new product"""
    user_shops = Shop.objects.filter(owner=request.user)
    
    if not user_shops.exists():
        messages.warning(request, 'You need to create a shop first before adding products.')
        return redirect('shop:seller_shop_create')
    
    # Pre-select shop if provided
    initial = {}
    if shop_pk:
        shop = get_object_or_404(Shop, pk=shop_pk, owner=request.user)
        initial['shop'] = shop
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('shop:seller_product_detail', pk=product.pk)
    else:
        form = ProductForm(user=request.user, initial=initial)
    
    return render(request, 'shop/seller/product_form.html', {
        'form': form,
        'action': 'Create',
        'shops': user_shops,
    })


@login_required
def product_detail(request, pk):
    """View product details"""
    user_shops = Shop.objects.filter(owner=request.user)
    product = get_object_or_404(
        Product,
        Q(pk=pk) & (Q(shop__in=user_shops) | Q(created_by=request.user))
    )
    images = product.images.all()
    
    return render(request, 'shop/seller/product_detail.html', {
        'product': product,
        'images': images,
    })


@login_required
def product_update(request, pk):
    """Update an existing product"""
    user_shops = Shop.objects.filter(owner=request.user)
    product = get_object_or_404(
        Product,
        Q(pk=pk) & (Q(shop__in=user_shops) | Q(created_by=request.user))
    )
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('shop:seller_product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product, user=request.user)
    
    return render(request, 'shop/seller/product_form.html', {
        'form': form,
        'product': product,
        'action': 'Update',
    })


@login_required
def product_delete(request, pk):
    """Delete a product"""
    user_shops = Shop.objects.filter(owner=request.user)
    product = get_object_or_404(
        Product,
        Q(pk=pk) & (Q(shop__in=user_shops) | Q(created_by=request.user))
    )
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('shop:seller_product_list')
    
    return render(request, 'shop/seller/product_confirm_delete.html', {'product': product})


@login_required
def product_toggle_active(request, pk):
    """Toggle product active status"""
    user_shops = Shop.objects.filter(owner=request.user)
    product = get_object_or_404(
        Product,
        Q(pk=pk) & (Q(shop__in=user_shops) | Q(created_by=request.user))
    )
    
    product.is_active = not product.is_active
    product.save()
    
    status = 'active' if product.is_active else 'inactive'
    messages.success(request, f'Product marked as {status}!')
    return redirect('shop:seller_product_detail', pk=product.pk)


# ============================================
# Product Image Management
# ============================================

@login_required
def product_image_add(request, product_pk):
    """Add images to a product"""
    user_shops = Shop.objects.filter(owner=request.user)
    product = get_object_or_404(
        Product,
        Q(pk=product_pk) & (Q(shop__in=user_shops) | Q(created_by=request.user))
    )
    
    if request.method == 'POST':
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.product = product
            image.save()
            messages.success(request, 'Image added successfully!')
            return redirect('shop:seller_product_detail', pk=product.pk)
    else:
        form = ProductImageForm()
    
    return render(request, 'shop/seller/product_image_form.html', {
        'form': form,
        'product': product,
    })


@login_required
def product_image_delete(request, pk):
    """Delete a product image"""
    user_shops = Shop.objects.filter(owner=request.user)
    image = get_object_or_404(
        ProductImage,
        Q(pk=pk) & (Q(product__shop__in=user_shops) | Q(product__created_by=request.user))
    )
    product_pk = image.product.pk
    
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully!')
        return redirect('shop:seller_product_detail', pk=product_pk)
    
    return render(request, 'shop/seller/product_image_confirm_delete.html', {
        'image': image,
        'product': image.product,
    })
