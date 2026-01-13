"""
CRUD views for Landlords/Equipment Owners to manage Equipment and Bookings
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Equipment, EquipmentCategory, EquipmentImage, RentalBooking
from .forms import EquipmentForm


def has_owner_role(user):
    """Check if user has landlord or equipment_owner role"""
    return user.has_role('landlord') or user.has_role('equipment_owner')


# ============================================
# Equipment CRUD Operations
# ============================================

@login_required
def equipment_list(request):
    """List all equipment owned by the logged-in user"""
    if not has_owner_role(request.user):
        messages.error(request, 'You need to be a landlord or equipment owner to access this page.')
        return redirect('rent:equipment_list')
    
    equipment_items = Equipment.objects.filter(owner=request.user).order_by('-created_at')
    
    # Filter by availability
    availability = request.GET.get('availability')
    if availability == 'available':
        equipment_items = equipment_items.filter(is_available=True)
    elif availability == 'unavailable':
        equipment_items = equipment_items.filter(is_available=False)
    
    paginator = Paginator(equipment_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_equipment': equipment_items.count(),
        'available_count': equipment_items.filter(is_available=True).count(),
        'unavailable_count': equipment_items.filter(is_available=False).count(),
    }
    return render(request, 'rent/owner/equipment_list.html', context)


@login_required
def equipment_create(request):
    """Create new equipment"""
    if not has_owner_role(request.user):
        messages.error(request, 'You need to be a landlord or equipment owner to add equipment.')
        return redirect('rent:equipment_list')
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.owner = request.user
            equipment.save()
            messages.success(request, 'Equipment added successfully!')
            return redirect('rent:owner_equipment_detail', pk=equipment.pk)
    else:
        form = EquipmentForm()
    
    context = {
        'form': form,
        'action': 'Add',
        'categories': EquipmentCategory.objects.all(),
    }
    return render(request, 'rent/owner/equipment_form.html', context)


@login_required
def equipment_detail(request, pk):
    """View equipment details"""
    equipment = get_object_or_404(Equipment, pk=pk, owner=request.user)
    
    # Get bookings for this equipment
    bookings = RentalBooking.objects.filter(equipment=equipment).order_by('-created_at')[:10]
    
    context = {
        'equipment': equipment,
        'bookings': bookings,
        'total_bookings': RentalBooking.objects.filter(equipment=equipment).count(),
        'active_bookings': RentalBooking.objects.filter(equipment=equipment, status__in=['pending', 'confirmed', 'active']).count(),
    }
    return render(request, 'rent/owner/equipment_detail.html', context)


@login_required
def equipment_update(request, pk):
    """Update existing equipment"""
    equipment = get_object_or_404(Equipment, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipment updated successfully!')
            return redirect('rent:owner_equipment_detail', pk=equipment.pk)
    else:
        form = EquipmentForm(instance=equipment)
    
    context = {
        'form': form,
        'equipment': equipment,
        'action': 'Update',
        'categories': EquipmentCategory.objects.all(),
    }
    return render(request, 'rent/owner/equipment_form.html', context)


@login_required
def equipment_delete(request, pk):
    """Delete equipment"""
    equipment = get_object_or_404(Equipment, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        equipment_name = equipment.name
        equipment.delete()
        messages.success(request, f'Equipment "{equipment_name}" deleted successfully!')
        return redirect('rent:owner_equipment_list')
    
    context = {'equipment': equipment}
    return render(request, 'rent/owner/equipment_confirm_delete.html', context)


@login_required
def equipment_toggle_availability(request, pk):
    """Toggle equipment availability"""
    equipment = get_object_or_404(Equipment, pk=pk, owner=request.user)
    
    equipment.is_available = not equipment.is_available
    equipment.save()
    
    status = 'available' if equipment.is_available else 'unavailable'
    messages.success(request, f'Equipment is now {status}.')
    
    # Redirect back to the referring page or equipment list
    next_url = request.GET.get('next', request.META.get('HTTP_REFERER'))
    if next_url:
        return redirect(next_url)
    return redirect('rent:owner_equipment_list')


# ============================================
# Booking Management
# ============================================

@login_required
def booking_list(request):
    """List all bookings for owner's equipment"""
    if not has_owner_role(request.user):
        messages.error(request, 'You need to be a landlord or equipment owner to manage bookings.')
        return redirect('rent:equipment_list')
    
    bookings = RentalBooking.objects.filter(
        equipment__owner=request.user
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    paginator = Paginator(bookings, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'total_bookings': bookings.count(),
        'pending_count': bookings.filter(status='pending').count(),
        'confirmed_count': bookings.filter(status='confirmed').count(),
        'active_count': bookings.filter(status='active').count(),
    }
    return render(request, 'rent/owner/booking_list.html', context)


@login_required
def booking_detail(request, pk):
    """View booking details (owner perspective)"""
    booking = get_object_or_404(RentalBooking, pk=pk, equipment__owner=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'rent/owner/booking_detail.html', context)


@login_required
def booking_update_status(request, pk):
    """Update booking status"""
    booking = get_object_or_404(RentalBooking, pk=pk, equipment__owner=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = ['pending', 'confirmed', 'active', 'completed', 'cancelled']
        
        if new_status in valid_statuses:
            booking.status = new_status
            booking.save()
            messages.success(request, f'Booking status updated to {new_status}!')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('rent:owner_booking_detail', pk=booking.pk)
