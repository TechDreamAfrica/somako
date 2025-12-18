"""
CRUD views for Landlords to manage Properties and Rooms
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Property, Room, PropertyImage
from .forms import PropertyForm, RoomForm, PropertyImageForm


# ============================================
# Property CRUD Operations
# ============================================

@login_required
def property_list(request):
    """List all properties owned by the logged-in landlord"""
    properties = Property.objects.filter(owner=request.user).order_by('-created_at')
    context = {
        'properties': properties,
        'total_properties': properties.count(),
        'available_properties': properties.filter(is_available=True).count(),
    }
    return render(request, 'rent/landlord/property_list.html', context)


@login_required
def property_create(request):
    """Create a new property"""
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            property = form.save(commit=False)
            property.owner = request.user
            property.save()
            messages.success(request, 'Property created successfully!')
            return redirect('rent:property_detail', pk=property.pk)
    else:
        form = PropertyForm()

    context = {'form': form, 'action': 'Create'}
    return render(request, 'rent/landlord/property_form.html', context)


@login_required
def property_detail(request, pk):
    """View property details with rooms"""
    property = get_object_or_404(Property, pk=pk, owner=request.user)
    rooms = property.rooms.all()
    images = property.images.all()

    context = {
        'property': property,
        'rooms': rooms,
        'images': images,
        'total_rooms': rooms.count(),
        'available_rooms': rooms.filter(is_available=True).count(),
    }
    return render(request, 'rent/landlord/property_detail.html', context)


@login_required
def property_update(request, pk):
    """Update an existing property"""
    property = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property)
        if form.is_valid():
            form.save()
            messages.success(request, 'Property updated successfully!')
            return redirect('rent:property_detail', pk=property.pk)
    else:
        form = PropertyForm(instance=property)

    context = {'form': form, 'property': property, 'action': 'Update'}
    return render(request, 'rent/landlord/property_form.html', context)


@login_required
def property_delete(request, pk):
    """Delete a property"""
    property = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        property_title = property.title
        property.delete()
        messages.success(request, f'Property "{property_title}" deleted successfully!')
        return redirect('rent:property_list')

    context = {'property': property}
    return render(request, 'rent/landlord/property_confirm_delete.html', context)


@login_required
def property_toggle_availability(request, pk):
    """Toggle property availability status"""
    property = get_object_or_404(Property, pk=pk, owner=request.user)
    property.is_available = not property.is_available
    property.save()

    status = 'available' if property.is_available else 'unavailable'
    messages.success(request, f'Property marked as {status}!')

    return redirect('rent:property_detail', pk=property.pk)


# ============================================
# Room CRUD Operations
# ============================================

@login_required
def room_create(request, property_pk):
    """Create a new room for a property"""
    property = get_object_or_404(Property, pk=property_pk, owner=request.user)

    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            room = form.save(commit=False)
            room.property = property
            room.save()
            messages.success(request, f'Room "{room.name}" created successfully!')
            return redirect('rent:property_detail', pk=property.pk)
    else:
        form = RoomForm()

    context = {
        'form': form,
        'property': property,
        'action': 'Create',
    }
    return render(request, 'rent/landlord/room_form.html', context)


@login_required
def room_update(request, pk):
    """Update an existing room"""
    room = get_object_or_404(Room, pk=pk, property__owner=request.user)

    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, f'Room "{room.name}" updated successfully!')
            return redirect('rent:property_detail', pk=room.property.pk)
    else:
        form = RoomForm(instance=room)

    context = {
        'form': form,
        'room': room,
        'property': room.property,
        'action': 'Update',
    }
    return render(request, 'rent/landlord/room_form.html', context)


@login_required
def room_delete(request, pk):
    """Delete a room"""
    room = get_object_or_404(Room, pk=pk, property__owner=request.user)
    property_pk = room.property.pk

    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f'Room "{room_name}" deleted successfully!')
        return redirect('rent:property_detail', pk=property_pk)

    context = {'room': room, 'property': room.property}
    return render(request, 'rent/landlord/room_confirm_delete.html', context)


@login_required
def room_toggle_availability(request, pk):
    """Toggle room availability status"""
    room = get_object_or_404(Room, pk=pk, property__owner=request.user)
    room.is_available = not room.is_available
    room.save()

    status = 'available' if room.is_available else 'unavailable'
    messages.success(request, f'Room marked as {status}!')

    return redirect('rent:property_detail', pk=room.property.pk)


# ============================================
# Property Image Management
# ============================================

@login_required
def property_image_add(request, property_pk):
    """Add images to a property"""
    property = get_object_or_404(Property, pk=property_pk, owner=request.user)

    if request.method == 'POST':
        form = PropertyImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.property = property
            image.save()
            messages.success(request, 'Image added successfully!')
            return redirect('rent:property_detail', pk=property.pk)
    else:
        form = PropertyImageForm()

    context = {'form': form, 'property': property}
    return render(request, 'rent/landlord/property_image_form.html', context)


@login_required
def property_image_delete(request, pk):
    """Delete a property image"""
    image = get_object_or_404(PropertyImage, pk=pk, property__owner=request.user)
    property_pk = image.property.pk

    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully!')
        return redirect('rent:property_detail', pk=property_pk)

    context = {'image': image, 'property': image.property}
    return render(request, 'rent/landlord/property_image_confirm_delete.html', context)
