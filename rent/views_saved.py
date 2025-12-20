"""
Views for saving/favoriting equipment
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Equipment, SavedEquipment



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
    """View all saved equipment"""
    saved_equip = SavedEquipment.objects.filter(user=request.user).select_related('equipment', 'equipment__owner')

    context = {
        'saved_equipment': saved_equip,
        'page_title': 'My Saved Items'
    }

    return render(request, 'rent/saved_items.html', context)
