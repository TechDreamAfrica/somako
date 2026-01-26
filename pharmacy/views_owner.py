"""
CRUD views for Pharmacy Owners to manage Pharmacies and Medicines
Similar to restaurant owner functionality in food app
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from .models import Pharmacy, Medicine
from .forms import PharmacyForm, MedicineForm


def get_user_subscription(user):
    """Get user's active subscription or None"""
    try:
        subscription = user.subscription
        if subscription.is_active():
            return subscription
    except:
        pass
    return None


def can_create_pharmacy(user):
    """
    Check if user can create a new pharmacy based on subscription.
    Returns (can_create, message, subscription)
    """
    subscription = get_user_subscription(user)
    
    if not subscription:
        # Allow creating one pharmacy without subscription
        current_count = Pharmacy.objects.filter(owner=user).count()
        if current_count >= 1:
            return False, "You need an active subscription to create more pharmacies. Please subscribe to a plan first.", None
        return True, None, None
    
    # Get current pharmacy count for this user
    current_count = Pharmacy.objects.filter(owner=user).count()
    max_allowed = subscription.plan.max_listings
    
    # -1 means unlimited
    if max_allowed == -1:
        return True, None, subscription
    
    if current_count >= max_allowed:
        return False, f"You have reached the maximum number of pharmacies ({max_allowed}) allowed on your {subscription.plan.display_name} plan. Please upgrade to add more pharmacies.", subscription
    
    return True, None, subscription


def can_add_medicine(user):
    """
    Check if user can add medicines based on subscription.
    Requires an active subscription to add medicines.
    Returns (can_add, message, subscription)
    """
    subscription = get_user_subscription(user)
    
    if not subscription:
        return False, "You need an active subscription to add medicines. Please subscribe to a plan first.", None
    
    return True, None, subscription


# ============================================
# Owner Dashboard
# ============================================

@login_required
def owner_dashboard(request):
    """Main dashboard for pharmacy owners"""
    user = request.user
    pharmacies = Pharmacy.objects.filter(owner=user)
    medicines = Medicine.objects.filter(Q(pharmacy__owner=user) | Q(owner=user)).distinct()
    
    context = {
        'pharmacies': pharmacies,
        'total_pharmacies': pharmacies.count(),
        'active_pharmacies': pharmacies.filter(status='active').count(),
        'medicines': medicines.order_by('-created_at')[:10],
        'total_medicines': medicines.count(),
        'active_medicines': medicines.filter(is_active=True).count(),
        'low_stock': medicines.filter(stock_quantity__lte=F('low_stock_threshold')).count(),
        'subscription': get_user_subscription(user),
    }
    return render(request, 'pharmacy/owner/dashboard.html', context)


# ============================================
# Pharmacy CRUD Operations
# ============================================

@login_required
def pharmacy_list(request):
    """List all pharmacies owned by the logged-in pharmacy owner"""
    pharmacies = Pharmacy.objects.filter(owner=request.user).order_by('-created_at')
    subscription = get_user_subscription(request.user)
    
    # Calculate remaining slots
    max_allowed = 0
    remaining_slots = 0
    if subscription and subscription.plan:
        max_allowed = subscription.plan.max_listings
        if max_allowed == -1:
            remaining_slots = -1  # Unlimited
        else:
            remaining_slots = max(0, max_allowed - pharmacies.count())
    
    context = {
        'pharmacies': pharmacies,
        'total_pharmacies': pharmacies.count(),
        'active_pharmacies': pharmacies.filter(status='active').count(),
        'subscription': subscription,
        'max_allowed': max_allowed,
        'remaining_slots': remaining_slots,
    }
    return render(request, 'pharmacy/owner/pharmacy_list.html', context)


@login_required
def pharmacy_create(request):
    """Create a new pharmacy"""
    # Check subscription limits
    can_create, error_message, subscription = can_create_pharmacy(request.user)
    
    if not can_create:
        messages.error(request, error_message)
        if not subscription:
            return redirect('accounts:subscription_plans')
        return redirect('pharmacy:owner_pharmacy_list')
    
    if request.method == 'POST':
        form = PharmacyForm(request.POST, request.FILES)
        if form.is_valid():
            pharmacy = form.save(commit=False)
            pharmacy.owner = request.user
            pharmacy.save()
            
            # Update subscription listing count
            if subscription:
                subscription.current_listings_count = Pharmacy.objects.filter(owner=request.user).count()
                subscription.save()
            
            messages.success(request, 'Pharmacy created successfully!')
            return redirect('pharmacy:owner_pharmacy_detail', pk=pharmacy.pk)
    else:
        form = PharmacyForm()

    context = {
        'form': form, 
        'action': 'Create',
        'subscription': subscription,
    }
    return render(request, 'pharmacy/owner/pharmacy_form.html', context)


@login_required
def pharmacy_detail(request, pk):
    """View pharmacy details with medicines"""
    pharmacy = get_object_or_404(Pharmacy, pk=pk, owner=request.user)
    medicines = pharmacy.medicines.all().order_by('-created_at')

    context = {
        'pharmacy': pharmacy,
        'medicines': medicines,
        'total_medicines': medicines.count(),
        'active_medicines': medicines.filter(is_active=True).count(),
        'low_stock': medicines.filter(stock_quantity__lte=F('low_stock_threshold')).count(),
    }
    return render(request, 'pharmacy/owner/pharmacy_detail.html', context)


@login_required
def pharmacy_update(request, pk):
    """Update an existing pharmacy"""
    pharmacy = get_object_or_404(Pharmacy, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = PharmacyForm(request.POST, request.FILES, instance=pharmacy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pharmacy updated successfully!')
            return redirect('pharmacy:owner_pharmacy_detail', pk=pharmacy.pk)
    else:
        form = PharmacyForm(instance=pharmacy)

    context = {'form': form, 'pharmacy': pharmacy, 'action': 'Update'}
    return render(request, 'pharmacy/owner/pharmacy_form.html', context)


@login_required
def pharmacy_delete(request, pk):
    """Delete a pharmacy"""
    pharmacy = get_object_or_404(Pharmacy, pk=pk, owner=request.user)

    if request.method == 'POST':
        pharmacy_name = pharmacy.name
        pharmacy.delete()
        messages.success(request, f'Pharmacy "{pharmacy_name}" deleted successfully!')
        return redirect('pharmacy:owner_pharmacy_list')

    context = {'pharmacy': pharmacy}
    return render(request, 'pharmacy/owner/pharmacy_confirm_delete.html', context)


@login_required
def pharmacy_toggle_status(request, pk):
    """Toggle pharmacy status (active/inactive)"""
    pharmacy = get_object_or_404(Pharmacy, pk=pk, owner=request.user)

    if pharmacy.status == 'active':
        pharmacy.status = 'inactive'
    else:
        pharmacy.status = 'active'

    pharmacy.save()
    messages.success(request, f'Pharmacy status changed to {pharmacy.status}!')
    return redirect('pharmacy:owner_pharmacy_detail', pk=pharmacy.pk)


# ============================================
# Medicine CRUD Operations
# ============================================

@login_required
def medicine_list(request):
    """List all medicines owned by the logged-in pharmacy owner"""
    user_pharmacies = Pharmacy.objects.filter(owner=request.user)
    medicines = Medicine.objects.filter(
        Q(pharmacy__in=user_pharmacies) | Q(owner=request.user)
    ).distinct().order_by('-created_at')
    
    context = {
        'medicines': medicines,
        'total_medicines': medicines.count(),
        'active_medicines': medicines.filter(is_active=True).count(),
        'low_stock': medicines.filter(stock_quantity__lte=F('low_stock_threshold')).count(),
        'pharmacies': user_pharmacies,
    }
    return render(request, 'pharmacy/owner/medicine_list.html', context)


@login_required
def medicine_create(request, pharmacy_pk=None):
    """Create a new medicine"""
    user_pharmacies = Pharmacy.objects.filter(owner=request.user)
    
    if not user_pharmacies.exists():
        messages.warning(request, 'You need to create a pharmacy first before adding medicines.')
        return redirect('pharmacy:owner_pharmacy_create')
    
    # Check subscription before allowing medicine creation
    can_add, message, subscription = can_add_medicine(request.user)
    if not can_add:
        messages.warning(request, message)
        return redirect('accounts:subscription_plans')
    
    # Pre-select pharmacy if provided
    initial = {}
    if pharmacy_pk:
        pharmacy = get_object_or_404(Pharmacy, pk=pharmacy_pk, owner=request.user)
        initial['pharmacy'] = pharmacy
    
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            medicine = form.save(commit=False)
            medicine.owner = request.user
            medicine.save()
            messages.success(request, f'Medicine "{medicine.name}" created successfully!')
            return redirect('pharmacy:owner_medicine_detail', pk=medicine.pk)
    else:
        form = MedicineForm(user=request.user, initial=initial)
    
    return render(request, 'pharmacy/owner/medicine_form.html', {
        'form': form,
        'action': 'Create',
        'pharmacies': user_pharmacies,
    })


@login_required
def medicine_detail(request, pk):
    """View medicine details"""
    user_pharmacies = Pharmacy.objects.filter(owner=request.user)
    medicine = get_object_or_404(
        Medicine,
        Q(pk=pk) & (Q(pharmacy__in=user_pharmacies) | Q(owner=request.user))
    )
    return render(request, 'pharmacy/owner/medicine_detail.html', {'medicine': medicine})


@login_required
def medicine_update(request, pk):
    """Update an existing medicine"""
    user_pharmacies = Pharmacy.objects.filter(owner=request.user)
    medicine = get_object_or_404(
        Medicine,
        Q(pk=pk) & (Q(pharmacy__in=user_pharmacies) | Q(owner=request.user))
    )
    
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES, instance=medicine, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine updated successfully!')
            return redirect('pharmacy:owner_medicine_detail', pk=medicine.pk)
    else:
        form = MedicineForm(instance=medicine, user=request.user)
    
    return render(request, 'pharmacy/owner/medicine_form.html', {
        'form': form,
        'medicine': medicine,
        'action': 'Update'
    })


@login_required
def medicine_delete(request, pk):
    """Delete a medicine"""
    user_pharmacies = Pharmacy.objects.filter(owner=request.user)
    medicine = get_object_or_404(
        Medicine,
        Q(pk=pk) & (Q(pharmacy__in=user_pharmacies) | Q(owner=request.user))
    )
    
    if request.method == 'POST':
        medicine_name = medicine.name
        medicine.delete()
        messages.success(request, f'Medicine "{medicine_name}" deleted successfully!')
        return redirect('pharmacy:owner_medicine_list')
    
    return render(request, 'pharmacy/owner/medicine_confirm_delete.html', {'medicine': medicine})


@login_required
def medicine_toggle_active(request, pk):
    """Toggle medicine active status"""
    user_pharmacies = Pharmacy.objects.filter(owner=request.user)
    medicine = get_object_or_404(
        Medicine,
        Q(pk=pk) & (Q(pharmacy__in=user_pharmacies) | Q(owner=request.user))
    )
    
    medicine.is_active = not medicine.is_active
    medicine.save()
    status = 'active' if medicine.is_active else 'inactive'
    messages.success(request, f'Medicine marked as {status}!')
    return redirect('pharmacy:owner_medicine_detail', pk=medicine.pk)
