"""CRUD views for Drivers to manage Vehicles"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Vehicle
from .forms import VehicleForm


@login_required
def vehicle_list(request):
    """List all vehicles owned by the logged-in driver"""
    vehicles = Vehicle.objects.filter(driver=request.user).order_by('-created_at')
    context = {
        'vehicles': vehicles,
        'total_vehicles': vehicles.count(),
        'active_vehicles': vehicles.filter(is_active=True).count(),
    }
    return render(request, 'ride/driver/vehicle_list.html', context)


@login_required
def vehicle_create(request):
    """Create a new vehicle"""
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.driver = request.user
            vehicle.save()
            messages.success(request, 'Vehicle created successfully!')
            return redirect('ride:vehicle_detail', pk=vehicle.pk)
    else:
        form = VehicleForm()
    return render(request, 'ride/driver/vehicle_form.html', {'form': form, 'action': 'Create'})


@login_required
def vehicle_detail(request, pk):
    """View vehicle details"""
    vehicle = get_object_or_404(Vehicle, pk=pk, driver=request.user)
    return render(request, 'ride/driver/vehicle_detail.html', {'vehicle': vehicle})


@login_required
def vehicle_update(request, pk):
    """Update an existing vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk, driver=request.user)
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vehicle updated successfully!')
            return redirect('ride:vehicle_detail', pk=vehicle.pk)
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'ride/driver/vehicle_form.html', {'form': form, 'vehicle': vehicle, 'action': 'Update'})


@login_required
def vehicle_delete(request, pk):
    """Delete a vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk, driver=request.user)
    if request.method == 'POST':
        vehicle_name = f"{vehicle.make} {vehicle.model}"
        vehicle.delete()
        messages.success(request, f'Vehicle "{vehicle_name}" deleted successfully!')
        return redirect('ride:vehicle_list')
    return render(request, 'ride/driver/vehicle_confirm_delete.html', {'vehicle': vehicle})


@login_required
def vehicle_toggle_active(request, pk):
    """Toggle vehicle active status"""
    vehicle = get_object_or_404(Vehicle, pk=pk, driver=request.user)
    vehicle.is_active = not vehicle.is_active
    vehicle.save()
    status = 'active' if vehicle.is_active else 'inactive'
    messages.success(request, f'Vehicle marked as {status}!')
    return redirect('ride:vehicle_detail', pk=vehicle.pk)


@login_required
def vehicle_set_primary(request, pk):
    """Set a vehicle as primary"""
    vehicle = get_object_or_404(Vehicle, pk=pk, driver=request.user)
    # Unset all other vehicles as primary
    Vehicle.objects.filter(driver=request.user).update(is_primary=False)
    # Set this vehicle as primary
    vehicle.is_primary = True
    vehicle.save()
    messages.success(request, f'Vehicle set as primary!')
    return redirect('ride:vehicle_detail', pk=vehicle.pk)
