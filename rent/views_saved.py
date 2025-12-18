"""
Views for saving/favoriting properties and equipment
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Property, Equipment, SavedProperty, SavedEquipment


@login_required
def toggle_save_property(request, property_id):
    """Save or unsave a property"""
    property_obj = get_object_or_404(Property, pk=property_id)

    # Check if already saved
    saved = SavedProperty.objects.filter(user=request.user, property=property_obj).first()

    if saved:
        # Unsave
        saved.delete()
        is_saved = False
        message = f'Removed "{property_obj.title}" from your saved properties.'
    else:
        # Save
        SavedProperty.objects.create(user=request.user, property=property_obj)
        is_saved = True
        message = f'Saved "{property_obj.title}" to your favorites!'

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_saved': is_saved,
            'message': message
        })

    # Regular request - show message and redirect back
    if is_saved:
        messages.success(request, message)
    else:
        messages.info(request, message)

    return redirect(request.META.get('HTTP_REFERER', 'rent:property_detail', kwargs={'pk': property_id}))


@login_required
def toggle_save_equipment(request, equipment_id):
    """Save or unsave equipment"""
    equipment_obj = get_object_or_404(Equipment, pk=equipment_id)

    # Check if already saved
    saved = SavedEquipment.objects.filter(user=request.user, equipment=equipment_obj).first()

    if saved:
        # Unsave
        saved.delete()
        is_saved = False
        message = f'Removed "{equipment_obj.name}" from your saved equipment.'
    else:
        # Save
        SavedEquipment.objects.create(user=request.user, equipment=equipment_obj)
        is_saved = True
        message = f'Saved "{equipment_obj.name}" to your favorites!'

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_saved': is_saved,
            'message': message
        })

    # Regular request - show message and redirect back
    if is_saved:
        messages.success(request, message)
    else:
        messages.info(request, message)

    return redirect(request.META.get('HTTP_REFERER', 'rent:equipment_detail', kwargs={'pk': equipment_id}))


@login_required
def saved_properties(request):
    """View all saved properties"""
    saved = SavedProperty.objects.filter(user=request.user).select_related('property', 'property__owner')

    context = {
        'saved_properties': saved,
        'page_title': 'My Saved Properties'
    }

    return render(request, 'rent/saved_properties.html', context)


@login_required
def saved_equipment(request):
    """View all saved equipment"""
    saved = SavedEquipment.objects.filter(user=request.user).select_related('equipment', 'equipment__owner')

    context = {
        'saved_equipment': saved,
        'page_title': 'My Saved Equipment'
    }

    return render(request, 'rent/saved_equipment.html', context)


@login_required
def saved_items(request):
    """View all saved properties and equipment"""
    saved_props = SavedProperty.objects.filter(user=request.user).select_related('property', 'property__owner')
    saved_equip = SavedEquipment.objects.filter(user=request.user).select_related('equipment', 'equipment__owner')

    context = {
        'saved_properties': saved_props,
        'saved_equipment': saved_equip,
        'page_title': 'My Saved Items'
    }

    return render(request, 'rent/saved_items.html', context)
