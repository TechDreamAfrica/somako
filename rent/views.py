from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal
from .models import (
    Equipment, EquipmentCategory,
    RentalBooking
)


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
    """Equipment detail view with inline booking form"""
    from datetime import date as date_class
    
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

    # Handle inline booking form submission
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            from decimal import Decimal
            from .notifications import notify_rental_booked
            
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip() 
            quantity = int(request.POST.get('quantity', 1))
            notes = request.POST.get('notes', '')
            payment_method = request.POST.get('payment_method', 'paystack')

            # For purchases, use today's date if dates are not provided
            if equipment.listing_type == 'for_sale':
                if not start_date or not end_date:
                    today = date_class.today()
                    start = today
                    end = today
                else:
                    from datetime import datetime
                    start = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                # For rentals, dates are required
                if not start_date or not end_date:
                    messages.error(request, 'Please provide both start and end dates.')
                    return redirect('rent:equipment_detail', pk=pk)

                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()

                # Validate end date is after start date
                if start >= end:
                    messages.error(request, 'End date must be after start date.')
                    return redirect('rent:equipment_detail', pk=pk)

            # Validate quantity
            if quantity > equipment.quantity_available:
                messages.error(request, f'Only {equipment.quantity_available} unit(s) available.')
                return redirect('rent:equipment_detail', pk=pk)

            # Calculate total amount based on duration
            duration_days = (end - start).days
            
            if equipment.rental_period == 'day':
                periods = duration_days if duration_days > 0 else 1
            elif equipment.rental_period == 'week':
                periods = duration_days / 7 if duration_days > 0 else 1
            elif equipment.rental_period == 'month':
                periods = duration_days / 30 if duration_days > 0 else 1
            else:  # hour
                periods = duration_days * 24 if duration_days > 0 else 1

            total_amount = equipment.price_per_period * Decimal(str(periods)) * quantity
            transaction_type = 'rental'

            if equipment.listing_type == 'for_sale':
                total_amount = equipment.price_per_period * quantity  # Fixed price for sale
                transaction_type = 'purchase'

            # Create booking
            booking = RentalBooking.objects.create(
                transaction_type=transaction_type,
                equipment=equipment,
                renter=request.user,
                start_date=start,
                end_date=end,
                quantity=quantity,
                total_amount=total_amount,
                notes=notes,
                status='pending'
            )

            # Send SMS notification to equipment owner
            try:
                notify_rental_booked(booking)
            except Exception as e:
                # Don't fail the booking if SMS fails
                print(f"SMS notification failed: {str(e)}")

            # Handle payment
            if payment_method == 'paystack':
                from payment.helpers import create_payment, initialize_paystack_payment

                trans_label = 'Purchase' if booking.transaction_type == 'purchase' else 'Rental'
                payment = create_payment(
                    user=request.user,
                    amount=total_amount,
                    source_app='rent',
                    order_id=str(booking.id),
                    description=f'{trans_label} Booking #{booking.id} - {equipment.name}',
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
            return redirect('rent:equipment_detail', pk=pk)

    context = {
        'equipment': equipment,
        'related_equipment': related_equipment,
        'today': date_class.today(),
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
    """Create a new booking for equipment"""
    # Get equipment from query params
    equipment_id = request.GET.get('equipment')

    if not equipment_id:
        messages.error(request, 'Please select equipment to book.')
        return redirect('rent:equipment_list')

    equipment_obj = get_object_or_404(Equipment, pk=equipment_id, is_available=True)

    if request.method == 'POST':
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        quantity = int(request.POST.get('quantity', 1))
        notes = request.POST.get('notes', '')
        payment_method = request.POST.get('payment_method', 'paystack')

        try:
            from datetime import datetime, date as date_class

            # Check if this is a purchase transaction
            is_purchase = equipment_obj.listing_type == 'for_sale'

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
                    return redirect(request.path + f'?equipment={equipment_id}')

                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()

                # Validate end date is after start date (only for rentals)
                if start >= end:
                    messages.error(request, 'End date must be after start date.')
                    return redirect(request.path + f'?equipment={equipment_id}')

            # Calculate total amount based on duration
            duration_days = (end - start).days

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

                item_name = equipment_obj.name
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
            return redirect(request.path + f'?equipment={equipment_id}')

    # GET request - show booking form
    from datetime import date
    context = {
        'equipment': equipment_obj,
        'today': date.today(),
    }
    return render(request, 'rent/booking_create.html', context)


@login_required
def booking_detail(request, pk):
    """Display booking details"""
    booking = get_object_or_404(
        RentalBooking.objects.select_related('equipment', 'renter'),
        pk=pk
    )

    # Check if user is the renter or the equipment owner
    if booking.renter != request.user and booking.equipment.owner != request.user:
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
    equipment = Equipment.objects.filter(owner=request.user)
    bookings = RentalBooking.objects.filter(
        Q(renter=request.user) | Q(equipment__owner=request.user)
    )

    context = {
        'equipment_count': equipment.count(),
        'renters_count': bookings.filter(status='confirmed').count(),
        'revenue': sum([b.total_amount for b in bookings.filter(status='completed')]),
        'views': sum([e.views_count for e in equipment]),
    }
    return render(request, 'rent/dashboard_pwa.html', context)