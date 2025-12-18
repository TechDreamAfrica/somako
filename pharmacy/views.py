from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal
from .models import (
    Medicine, MedicineCategory, Prescription, Cart, CartItem,
    Order, OrderItem, Wishlist
)


def medicine_list(request):
    """List all available medicines with search and filters"""
    medicines = Medicine.objects.filter(is_active=True).select_related('category')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) |
            Q(generic_name__icontains=search_query) |
            Q(brand_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(manufacturer__icontains=search_query)
        )

    # Filters
    category_id = request.GET.get('category', '')
    if category_id:
        medicines = medicines.filter(category_id=category_id)

    dosage_form = request.GET.get('dosage_form', '')
    if dosage_form:
        medicines = medicines.filter(dosage_form=dosage_form)

    requires_prescription = request.GET.get('requires_prescription', '')
    if requires_prescription:
        medicines = medicines.filter(requires_prescription=(requires_prescription == 'yes'))

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    medicines = medicines.order_by(sort_by)

    # Pagination
    paginator = Paginator(medicines, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories for filter
    categories = MedicineCategory.objects.filter(is_active=True)

    context = {
        'medicines': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_dosage_form': dosage_form,
    }
    return render(request, 'pharmacy/medicine_list.html', context)


def medicine_detail(request, slug):
    """Display medicine details"""
    medicine = get_object_or_404(
        Medicine.objects.select_related('category').prefetch_related('reviews'),
        slug=slug,
        is_active=True
    )

    # Increment views
    medicine.views_count += 1
    medicine.save(update_fields=['views_count'])

    # Get related medicines
    related_medicines = Medicine.objects.filter(
        category=medicine.category,
        is_active=True
    ).exclude(pk=medicine.pk)[:4]

    # Get reviews
    reviews = medicine.reviews.filter(is_approved=True).select_related('user')[:10]

    context = {
        'medicine': medicine,
        'related_medicines': related_medicines,
        'reviews': reviews,
    }
    return render(request, 'pharmacy/medicine_detail.html', context)


@login_required
def add_to_cart(request, medicine_id):
    """Add medicine to cart"""
    if request.method == 'POST':
        medicine = get_object_or_404(Medicine, pk=medicine_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        prescription_id = request.POST.get('prescription_id', '')

        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if medicine requires prescription
        prescription = None
        if medicine.requires_prescription:
            if not prescription_id:
                messages.error(request, 'This medicine requires a prescription.')
                return redirect('pharmacy:medicine_detail', slug=medicine.slug)
            prescription = get_object_or_404(Prescription, pk=prescription_id, user=request.user, status='approved')

        # Add to cart or update quantity
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            medicine=medicine,
            defaults={
                'quantity': quantity,
                'prescription': prescription
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f'{medicine.name} added to cart.')
        return redirect('pharmacy:cart')

    return redirect('pharmacy:medicine_list')


@login_required
def cart_view(request):
    """Display shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('medicine', 'prescription').all()

    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'pharmacy/cart.html', context)


@login_required
def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
        action = request.POST.get('action')

        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                messages.success(request, 'Item removed from cart.')
                return redirect('pharmacy:cart')
        elif action == 'remove':
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')
            return redirect('pharmacy:cart')

        messages.success(request, 'Cart updated.')
    return redirect('pharmacy:cart')


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    medicine_name = cart_item.medicine.name
    cart_item.delete()
    messages.success(request, f'{medicine_name} removed from cart.')
    return redirect('pharmacy:cart')


@login_required
def checkout(request):
    """Checkout and create order"""
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.select_related('medicine').all()

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('pharmacy:cart')

        # Get delivery information
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        phone = request.POST.get('phone', '').strip()
        payment_method = request.POST.get('payment_method', 'cash')

        # Validate required fields
        if not all([address, city, state, postal_code, phone]):
            messages.error(request, 'Please fill in all delivery information fields.')
            return redirect('pharmacy:checkout')

        # Calculate totals
        subtotal = cart.subtotal
        delivery_charge = Decimal('10.00')  # Fixed delivery charge
        tax = subtotal * Decimal('0.05')  # 5% tax
        total = subtotal + delivery_charge + tax

        # Create order
        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            tax=tax,
            total=total,
            payment_method=payment_method,
            delivery_address=address,
            delivery_city=city,
            delivery_state=state,
            delivery_postal_code=postal_code,
            delivery_phone=phone,
        )

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                medicine=cart_item.medicine,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price,
                prescription=cart_item.prescription,
            )

        # Clear cart
        cart_items.delete()

        messages.success(request, f'Order {order.order_number} placed successfully!')
        return redirect('pharmacy:order_detail', order_number=order.order_number)

    # GET request - show checkout form
    from django.conf import settings
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('medicine').all()

    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('pharmacy:cart')

    # Calculate totals
    subtotal = cart.subtotal
    delivery_charge = Decimal('10.00')
    tax = subtotal * Decimal('0.05')
    total = subtotal + delivery_charge + tax

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'pharmacy/checkout.html', context)


@login_required
def order_list(request):
    """List user's orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)

    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_status': status,
    }
    return render(request, 'pharmacy/order_list.html', context)


@login_required
def order_detail(request, order_number):
    """Display order details"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__medicine'),
        order_number=order_number,
        user=request.user
    )

    context = {
        'order': order,
    }
    return render(request, 'pharmacy/order_detail.html', context)


@login_required
def cancel_order(request, order_number):
    """Cancel an order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.can_be_cancelled:
        order.status = 'cancelled'
        order.save()
        messages.success(request, 'Order cancelled successfully.')
    else:
        messages.error(request, 'This order cannot be cancelled.')

    return redirect('pharmacy:order_detail', order_number=order_number)


@login_required
def prescription_list(request):
    """List user's prescriptions"""
    prescriptions = Prescription.objects.filter(user=request.user).order_by('-created_at')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        prescriptions = prescriptions.filter(status=status)

    # Pagination
    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_status': status,
    }
    return render(request, 'pharmacy/prescription_list.html', context)


@login_required
def prescription_upload(request):
    """Upload a new prescription"""
    if request.method == 'POST':
        doctor_name = request.POST.get('doctor_name')
        doctor_license = request.POST.get('doctor_license', '')
        hospital_clinic = request.POST.get('hospital_clinic', '')
        issue_date = request.POST.get('issue_date')
        expiry_date = request.POST.get('expiry_date')
        patient_notes = request.POST.get('patient_notes', '')
        prescription_file = request.FILES.get('prescription_file')

        prescription = Prescription.objects.create(
            user=request.user,
            doctor_name=doctor_name,
            doctor_license=doctor_license,
            hospital_clinic=hospital_clinic,
            issue_date=issue_date,
            expiry_date=expiry_date,
            patient_notes=patient_notes,
            prescription_file=prescription_file,
        )

        messages.success(request, f'Prescription {prescription.prescription_number} uploaded successfully. It will be reviewed shortly.')
        return redirect('pharmacy:prescription_list')

    return render(request, 'pharmacy/prescription_upload.html')


@login_required
def prescription_detail(request, pk):
    """Display prescription details"""
    prescription = get_object_or_404(Prescription, pk=pk, user=request.user)

    context = {
        'prescription': prescription,
    }
    return render(request, 'pharmacy/prescription_detail.html', context)


@login_required
def wishlist_view(request):
    """Display user's wishlist"""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    medicines = wishlist.medicines.filter(is_active=True)

    # Pagination
    paginator = Paginator(medicines, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wishlist': wishlist,
        'page_obj': page_obj,
    }
    return render(request, 'pharmacy/wishlist.html', context)


@login_required
def toggle_wishlist(request, medicine_id):
    """Add or remove medicine from wishlist"""
    medicine = get_object_or_404(Medicine, pk=medicine_id, is_active=True)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    if medicine in wishlist.medicines.all():
        wishlist.medicines.remove(medicine)
        messages.success(request, f'{medicine.name} removed from wishlist.')
    else:
        wishlist.medicines.add(medicine)
        messages.success(request, f'{medicine.name} added to wishlist.')

    return redirect(request.META.get('HTTP_REFERER', 'pharmacy:medicine_list'))