"""
Pharmacy PWA Views - Progressive Web App specific views
Optimized for mobile-first experience with touch-friendly interfaces
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg, Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import date
from decimal import Decimal

from pharmacy.models import Medicine, Cart, CartItem, Order, OrderItem, Prescription, MedicineCategory, Pharmacy


# ============================================
# CUSTOMER VIEWS
# ============================================

@login_required
def pwa_dashboard(request):
    """PWA Pharmacy Dashboard - Role-based (Customer/Owner)"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'pharmacy'

    user = request.user
    # Check if user has pharmacy_owner role
    is_pharmacy_owner = user.has_role('pharmacy_owner') and hasattr(user, 'pharmacy_profile')

    if is_pharmacy_owner:
        return redirect('pharmacy_pwa:owner_dashboard')

    # Customer dashboard
    context = {
        'featured_medicines': Medicine.objects.filter(
            is_active=True, is_featured=True
        ).order_by('-created_at')[:6],
        'recent_medicines': Medicine.objects.filter(
            is_active=True
        ).order_by('-created_at')[:8],
        'recent_orders': Order.objects.filter(
            user=user
        ).order_by('-created_at')[:3],
        'cart_count': CartItem.objects.filter(cart__user=user).count(),
        'pending_prescriptions': Prescription.objects.filter(user=user, status='pending').count(),
    }
    return render(request, 'pharmacy/pwa/dashboard.html', context)


@login_required
def pwa_pharmacy_list(request):
    """Browse all pharmacies - PWA version"""
    pharmacies = Pharmacy.objects.filter(status='active').select_related('owner')

    # Search functionality
    search_query = request.GET.get('q', '').strip()
    if search_query:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # Filter by city
    city = request.GET.get('city', '').strip()
    if city:
        pharmacies = pharmacies.filter(city__iexact=city)

    # Sorting
    sort = request.GET.get('sort', 'featured')
    if sort == 'rating':
        pharmacies = pharmacies.order_by('-average_rating')
    elif sort == 'name':
        pharmacies = pharmacies.order_by('name')
    elif sort == 'newest':
        pharmacies = pharmacies.order_by('-created_at')
    else:  # featured
        pharmacies = pharmacies.order_by('-is_featured', '-average_rating')

    # Get all cities for filter
    cities = Pharmacy.objects.filter(status='active').values_list('city', flat=True).distinct().order_by('city')

    context = {
        'pharmacies': pharmacies,
        'cities': cities,
        'selected_city': city,
        'selected_sort': sort,
        'search_query': search_query,
    }
    return render(request, 'pharmacy/pwa/pharmacy_list.html', context)


@login_required
def pwa_pharmacy_detail(request, pk):
    """Pharmacy details page - PWA version"""
    pharmacy = get_object_or_404(
        Pharmacy.objects.select_related('owner').prefetch_related(
            Prefetch(
                'medicines',
                queryset=Medicine.objects.filter(is_active=True).select_related('category')
            )
        ),
        pk=pk,
        status='active'
    )

    # Get medicines for this pharmacy
    medicines = Medicine.objects.filter(
        pharmacy=pharmacy,
        is_active=True
    ).select_related('category').order_by('category__name', '-is_featured', 'name')

    # Get categories for this pharmacy
    categories = MedicineCategory.objects.filter(
        medicines__pharmacy=pharmacy,
        medicines__is_active=True,
        is_active=True
    ).distinct().order_by('name')

    # Filter by category if specified
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        medicines = medicines.filter(category__slug=category_slug)

    # Search in medicines
    search_query = request.GET.get('q', '').strip()
    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(generic_name__icontains=search_query)
        )

    context = {
        'pharmacy': pharmacy,
        'medicines': medicines,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
    }
    return render(request, 'pharmacy/pwa/pharmacy_detail.html', context)


@login_required
def pwa_medicine_list(request):
    """Browse all medicines"""
    medicines = Medicine.objects.filter(is_active=True)

    # Filters
    category = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'newest')

    if category:
        medicines = medicines.filter(category__slug=category)

    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(manufacturer__icontains=search_query)
        )

    # Sorting
    if sort == 'price_low':
        medicines = medicines.order_by('price')
    elif sort == 'price_high':
        medicines = medicines.order_by('-price')
    elif sort == 'name':
        medicines = medicines.order_by('name')
    else:  # newest
        medicines = medicines.order_by('-created_at')

    context = {
        'medicines': medicines,
        'categories': MedicineCategory.objects.filter(is_active=True),
        'selected_category': category,
        'selected_sort': sort,
        'search_query': search_query,
    }
    return render(request, 'pharmacy/pwa/medicine_list.html', context)


@login_required
def pwa_medicine_detail(request, pk):
    """Medicine details page"""
    medicine = get_object_or_404(Medicine, pk=pk, is_active=True)

    context = {
        'medicine': medicine,
    }
    return render(request, 'pharmacy/pwa/medicine_detail.html', context)


@login_required
def pwa_category_medicines(request, category):
    """Medicines filtered by category"""
    medicines = Medicine.objects.filter(category__name__iexact=category, is_active=True).order_by('name')

    context = {
        'category': category,
        'medicines': medicines,
    }
    return render(request, 'pharmacy/pwa/category_medicines.html', context)


@login_required
def pwa_cart_view(request):
    """View shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('medicine')

    # Calculate totals
    subtotal = sum(item.get_total_price() for item in cart_items)
    delivery_fee = Decimal('8.00')  # You can make this dynamic
    total = subtotal + delivery_fee

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'can_checkout': cart_items.exists(),
    }
    return render(request, 'pharmacy/pwa/cart.html', context)


@login_required
def pwa_add_to_cart(request, medicine_id):
    """Add item to cart (AJAX)"""
    if request.method == 'POST':
        medicine = get_object_or_404(Medicine, pk=medicine_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))

        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            medicine=medicine,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f'{medicine.name} added to cart!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': CartItem.objects.filter(cart=cart).count(),
                'message': f'{medicine.name} added to cart!'
            })

        return redirect('pharmacy_pwa:cart')

    return redirect('pharmacy_pwa:medicine_list')


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

    return redirect('pharmacy_pwa:cart')


@login_required
def pwa_remove_from_cart(request, cart_item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('pharmacy_pwa:cart')


@login_required
def pwa_clear_cart(request):
    """Clear entire cart"""
    CartItem.objects.filter(cart__user=request.user).delete()
    messages.success(request, 'Cart cleared!')
    return redirect('pharmacy_pwa:cart')


@login_required
def pwa_checkout(request):
    """Checkout page"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('medicine')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('pharmacy_pwa:medicine_list')

    # Calculate totals
    subtotal = sum(item.get_total_price() for item in cart_items)
    delivery_fee = Decimal('8.00')
    total = subtotal + delivery_fee

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'user': request.user,
    }
    return render(request, 'pharmacy/pwa/checkout.html', context)


@login_required
def pwa_confirm_order(request):
    """Process order confirmation"""
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty!')
            return redirect('pharmacy_pwa:medicine_list')

        # Get delivery details
        delivery_address = request.POST.get('delivery_address')
        phone_number = request.POST.get('phone_number')
        payment_method = request.POST.get('payment_method', 'cash')
        notes = request.POST.get('notes', '')

        # Calculate totals
        subtotal = sum(item.get_total_price() for item in cart_items)
        delivery_fee = Decimal('8.00')
        total = subtotal + delivery_fee

        # Create order
        order = Order.objects.create(
            user=request.user,
            delivery_address=delivery_address,
            delivery_phone=phone_number,
            payment_method=payment_method,
            order_notes=notes,
            subtotal=subtotal,
            delivery_charge=delivery_fee,
            total=total,
            status='pending'
        )

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                medicine=cart_item.medicine,
                quantity=cart_item.quantity,
                price=cart_item.medicine.price
            )

        # Clear cart
        cart_items.delete()

        messages.success(request, f'Order placed successfully! Order #{order.order_number}')
        return redirect('pharmacy_pwa:order_detail', order_number=order.order_number)

    return redirect('pharmacy_pwa:checkout')


@login_required
def pwa_upload_prescription(request):
    """Upload prescription"""
    if request.method == 'POST':
        prescription_file = request.FILES.get('prescription_image')
        notes = request.POST.get('notes', '')

        if prescription_file:
            Prescription.objects.create(
                user=request.user,
                prescription_file=prescription_file,
                patient_notes=notes,
                status='pending'
            )
            messages.success(request, 'Prescription uploaded successfully!')
            return redirect('pharmacy_pwa:dashboard')

    return render(request, 'pharmacy/pwa/upload_prescription.html')


@login_required
def pwa_scan_prescription(request):
    """Scan prescription using camera"""
    import base64
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from datetime import timedelta
    
    if request.method == 'POST':
        patient_name = request.POST.get('patient_name')
        doctor_name = request.POST.get('doctor_name', '')
        notes = request.POST.get('notes', '')
        prescription_image_data = request.POST.get('prescription_image')

        if prescription_image_data and patient_name:
            # Handle base64 image data from camera
            try:
                format, imgstr = prescription_image_data.split(';base64,')
                ext = format.split('/')[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f'prescription_{request.user.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{ext}')
                
                # Build patient notes with all info
                patient_notes_text = f"Patient: {patient_name}"
                if doctor_name:
                    patient_notes_text += f"\nDoctor: {doctor_name}"
                if notes:
                    patient_notes_text += f"\n{notes}"
                
                # Create prescription with proper field names
                Prescription.objects.create(
                    user=request.user,
                    prescription_file=image_file,  # Changed from prescription_image to prescription_file
                    doctor_name=doctor_name if doctor_name else 'Not specified',
                    patient_notes=patient_notes_text,  # Changed from notes to patient_notes
                    issue_date=timezone.now().date(),
                    expiry_date=timezone.now().date() + timedelta(days=90),  # 90 days validity
                    status='pending'
                )
                messages.success(request, 'Prescription submitted successfully! We will review it within 24 hours.')
                return redirect('pharmacy_pwa:dashboard')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error uploading prescription: {str(e)}')
                messages.error(request, f'Error uploading prescription. Please try again or contact support.')

    return render(request, 'pharmacy/pwa/scan_prescription.html')


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
    return render(request, 'pharmacy/pwa/order_list.html', context)


@login_required
def pwa_order_detail(request, order_number):
    """View order details"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    context = {
        'order': order,
        'order_items': order.items.all(),
        'can_cancel': order.status in ['pending', 'confirmed'],
    }
    return render(request, 'pharmacy/pwa/order_detail.html', context)


@login_required
def pwa_track_order(request, order_number):
    """Track order status"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    # Order progress stages
    stages = [
        {'status': 'pending', 'label': 'Order Placed', 'icon': 'fa-check-circle'},
        {'status': 'confirmed', 'label': 'Confirmed', 'icon': 'fa-clipboard-check'},
        {'status': 'processing', 'label': 'Processing', 'icon': 'fa-pills'},
        {'status': 'ready', 'label': 'Ready', 'icon': 'fa-box'},
        {'status': 'out_for_delivery', 'label': 'Out for Delivery', 'icon': 'fa-truck'},
        {'status': 'delivered', 'label': 'Delivered', 'icon': 'fa-home'},
    ]

    context = {
        'order': order,
        'stages': stages,
    }
    return render(request, 'pharmacy/pwa/track_order.html', context)


@login_required
def pwa_cancel_order(request, order_number):
    """Cancel an order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status in ['pending', 'confirmed']:
        order.status = 'cancelled'
        order.save()
        messages.success(request, 'Order cancelled successfully!')
    else:
        messages.error(request, 'This order cannot be cancelled.')

    return redirect('pharmacy_pwa:order_detail', order_number=order_number)


@login_required
def pwa_search(request):
    """Search medicines"""
    query = request.GET.get('q', '')

    medicines = []
    if query:
        medicines = Medicine.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(manufacturer__icontains=query),
            is_active=True
        )[:20]

    context = {
        'query': query,
        'medicines': medicines,
    }
    return render(request, 'pharmacy/pwa/search.html', context)


# ============================================
# PHARMACY OWNER VIEWS
# ============================================

@login_required
def pwa_owner_dashboard(request):
    """Pharmacy owner dashboard"""
    # Check if user has pharmacy_owner role
    if not request.user.has_role('pharmacy_owner'):
        messages.error(request, 'You need to be a pharmacy owner to access this page.')
        return redirect('pharmacy_pwa:dashboard')
    
    if not hasattr(request.user, 'pharmacy_profile'):
        messages.error(request, 'You do not have a pharmacy profile.')
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile
    today = date.today()

    # Stats - Note: Order model doesn't have pharmacy field, need to filter by medicine ownership
    user_medicines = Medicine.objects.filter(owner=request.user)
    total_orders = Order.objects.filter(items__medicine__in=user_medicines).distinct().count()
    pending_orders = Order.objects.filter(items__medicine__in=user_medicines, status__in=['pending', 'confirmed']).distinct().count()
    today_orders = Order.objects.filter(items__medicine__in=user_medicines, created_at__date=today).distinct().count()
    today_revenue = Order.objects.filter(
        items__medicine__in=user_medicines,
        created_at__date=today,
        status='delivered'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    # Recent orders
    recent_orders = Order.objects.filter(items__medicine__in=user_medicines).distinct().order_by('-created_at')[:10]

    context = {
        'pharmacy': pharmacy,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
        'active_medicines': Medicine.objects.filter(owner=request.user, is_active=True).count(),
    }
    return render(request, 'pharmacy/pwa/owner/dashboard.html', context)


@login_required
def pwa_manage_orders(request):
    """Manage pharmacy orders"""
    # Check if user has pharmacy_owner role
    if not request.user.has_role('pharmacy_owner'):
        messages.error(request, 'You need to be a pharmacy owner to manage orders.')
        return redirect('pharmacy_pwa:dashboard')
    
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile
    user_medicines = Medicine.objects.filter(owner=request.user)
    orders = Order.objects.filter(items__medicine__in=user_medicines).distinct().order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'pharmacy': pharmacy,
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'pharmacy/pwa/owner/manage_orders.html', context)


@login_required
def pwa_order_detail_owner(request, order_id):
    """View order details (owner perspective)"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    request.user.pharmacy_profile
    user_medicines = Medicine.objects.filter(owner=request.user)
    order = get_object_or_404(Order, pk=order_id, items__medicine__in=user_medicines)

    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    return render(request, 'pharmacy/pwa/owner/order_detail.html', context)


@login_required
def pwa_update_order_status(request, order_id):
    """Update order status"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    request.user.pharmacy_profile
    user_medicines = Medicine.objects.filter(owner=request.user)
    order = get_object_or_404(Order, pk=order_id, items__medicine__in=user_medicines)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = ['pending', 'confirmed', 'processing', 'ready', 'out_for_delivery', 'delivered', 'cancelled']

        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            messages.success(request, 'Order status updated!')

        return redirect('pharmacy_pwa:order_detail_owner', order_id=order_id)

    return redirect('pharmacy_pwa:manage_orders')


@login_required
def pwa_manage_medicines(request):
    """Manage medicines"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile
    medicines = Medicine.objects.filter(owner=request.user).order_by('name')

    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        medicines = medicines.filter(category__slug=category_filter)

    categories = MedicineCategory.objects.filter(
        medicines__owner=request.user
    ).distinct()

    context = {
        'pharmacy': pharmacy,
        'medicines': medicines,
        'categories': categories,
        'category_filter': category_filter,
    }
    return render(request, 'pharmacy/pwa/owner/manage_medicines.html', context)


@login_required
def pwa_add_medicine(request):
    """Add new medicine"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        generic_name = request.POST.get('generic_name', '')
        brand_name = request.POST.get('brand_name', '')
        description = request.POST.get('description')
        price = request.POST.get('price')
        discount_price = request.POST.get('discount_price') or None
        category_id = request.POST.get('category')
        dosage = request.POST.get('dosage', '')
        dosage_form = request.POST.get('dosage_form', 'tablet')
        usage = request.POST.get('usage', '')
        active_ingredients = request.POST.get('active_ingredients', '')
        side_effects = request.POST.get('side_effects', '')
        warnings = request.POST.get('warnings', '')
        requires_prescription = request.POST.get('requires_prescription') == 'on'
        stock_quantity = request.POST.get('stock_quantity', 0)
        low_stock_threshold = request.POST.get('low_stock_threshold', 10)
        manufacturer = request.POST.get('manufacturer', '')
        pack_size = request.POST.get('pack_size', '')
        batch_number = request.POST.get('batch_number', '')
        expiry_date = request.POST.get('expiry_date') or None

        # Get the category object
        category = get_object_or_404(MedicineCategory, pk=category_id)

        medicine = Medicine.objects.create(
            owner=request.user,
            name=name,
            generic_name=generic_name,
            brand_name=brand_name,
            description=description,
            price=price,
            discount_price=discount_price,
            category=category,
            dosage=dosage,
            dosage_form=dosage_form,
            usage=usage,
            active_ingredients=active_ingredients,
            side_effects=side_effects,
            warnings=warnings,
            requires_prescription=requires_prescription,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            manufacturer=manufacturer,
            pack_size=pack_size,
            batch_number=batch_number,
            expiry_date=expiry_date,
            is_active=True,
        )

        # Handle image upload
        if 'image' in request.FILES:
            medicine.image = request.FILES['image']
            medicine.save()

        messages.success(request, 'Medicine added successfully!')
        return redirect('pharmacy_pwa:manage_medicines')

    context = {
        'pharmacy': pharmacy,
        'categories': MedicineCategory.objects.filter(is_active=True),
    }
    return render(request, 'pharmacy/pwa/owner/add_medicine.html', context)


@login_required
def pwa_edit_medicine(request, medicine_id):
    """Edit medicine"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile
    medicine = get_object_or_404(Medicine, pk=medicine_id, owner=request.user)

    if request.method == 'POST':
        # Update all fields from form
        medicine.name = request.POST.get('name')
        medicine.generic_name = request.POST.get('generic_name', '')
        medicine.brand_name = request.POST.get('brand_name', '')
        medicine.description = request.POST.get('description')
        medicine.price = request.POST.get('price')
        medicine.discount_price = request.POST.get('discount_price') or None
        medicine.dosage = request.POST.get('dosage', '')
        medicine.dosage_form = request.POST.get('dosage_form', 'tablet')
        medicine.usage = request.POST.get('usage', '')
        medicine.active_ingredients = request.POST.get('active_ingredients', '')
        medicine.side_effects = request.POST.get('side_effects', '')
        medicine.warnings = request.POST.get('warnings', '')
        medicine.requires_prescription = request.POST.get('requires_prescription') == 'on'
        medicine.stock_quantity = request.POST.get('stock_quantity', 0)
        medicine.low_stock_threshold = request.POST.get('low_stock_threshold', 10)
        medicine.manufacturer = request.POST.get('manufacturer', '')
        medicine.pack_size = request.POST.get('pack_size', '')
        medicine.batch_number = request.POST.get('batch_number', '')
        medicine.expiry_date = request.POST.get('expiry_date') or None
        medicine.is_active = request.POST.get('is_active') == 'on'
        
        category_id = request.POST.get('category')
        if category_id:
            medicine.category = get_object_or_404(MedicineCategory, pk=category_id)
        
        # Handle image upload
        if 'image' in request.FILES:
            medicine.image = request.FILES['image']
        
        medicine.save()

        messages.success(request, 'Medicine updated!')
        return redirect('pharmacy_pwa:manage_medicines')

    context = {
        'pharmacy': pharmacy,
        'medicine': medicine,
        'categories': MedicineCategory.objects.filter(is_active=True),
    }
    return render(request, 'pharmacy/pwa/owner/edit_medicine.html', context)


@login_required
def pwa_toggle_medicine(request, medicine_id):
    """Toggle medicine availability"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    request.user.pharmacy_profile
    medicine = get_object_or_404(Medicine, pk=medicine_id, owner=request.user)

    medicine.is_active = not medicine.is_active
    medicine.save()

    status = 'active' if medicine.is_active else 'inactive'
    messages.success(request, f'{medicine.name} is now {status}!')

    return redirect('pharmacy_pwa:manage_medicines')


@login_required
def pwa_delete_medicine(request, medicine_id):
    """Delete medicine"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    request.user.pharmacy_profile
    medicine = get_object_or_404(Medicine, pk=medicine_id, owner=request.user)

    if request.method == 'POST':
        medicine_name = medicine.name
        medicine.delete()
        messages.success(request, f'{medicine_name} deleted successfully!')
        return redirect('pharmacy_pwa:manage_medicines')

    return redirect('pharmacy_pwa:manage_medicines')


@login_required
def pwa_analytics(request):
    """Pharmacy analytics dashboard"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile

    user_medicines = Medicine.objects.filter(owner=request.user)

    context = {
        'pharmacy': pharmacy,
        'total_revenue': Order.objects.filter(
            items__medicine__in=user_medicines, status='delivered'
        ).aggregate(total=Sum('total'))['total'] or 0,
        'total_orders': Order.objects.filter(items__medicine__in=user_medicines).distinct().count(),
        'avg_order_value': Order.objects.filter(
            items__medicine__in=user_medicines, status='delivered'
        ).aggregate(avg=Avg('total'))['avg'] or 0,
        'popular_medicines': Medicine.objects.filter(
            owner=request.user
        ).annotate(order_count=Count('orderitem')).order_by('-order_count')[:5],
    }
    return render(request, 'pharmacy/pwa/owner/analytics.html', context)


@login_required
def pwa_pharmacy_settings(request):
    """Pharmacy settings"""
    if not hasattr(request.user, 'pharmacy_profile'):
        return redirect('pharmacy_pwa:dashboard')

    pharmacy = request.user.pharmacy_profile

    if request.method == 'POST':
        # Update pharmacy settings
        pharmacy.name = request.POST.get('name')
        pharmacy.phone = request.POST.get('phone')
        pharmacy.email = request.POST.get('email')
        pharmacy.address = request.POST.get('address')
        pharmacy.save()

        messages.success(request, 'Settings updated successfully!')
        return redirect('pharmacy_pwa:pharmacy_settings')

    context = {
        'pharmacy': pharmacy,
    }
    return render(request, 'pharmacy/pwa/owner/settings.html', context)


@login_required
def pwa_notifications(request):
    """View notifications"""
    # Implement notifications logic
    context = {
        'notifications': [],
    }
    return render(request, 'pharmacy/pwa/notifications.html', context)
