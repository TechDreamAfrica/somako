"""CRUD views for Pharmacy Owners to manage Medicines"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from .models import Medicine
from .forms import MedicineForm


@login_required
def medicine_list(request):
    """List all medicines owned by the logged-in pharmacy owner"""
    medicines = Medicine.objects.filter(owner=request.user).order_by('-created_at')
    context = {
        'medicines': medicines,
        'total_medicines': medicines.count(),
        'active_medicines': medicines.filter(is_active=True).count(),
        'low_stock': medicines.filter(stock_quantity__lte=F('low_stock_threshold')).count(),
    }
    return render(request, 'pharmacy/owner/medicine_list.html', context)


@login_required
def medicine_create(request):
    """Create a new medicine"""
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES)
        if form.is_valid():
            medicine = form.save(commit=False)
            medicine.owner = request.user
            medicine.save()
            messages.success(request, 'Medicine created successfully!')
            return redirect('pharmacy:medicine_detail', pk=medicine.pk)
    else:
        form = MedicineForm()
    return render(request, 'pharmacy/owner/medicine_form.html', {'form': form, 'action': 'Create'})


@login_required
def medicine_detail(request, pk):
    """View medicine details"""
    medicine = get_object_or_404(Medicine, pk=pk, owner=request.user)
    return render(request, 'pharmacy/owner/medicine_detail.html', {'medicine': medicine})


@login_required
def medicine_update(request, pk):
    """Update an existing medicine"""
    medicine = get_object_or_404(Medicine, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine updated successfully!')
            return redirect('pharmacy:medicine_detail', pk=medicine.pk)
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'pharmacy/owner/medicine_form.html', {'form': form, 'medicine': medicine, 'action': 'Update'})


@login_required
def medicine_delete(request, pk):
    """Delete a medicine"""
    medicine = get_object_or_404(Medicine, pk=pk, owner=request.user)
    if request.method == 'POST':
        medicine_name = medicine.name
        medicine.delete()
        messages.success(request, f'Medicine "{medicine_name}" deleted successfully!')
        return redirect('pharmacy:medicine_list')
    return render(request, 'pharmacy/owner/medicine_confirm_delete.html', {'medicine': medicine})


@login_required
def medicine_toggle_active(request, pk):
    """Toggle medicine active status"""
    medicine = get_object_or_404(Medicine, pk=pk, owner=request.user)
    medicine.is_active = not medicine.is_active
    medicine.save()
    status = 'active' if medicine.is_active else 'inactive'
    messages.success(request, f'Medicine marked as {status}!')
    return redirect('pharmacy:medicine_detail', pk=medicine.pk)
