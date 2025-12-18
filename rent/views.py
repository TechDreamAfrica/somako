from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal
from .models import (
    Property, Equipment, PropertyCategory, EquipmentCategory,
    RentalBooking
)


def property_list(request):
    """List all available properties with search and filters"""
    properties = Property.objects.filter(is_available=True).select_related('owner', 'category')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        properties = properties.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(address__icontains=search_query)
        )

    # Filters
    property_type = request.GET.get('type', '')
    if property_type:
        properties = properties.filter(property_type=property_type)

    city = request.GET.get('city', '')
    if city:
        properties = properties.filter(city__icontains=city)

    category_id = request.GET.get('category', '')
    if category_id:
        properties = properties.filter(category_id=category_id)

    rental_period = request.GET.get('period', '')
    if rental_period:
        properties = properties.filter(rental_period=rental_period)

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    properties = properties.order_by(sort_by)

    # Pagination
    paginator = Paginator(properties, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories for filter
    categories = PropertyCategory.objects.all()

    context = {
        'properties': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_type': property_type,
        'selected_city': city,
        'selected_category': category_id,
        'selected_period': rental_period,
    }
    return render(request, 'rent/property_list.html', context)


def property_detail(request, pk):
    """Display property details"""
    from .models import SavedProperty

    property_obj = get_object_or_404(
        Property.objects.select_related('owner', 'category').prefetch_related('images', 'reviews'),
        pk=pk
    )

    # Increment views
    property_obj.views_count += 1
    property_obj.save(update_fields=['views_count'])

    # Check if user has saved this property
    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedProperty.objects.filter(user=request.user, property=property_obj).exists()

    # Get related properties
    related_properties = Property.objects.filter(
        category=property_obj.category,
        is_available=True
    ).exclude(pk=pk)[:4]

    context = {
        'property': property_obj,
        'related_properties': related_properties,
        'is_saved': is_saved,
    }
    return render(request, 'rent/property_detail.html', context)


def equipment_list(request):
    """List all available equipment with search and filters"""
    equipment_items = Equipment.objects.filter(is_available=True).select_related('owner', 'category')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        equipment_items = equipment_items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # Filters
    city = request.GET.get('city', '')
    if city:
        equipment_items = equipment_items.filter(city__icontains=city)

    category_id = request.GET.get('category', '')
    if category_id:
        equipment_items = equipment_items.filter(category_id=category_id)

    condition = request.GET.get('condition', '')
    if condition:
        equipment_items = equipment_items.filter(condition=condition)

    rental_period = request.GET.get('period', '')
    if rental_period:
        equipment_items = equipment_items.filter(rental_period=rental_period)

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    equipment_items = equipment_items.order_by(sort_by)

    # Pagination
    paginator = Paginator(equipment_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories for filter
    categories = EquipmentCategory.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_city': city,
        'selected_category': category_id,
        'selected_condition': condition,
        'selected_period': rental_period,
    }
    return render(request, 'rent/equipment_list.html', context)


def equipment_detail(request, pk):
    """Display equipment details"""
    equipment = get_object_or_404(
        Equipment.objects.select_related('owner', 'category').prefetch_related('images', 'reviews'),
        pk=pk
    )

    # Increment views
    equipment.views_count += 1
    equipment.save(update_fields=['views_count'])

    # Get related equipment
    related_equipment = Equipment.objects.filter(
        category=equipment.category,
        is_available=True
    ).exclude(pk=pk)[:4]

    context = {
        'equipment': equipment,
        'related_equipment': related_equipment,
    }
    return render(request, 'rent/equipment_detail.html', context)


@login_required
def booking_list(request):
    """List user's bookings"""
    bookings = RentalBooking.objects.filter(
        renter=request.user
    ).select_related('property', 'equipment').order_by('-created_at')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        bookings = bookings.filter(status=status)

    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_status': status,
    }
    return render(request, 'rent/booking_list.html', context)


@login_required
def booking_create(request):
    """Create a new booking"""
    # Get property or equipment from query params
    property_id = request.GET.get('property')
    equipment_id = request.GET.get('equipment')

    property_obj = None
    equipment_obj = None

    if property_id:
        property_obj = get_object_or_404(Property, pk=property_id, is_available=True)
    elif equipment_id:
        equipment_obj = get_object_or_404(Equipment, pk=equipment_id, is_available=True)
    else:
        messages.error(request, 'Please select a property or equipment to book.')
        return redirect('rent:property_list')

    if request.method == 'POST':
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        quantity = int(request.POST.get('quantity', 1))
        rental_years = int(request.POST.get('rental_years', 1))
        notes = request.POST.get('notes', '')
        payment_method = request.POST.get('payment_method', 'paystack')

        try:
            from datetime import datetime, date as date_class

            # Check if this is a purchase transaction
            is_purchase = (property_obj and property_obj.listing_type == 'for_sale') or \
                         (equipment_obj and equipment_obj.listing_type == 'for_sale')

            # For purchases, use today's date if dates are not provided
            if is_purchase:
                if not start_date or not end_date:
                    today = date_class.today()
                    start = today
                    end = today
                else:
                    start = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                # For rentals, dates are required
                if not start_date or not end_date:
                    messages.error(request, 'Please provide both start and end dates.')
                    return redirect(request.path + f'?{"property=" + property_id if property_id else "equipment=" + equipment_id}')

                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()

                # Validate end date is after start date (only for rentals)
                if start >= end:
                    messages.error(request, 'End date must be after start date.')
                    return redirect(request.path + f'?{"property=" + property_id if property_id else "equipment=" + equipment_id}')

                # Validate rental years for property rentals
                if property_obj:
                    if rental_years < property_obj.minimum_rental_years:
                        messages.error(request, f'Minimum rental period for this property is {property_obj.minimum_rental_years} year(s).')
                        return redirect(request.path + f'?property={property_id}')

                    # Validate that date range matches rental years (with 7 days tolerance)
                    duration_days = (end - start).days
                    expected_days = rental_years * 365.25  # Account for leap years
                    tolerance_days = 7

                    if abs(duration_days - expected_days) > tolerance_days:
                        messages.error(
                            request,
                            f'The date range must match the selected rental period of {rental_years} year(s). '
                            f'Expected approximately {int(expected_days)} days, but got {duration_days} days. '
                            f'Please adjust your dates accordingly.'
                        )
                        return redirect(request.path + f'?property={property_id}')

            # Calculate total amount based on duration
            duration_days = (end - start).days

            if property_obj:
                # Calculate based on rental period
                if property_obj.rental_period == 'month':
                    periods = duration_days / 30
                elif property_obj.rental_period == 'week':
                    periods = duration_days / 7
                else:  # day
                    periods = duration_days

                total_amount = property_obj.price_per_period * Decimal(str(periods))
                transaction_type = 'rental'

                if property_obj.listing_type == 'for_sale':
                    total_amount = property_obj.price_per_period  # Fixed price for sale
                    transaction_type = 'purchase'

                booking = RentalBooking.objects.create(
                    booking_type='property',
                    transaction_type=transaction_type,
                    property=property_obj,
                    renter=request.user,
                    start_date=start,
                    end_date=end,
                    rental_years=rental_years,
                    total_amount=total_amount,
                    notes=notes,
                    status='pending'
                )
            else:
                # Calculate for equipment
                if equipment_obj.rental_period == 'day':
                    periods = duration_days
                elif equipment_obj.rental_period == 'week':
                    periods = duration_days / 7
                elif equipment_obj.rental_period == 'month':
                    periods = duration_days / 30
                else:  # hour
                    periods = duration_days * 24

                total_amount = equipment_obj.price_per_period * Decimal(str(periods)) * quantity
                transaction_type = 'rental'

                if equipment_obj.listing_type == 'for_sale':
                    total_amount = equipment_obj.price_per_period * quantity  # Fixed price for sale
                    transaction_type = 'purchase'

                booking = RentalBooking.objects.create(
                    booking_type='equipment',
                    transaction_type=transaction_type,
                    equipment=equipment_obj,
                    renter=request.user,
                    start_date=start,
                    end_date=end,
                    quantity=quantity,
                    total_amount=total_amount,
                    notes=notes,
                    status='pending'
                )

            # Handle payment
            if payment_method == 'paystack':
                from payment.helpers import create_payment, initialize_paystack_payment

                item_name = property_obj.title if property_obj else equipment_obj.name
                trans_label = 'Purchase' if booking.transaction_type == 'purchase' else 'Rental'
                payment = create_payment(
                    user=request.user,
                    amount=total_amount,
                    source_app='rent',
                    order_id=str(booking.id),
                    description=f'{trans_label} Booking #{booking.id} - {item_name}',
                    payment_method='paystack'
                )

                result = initialize_paystack_payment(payment)
                if result['status']:
                    return redirect(result['authorization_url'])
                else:
                    messages.error(request, f"Payment initialization failed: {result['message']}")
                    return redirect('rent:booking_detail', pk=booking.id)
            else:
                messages.success(request, 'Booking request submitted successfully! Payment on arrival.')
                return redirect('rent:booking_detail', pk=booking.id)

        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
            return redirect(request.path + f'?{"property=" + property_id if property_id else "equipment=" + equipment_id}')

    # GET request - show booking form
    from datetime import date
    context = {
        'property': property_obj,
        'equipment': equipment_obj,
        'today': date.today(),
    }
    return render(request, 'rent/booking_create.html', context)


@login_required
def booking_detail(request, pk):
    """Display booking details"""
    booking = get_object_or_404(
        RentalBooking.objects.select_related('property', 'equipment', 'renter'),
        pk=pk
    )

    # Check if user is the renter or the owner
    if booking.renter != request.user:
        if booking.booking_type == 'property' and booking.property:
            if booking.property.owner != request.user:
                messages.error(request, 'You do not have permission to view this booking.')
                return redirect('rent:booking_list')
        elif booking.booking_type == 'equipment' and booking.equipment:
            if booking.equipment.owner != request.user:
                messages.error(request, 'You do not have permission to view this booking.')
                return redirect('rent:booking_list')

    context = {
        'booking': booking,
    }
    return render(request, 'rent/booking_detail.html', context)


@login_required
def booking_cancel(request, pk):
    """Cancel a booking"""
    booking = get_object_or_404(RentalBooking, pk=pk, renter=request.user)

    if booking.status in ['pending', 'confirmed']:
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Booking cancelled successfully.')
    else:
        messages.error(request, 'This booking cannot be cancelled.')

    return redirect('rent:booking_detail', pk=pk)


@login_required
def my_properties(request):
    """List properties owned by the user"""
    properties = Property.objects.filter(owner=request.user).order_by('-created_at')

    paginator = Paginator(properties, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'rent/my_properties.html', context)


@login_required
def my_equipment(request):
    """List equipment owned by the user"""
    equipment_items = Equipment.objects.filter(owner=request.user).order_by('-created_at')

    paginator = Paginator(equipment_items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'rent/my_equipment.html', context)


@login_required
def dashboard_pwa(request):
    """PWA Dashboard for Rent app"""
    properties = Property.objects.filter(owner=request.user)
    bookings = RentalBooking.objects.filter(
        Q(renter=request.user) | Q(property__owner=request.user)
    )

    context = {
        'properties_count': properties.count(),
        'tenants_count': bookings.filter(status='confirmed').count(),
        'revenue': sum([b.total_amount for b in bookings.filter(status='completed')]),
        'views': sum([p.views_count for p in properties]),
    }
    return render(request, 'rent/dashboard_pwa.html', context)