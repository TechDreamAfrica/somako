"""
Rent PWA Views - Progressive Web App specific views
Optimized for mobile-first experience with touch-friendly interfaces
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from datetime import date

from rent.models import Equipment, EquipmentCategory, RentalBooking, SavedEquipment


# ============================================
# CUSTOMER VIEWS
# ============================================

@login_required
def pwa_dashboard(request):
    """PWA Rent Dashboard - Role-based (Customer/Equipment Owner)"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'rent'

    user = request.user
    # Check if user has equipment_owner role
    is_owner = user.has_role('equipment_owner')
    has_equipment = Equipment.objects.filter(owner=user).exists()

    if is_owner and has_equipment:
        return redirect('rent_pwa:owner_dashboard')

    # Customer dashboard
    featured_equipment = Equipment.objects.filter(
        is_available=True, listing_type='for_rent'
    ).order_by('-created_at')

    context = {
        'featured_equipment': featured_equipment[:6],
        'recent_equipment': featured_equipment[6:12] if len(featured_equipment) > 6 else featured_equipment[:6],
        'recent_bookings': RentalBooking.objects.filter(
            renter=user
        ).order_by('-created_at')[:3],
        'cart_count': 0,  # Placeholder - implement cart later if needed
        'saved_count': SavedEquipment.objects.filter(user=user).count(),
    }
    return render(request, 'rent/pwa/dashboard.html', context)


@login_required  
def pwa_equipment_list(request):
    """Browse all equipment"""
    equipment = Equipment.objects.filter(is_available=True, listing_type='for_rent')

    # Filters
    category_id = request.GET.get('category')
    city = request.GET.get('city')
    search_query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'newest')

    if category_id:
        equipment = equipment.filter(category_id=category_id)

    if city:
        equipment = equipment.filter(city__icontains=city)

    if search_query:
        equipment = equipment.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # Sorting
    if sort == 'price_low':
        equipment = equipment.order_by('price_per_period')
    elif sort == 'price_high':
        equipment = equipment.order_by('-price_per_period')
    else:  # newest
        equipment = equipment.order_by('-created_at')

    context = {
        'equipment': equipment,
        'categories': EquipmentCategory.objects.all(),
        'cities': Equipment.objects.values_list('city', flat=True).distinct(),
        'selected_category': category_id,
        'selected_city': city,
        'selected_sort': sort,
        'search_query': search_query,
    }
    return render(request, 'rent/pwa/equipment_list.html', context)


@login_required
def pwa_equipment_detail(request, pk):
    """Equipment details page"""
    equipment = get_object_or_404(Equipment, pk=pk, is_available=True)

    # Check if equipment is saved by user
    is_saved = SavedEquipment.objects.filter(user=request.user, equipment=equipment).exists()

    context = {
        'equipment': equipment,
        'is_saved': is_saved,
        'images': equipment.images.all() if hasattr(equipment, 'images') else [],
    }
    return render(request, 'rent/pwa/equipment_detail.html', context)


@login_required
def pwa_category_properties(request, category):
    """Equipment filtered by category (legacy endpoint)"""
    return redirect('rent_pwa:category_equipment', category=category)


@login_required
def pwa_equipment_list(request):
    """Browse all equipment"""
    equipment = Equipment.objects.filter(is_available=True)

    # Filters
    category_id = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'newest')

    if category_id:
        equipment = equipment.filter(category_id=category_id)

    if search_query:
        equipment = equipment.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Sorting
    if sort == 'price_low':
        equipment = equipment.order_by('price_per_period')
    elif sort == 'price_high':
        equipment = equipment.order_by('-price_per_period')
    else:  # newest
        equipment = equipment.order_by('-created_at')

    context = {
        'equipment': equipment,
        'categories': EquipmentCategory.objects.all(),
        'selected_category': category_id,
        'selected_sort': sort,
        'search_query': search_query,
    }
    return render(request, 'rent/pwa/equipment_list.html', context)


@login_required
def pwa_equipment_detail(request, pk):
    """Equipment details page"""
    equipment = get_object_or_404(Equipment, pk=pk, is_available=True)

    context = {
        'equipment': equipment,
    }
    return render(request, 'rent/pwa/equipment_detail.html', context)


@login_required
def pwa_category_equipment(request, category):
    """Equipment filtered by category"""
    category_obj = get_object_or_404(EquipmentCategory, name=category)
    equipment = Equipment.objects.filter(
        category=category_obj,
        is_available=True
    ).order_by('-created_at')

    context = {
        'category': category_obj,
        'equipment': equipment,
    }
    return render(request, 'rent/pwa/category_equipment.html', context)


@login_required
def pwa_book_equipment(request, equipment_id):
    """Book equipment"""
    equipment = get_object_or_404(Equipment, pk=equipment_id, is_available=True)

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        notes = request.POST.get('notes', '')

        # Create booking
        booking = RentalBooking.objects.create(
            equipment=equipment,
            renter=request.user,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
            total_amount=equipment.price_per_period,
            status='pending'
        )

        messages.success(request, f'Booking request submitted! Booking #{booking.id}')
        return redirect('rent_pwa:booking_detail', booking_id=booking.id)

    context = {
        'equipment': equipment,
    }
    return render(request, 'rent/pwa/book_equipment.html', context)


@login_required
def pwa_booking_list(request):
    """View booking history"""
    bookings = RentalBooking.objects.filter(renter=request.user).order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    context = {
        'bookings': bookings,
        'status_filter': status_filter,
    }
    return render(request, 'rent/pwa/booking_list.html', context)


@login_required
def pwa_booking_detail(request, booking_id):
    """View booking details"""
    booking = get_object_or_404(RentalBooking, pk=booking_id, renter=request.user)

    context = {
        'booking': booking,
        'can_cancel': booking.status in ['pending', 'confirmed'],
    }
    return render(request, 'rent/pwa/booking_detail.html', context)


@login_required
def pwa_cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(RentalBooking, pk=booking_id, renter=request.user)

    if booking.status in ['pending', 'confirmed']:
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Booking cancelled successfully!')
    else:
        messages.error(request, 'This booking cannot be cancelled.')

    return redirect('rent_pwa:booking_detail', booking_id=booking_id)


@login_required
def pwa_saved_equipment(request):
    """View saved equipment"""
    # Get saved equipment objects
    saved_equipment_objects = SavedEquipment.objects.filter(user=request.user).select_related('equipment')
    equipment = [se.equipment for se in saved_equipment_objects if se.equipment.is_available]

    context = {
        'equipment': equipment,
    }
    return render(request, 'rent/pwa/saved_equipment.html', context)


@login_required
def pwa_toggle_saved(request, equipment_id):
    """Toggle equipment saved status"""
    equipment_obj = get_object_or_404(Equipment, pk=equipment_id)

    # Check if equipment is already saved
    saved_obj = SavedEquipment.objects.filter(user=request.user, equipment=equipment_obj).first()
    
    if saved_obj:
        # Remove from saved
        saved_obj.delete()
        messages.success(request, f'{equipment_obj.name} removed from saved!')
    else:
        # Add to saved
        SavedEquipment.objects.create(user=request.user, equipment=equipment_obj)
        messages.success(request, f'{equipment_obj.name} added to saved!')

    return redirect('rent_pwa:equipment_detail', pk=equipment_id)


@login_required
def pwa_search(request):
    """Search equipment"""
    query = request.GET.get('q', '')

    equipment = []

    if query:
        equipment = Equipment.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(brand__icontains=query) |
            Q(city__icontains=query),
            is_available=True
        )[:20]

    context = {
        'query': query,
        'equipment': equipment,
    }
    return render(request, 'rent/pwa/search.html', context)


# ============================================
# LANDLORD/OWNER VIEWS
# ============================================

@login_required
def pwa_owner_dashboard(request):
    """Equipment owner dashboard"""
    # Check if user has equipment_owner role
    if not request.user.has_role('equipment_owner'):
        messages.error(request, 'You need to be an equipment owner to access this page.')
        return redirect('rent_pwa:dashboard')
    
    equipment = Equipment.objects.filter(owner=request.user)

    if not equipment.exists():
        messages.info(request, 'You do not have any equipment listed.')
        return redirect('rent_pwa:dashboard')

    today = date.today()

    # Stats
    total_bookings = RentalBooking.objects.filter(
        equipment__owner=request.user
    ).count()
    pending_bookings = RentalBooking.objects.filter(
        equipment__owner=request.user,
        status__in=['pending', 'confirmed']
    ).count()
    today_bookings = RentalBooking.objects.filter(
        equipment__owner=request.user,
        created_at__date=today
    ).count()

    # Recent bookings
    recent_bookings = RentalBooking.objects.filter(
        equipment__owner=request.user
    ).order_by('-created_at')[:10]

    context = {
        'total_equipment': equipment.count(),
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'today_bookings': today_bookings,
        'recent_bookings': recent_bookings,
        'active_equipment': equipment.filter(is_available=True).count(),
    }
    return render(request, 'rent/pwa/owner/dashboard.html', context)


@login_required
def pwa_manage_equipment(request):
    """Manage equipment"""
    # Check if user has equipment_owner role
    if not request.user.has_role('equipment_owner'):
        messages.error(request, 'You need to be an equipment owner to manage equipment.')
        return redirect('rent_pwa:dashboard')
    
    equipment = Equipment.objects.filter(owner=request.user).order_by('-created_at')

    context = {
        'equipment': equipment,
    }
    return render(request, 'rent/pwa/owner/manage_equipment.html', context)


@login_required
def pwa_add_equipment(request):
    """Add new equipment"""
    # Check if user has equipment_owner role
    if not request.user.has_role('equipment_owner'):
        messages.error(request, 'You need to be an equipment owner to add equipment.')
        return redirect('rent_pwa:dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price_per_period')

        Equipment.objects.create(
            owner=request.user,
            name=name,
            description=description,
            price_per_period=price,
            is_available=True
        )

        messages.success(request, 'Equipment added successfully!')
        return redirect('rent_pwa:manage_equipment')

    context = {
        'categories': EquipmentCategory.objects.all(),
    }
    return render(request, 'rent/pwa/owner/add_equipment.html', context)


@login_required
def pwa_edit_equipment(request, equipment_id):
    """Edit equipment"""
    equipment = get_object_or_404(Equipment, pk=equipment_id, owner=request.user)

    if request.method == 'POST':
        equipment.name = request.POST.get('name')
        equipment.description = request.POST.get('description')
        equipment.price_per_period = request.POST.get('price_per_period')
        equipment.save()

        messages.success(request, 'Equipment updated!')
        return redirect('rent_pwa:manage_equipment')

    context = {
        'equipment': equipment,
        'categories': EquipmentCategory.objects.all(),
    }
    return render(request, 'rent/pwa/owner/edit_equipment.html', context)


@login_required
def pwa_manage_bookings(request):
    """Manage bookings"""
    # Check if user has landlord or equipment_owner role
    if not (request.user.has_role('landlord') or request.user.has_role('equipment_owner')):
        messages.error(request, 'You need to be a landlord or equipment owner to manage bookings.')
        return redirect('rent_pwa:dashboard')
    
    bookings = RentalBooking.objects.filter(
        Q(property__owner=request.user) | Q(equipment__owner=request.user)
    ).order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    context = {
        'bookings': bookings,
        'status_filter': status_filter,
    }
    return render(request, 'rent/pwa/owner/manage_bookings.html', context)


@login_required
def pwa_booking_detail_owner(request, booking_id):
    """View booking details (owner perspective)"""
    booking = get_object_or_404(
        RentalBooking,
        pk=booking_id
    )

    # Verify ownership
    if booking.property:
        if booking.property.owner != request.user:
            messages.error(request, 'Access denied.')
            return redirect('rent_pwa:owner_dashboard')
    elif booking.equipment:
        if booking.equipment.owner != request.user:
            messages.error(request, 'Access denied.')
            return redirect('rent_pwa:owner_dashboard')

    context = {
        'booking': booking,
    }
    return render(request, 'rent/pwa/owner/booking_detail.html', context)


@login_required
def pwa_update_booking_status(request, booking_id):
    """Update booking status"""
    booking = get_object_or_404(RentalBooking, pk=booking_id)

    # Verify ownership
    is_owner = False
    if booking.property and booking.property.owner == request.user:
        is_owner = True
    elif booking.equipment and booking.equipment.owner == request.user:
        is_owner = True

    if not is_owner:
        messages.error(request, 'Access denied.')
        return redirect('rent_pwa:owner_dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = ['pending', 'confirmed', 'active', 'completed', 'cancelled']

        if new_status in valid_statuses:
            booking.status = new_status
            booking.save()
            messages.success(request, 'Booking status updated!')

        return redirect('rent_pwa:booking_detail_owner', booking_id=booking_id)

    return redirect('rent_pwa:manage_bookings')


@login_required
def pwa_analytics(request):
    """Analytics dashboard"""
    # Check if user has equipment_owner role
    if not request.user.has_role('equipment_owner'):
        messages.error(request, 'You need to be an equipment owner to view analytics.')
        return redirect('rent_pwa:dashboard')
    
    equipment = Equipment.objects.filter(owner=request.user)

    if not equipment.exists():
        return redirect('rent_pwa:owner_dashboard')

    context = {
        'total_revenue': RentalBooking.objects.filter(
            equipment__owner=request.user,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_bookings': RentalBooking.objects.filter(
            equipment__owner=request.user
        ).count(),
        'avg_booking_value': RentalBooking.objects.filter(
            equipment__owner=request.user,
            status='completed'
        ).aggregate(avg=Avg('total_amount'))['avg'] or 0,
        'popular_equipment': equipment.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5],
    }
    return render(request, 'rent/pwa/owner/analytics.html', context)


@login_required
def pwa_settings(request):
    """Settings"""
    context = {}
    return render(request, 'rent/pwa/owner/settings.html', context)


@login_required
def pwa_notifications(request):
    """View notifications"""
    context = {
        'notifications': [],
    }
    return render(request, 'rent/pwa/notifications.html', context)
