"""
Rider/Driver-specific views for Express PWA
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import (
    DeliveryRequest, DeliveryStatusUpdate, DeliveryDriverProfile,
    ExpressOrder, ExpressOrderItem
)
from .views import send_delivery_sms
from utils.sms_utils import send_custom_sms
from core.pwa_decorators import pwa_login_required


@login_required
def become_delivery_driver(request):
    """
    Registration page for users to become delivery drivers
    """
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'express'

    # Check if user already has a driver profile
    if hasattr(request.user, 'delivery_driver_profile'):
        profile = request.user.delivery_driver_profile
        messages.info(request, f'You already have a driver profile. Status: {profile.get_status_display()}')
        return redirect('express_pwa:rider_dashboard')

    if request.method == 'POST':
        try:
            # Create driver profile
            profile = DeliveryDriverProfile.objects.create(
                user=request.user,
                driver_license_number=request.POST.get('license_number').upper(),
                license_expiry_date=request.POST.get('license_expiry'),
                mobile_money_number=request.POST.get('mobile_money_number', ''),
                mobile_money_provider=request.POST.get('mobile_money_provider', ''),
                bank_name=request.POST.get('bank_name', ''),
                account_number=request.POST.get('account_number', ''),
                account_holder_name=request.POST.get('account_holder_name', ''),
                status='PENDING'
            )

            # Handle file uploads
            if 'license_document' in request.FILES:
                profile.license_document = request.FILES['license_document']
            if 'national_id' in request.FILES:
                profile.national_id = request.FILES['national_id']
            if 'profile_photo' in request.FILES:
                profile.profile_photo = request.FILES['profile_photo']

            profile.save()

            # Add delivery_driver role
            if not request.user.has_role('delivery_driver'):
                request.user.add_role('delivery_driver')
                request.user.save()

            messages.success(request, 'Your driver application has been submitted! We will review it shortly.')
            return redirect('express_pwa:rider_dashboard')

        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')
            return render(request, 'express_pwa/rider/become_driver.html')

    return render(request, 'express_pwa/rider/become_driver.html')


@pwa_login_required(pwa_app='express')
def rider_dashboard(request):
    """
    Main dashboard for delivery riders
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'You need to apply as a delivery driver first.')
        return redirect('express_pwa:become_driver')

    try:
        driver_profile = request.user.delivery_driver_profile
    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Driver profile not found. Please apply again.')
        return redirect('express_pwa:become_driver')

    # Check if driver is approved
    if driver_profile.status != 'APPROVED':
        context = {
            'driver_profile': driver_profile,
            'pending_approval': True
        }
        return render(request, 'express_pwa/rider/dashboard.html', context)

    today = timezone.now().date()
    week_ago = timezone.now() - timedelta(days=7)

    # Count both DeliveryRequests and ExpressOrderItems
    delivery_requests_completed_today = DeliveryRequest.objects.filter(
        driver=request.user,
        status='delivered',
        delivery_time__date=today
    ).count()
    
    order_items_completed_today = ExpressOrderItem.objects.filter(
        driver=request.user,
        status='delivered',
        delivery_time__date=today
    ).count()

    # Statistics
    stats = {
        'total_deliveries': driver_profile.total_deliveries,
        'average_rating': driver_profile.average_rating,
        'is_online': driver_profile.availability == 'ONLINE',
        'status': driver_profile.status,
        'availability': driver_profile.availability,

        # Today's stats (both DeliveryRequest and ExpressOrderItem)
        'today_completed': delivery_requests_completed_today + order_items_completed_today,

        'today_earnings': sum([
            (delivery.final_cost or delivery.estimated_cost or Decimal('0.00')) * Decimal('0.70')
            for delivery in DeliveryRequest.objects.filter(
                driver=request.user,
                status='delivered',
                delivery_time__date=today
            )
        ]) + sum([
            (item.final_cost or item.estimated_cost or Decimal('0.00')) * Decimal('0.70')
            for item in ExpressOrderItem.objects.filter(
                driver=request.user,
                status='delivered',
                delivery_time__date=today
            )
        ]),

        # Week stats (both DeliveryRequest and ExpressOrderItem)
        'week_deliveries': DeliveryRequest.objects.filter(
            driver=request.user,
            status='delivered',
            delivery_time__gte=week_ago
        ).count() + ExpressOrderItem.objects.filter(
            driver=request.user,
            status='delivered',
            delivery_time__gte=week_ago
        ).count(),

        'week_earnings': sum([
            (delivery.final_cost or delivery.estimated_cost or Decimal('0.00')) * Decimal('0.70')
            for delivery in DeliveryRequest.objects.filter(
                driver=request.user,
                status='delivered',
                delivery_time__gte=week_ago
            )
        ]) + sum([
            (item.final_cost or item.estimated_cost or Decimal('0.00')) * Decimal('0.70')
            for item in ExpressOrderItem.objects.filter(
                driver=request.user,
                status='delivered',
                delivery_time__gte=week_ago
            )
        ]),

        # Current stats (both DeliveryRequest and ExpressOrderItem)
        'active_count': DeliveryRequest.objects.filter(
            driver=request.user,
            status__in=['assigned', 'picked_up', 'in_transit']
        ).count() + ExpressOrderItem.objects.filter(
            driver=request.user,
            status__in=['assigned', 'picked_up', 'in_transit']
        ).count(),
        'available_count': DeliveryRequest.objects.filter(
            status='confirmed',
            driver__isnull=True
        ).count(),
    }

    # Active delivery (current one in progress) - check both types
    active_delivery = DeliveryRequest.objects.filter(
        driver=request.user,
        status__in=['assigned', 'picked_up', 'in_transit']
    ).first()
    
    # Also check for active ExpressOrders
    active_order = ExpressOrder.objects.filter(
        driver=request.user,
        status__in=['assigned', 'in_progress']
    ).first()

    # Recent completed deliveries (both types)
    recent_completed = DeliveryRequest.objects.filter(
        driver=request.user,
        status='delivered'
    ).order_by('-delivery_time')[:5]

    # Pending deliveries (assigned but not picked up yet) - include both types
    pending_deliveries = DeliveryRequest.objects.filter(
        driver=request.user,
        status='assigned'
    ).order_by('-created_at')
    
    # Pending orders (assigned but not started)
    pending_orders = ExpressOrder.objects.filter(
        driver=request.user,
        status='assigned'
    ).prefetch_related('items').order_by('-assigned_at')

    context = {
        'driver_profile': driver_profile,
        'stats': stats,
        'active_delivery': active_delivery,
        'active_order': active_order,
        'recent_completed': recent_completed,
        'pending_deliveries': pending_deliveries,
        'pending_orders': pending_orders,
        'pending_approval': False
    }

    return render(request, 'express_pwa/rider/dashboard.html', context)


@pwa_login_required(pwa_app='express')
def available_deliveries(request):
    """
    Show all orders assigned to the current driver (all statuses for tracking purposes)
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')

    try:
        driver_profile = request.user.delivery_driver_profile
        if driver_profile.status != 'APPROVED':
            messages.warning(request, 'Your driver profile is pending approval.')
            return redirect('express_pwa:rider_dashboard')
    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Please complete your driver registration first.')
        return redirect('express_pwa:become_driver')

    # Filter options
    urgency_filter = request.GET.get('urgency', '')
    package_type_filter = request.GET.get('package_type', '')
    status_filter = request.GET.get('status', '')

    # Get ALL orders that have items assigned to this driver (regardless of status for tracking)
    from django.db.models import Q, Prefetch
    
    # Build filter conditions for items within orders
    item_filters = Q(driver=request.user)
    if urgency_filter:
        item_filters &= Q(urgency=urgency_filter)
    if package_type_filter:
        item_filters &= Q(package_type=package_type_filter)
    if status_filter:
        item_filters &= Q(status=status_filter)

    # Get orders that have items matching our criteria
    assigned_orders = ExpressOrder.objects.filter(
        items__driver=request.user
    ).distinct().select_related('sender').prefetch_related(
        Prefetch('items', queryset=ExpressOrderItem.objects.filter(item_filters).select_related('pickup_region', 'delivery_region'))
    ).order_by('-created_at')

    # Filter out orders that have no items after filtering
    filtered_orders = []
    for order in assigned_orders:
        matching_items = [item for item in order.items.all() if item.driver == request.user]
        if urgency_filter:
            matching_items = [item for item in matching_items if item.urgency == urgency_filter]
        if package_type_filter:
            matching_items = [item for item in matching_items if item.package_type == package_type_filter]
        if status_filter:
            matching_items = [item for item in matching_items if item.status == status_filter]
        
        if matching_items:
            # Add the filtered items as an attribute for easy access in template
            order.driver_items = matching_items
            # Calculate order-level stats
            order.total_items = len(matching_items)
            order.pending_items = len([item for item in matching_items if item.status == 'pending'])
            order.in_progress_items = len([item for item in matching_items if item.status in ['assigned', 'picked_up', 'in_transit']])
            order.delivered_items = len([item for item in matching_items if item.status == 'delivered'])
            order.total_earnings = sum((item.final_cost or item.estimated_cost or 0) for item in matching_items if item.status == 'delivered')
            filtered_orders.append(order)

    # Get status counts for filtering
    status_counts = {}
    all_items = ExpressOrderItem.objects.filter(driver=request.user)
    for choice_value, choice_label in ExpressOrderItem.STATUS_CHOICES:
        count = all_items.filter(status=choice_value).count()
        if count > 0:
            status_counts[choice_value] = {'label': choice_label, 'count': count}

    context = {
        'assigned_orders': filtered_orders,
        'urgency_filter': urgency_filter,
        'package_type_filter': package_type_filter,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'urgency_choices': DeliveryRequest.URGENCY_LEVELS,
        'package_type_choices': DeliveryRequest.PACKAGE_TYPES,
        'status_choices': ExpressOrderItem.STATUS_CHOICES,
        'total_assigned': all_items.count(),
        'total_orders': len(filtered_orders),
    }

    return render(request, 'express_pwa/rider/available_deliveries.html', context)


@pwa_login_required(pwa_app='express')
def accept_delivery(request, request_id):
    """
    Accept an available delivery
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')

    try:
        driver_profile = request.user.delivery_driver_profile

        # Validate driver can accept deliveries
        if not driver_profile.is_available():
            messages.error(request, 'You must be online and approved to accept deliveries.')
            return redirect('express_pwa:available_deliveries')

        # Check if driver already has an active delivery
        has_active = DeliveryRequest.objects.filter(
            driver=request.user,
            status__in=['assigned', 'picked_up', 'in_transit']
        ).exists()

        if has_active:
            messages.warning(request, 'You already have an active delivery. Complete it first.')
            return redirect('express_pwa:rider_dashboard')

    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('express_pwa:become_driver')

    delivery = get_object_or_404(
        DeliveryRequest,
        id=request_id,
        status='confirmed',
        driver__isnull=True
    )

    # Assign delivery to driver
    delivery.driver = request.user
    delivery.status = 'assigned'
    delivery.save()

    # Update driver availability
    driver_profile.availability = 'ON_DELIVERY'
    driver_profile.save(update_fields=['availability'])

    # Create status update
    DeliveryStatusUpdate.objects.create(
        delivery=delivery,
        status='assigned',
        notes=f'Delivery accepted by {request.user.get_full_name()}',
        updated_by=request.user
    )

    # Send SMS notification to sender
    send_delivery_sms(
        phone=delivery.sender.phone_number if hasattr(delivery.sender, 'phone_number') else '',
        message=f'Good news! Driver {request.user.get_full_name()} has been assigned to your delivery {delivery.tracking_number}. Track: somako.com/track/{delivery.tracking_number}'
    )

    messages.success(request, f'You have accepted delivery {delivery.tracking_number}!')
    return redirect('express_pwa:delivery_detail_rider', delivery_id=delivery.id)


@pwa_login_required(pwa_app='express')
def my_deliveries(request):
    """
    Show all deliveries assigned to the rider
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')

    status_filter = request.GET.get('status', '')

    # Get all delivery items (from orders) assigned to this driver
    delivery_items = ExpressOrderItem.objects.filter(
        driver=request.user
    ).select_related('order', 'order__sender', 'pickup_region', 'delivery_region')

    if status_filter:
        delivery_items = delivery_items.filter(status=status_filter)

    delivery_items = delivery_items.order_by('-created_at')

    context = {
        'delivery_items': delivery_items,
        'status_filter': status_filter,
        'status_choices': ExpressOrderItem.STATUS_CHOICES,
    }

    return render(request, 'express_pwa/rider/my_deliveries.html', context)


@pwa_login_required(pwa_app='express')
def delivery_detail_rider(request, delivery_id):
    """
    Detailed view of delivery for rider with action buttons
    """
    delivery = get_object_or_404(
        DeliveryRequest,
        id=delivery_id,
        driver=request.user
    )

    status_updates = delivery.status_updates.all().order_by('-created_at')

    # Determine what actions are available
    can_pickup = delivery.status == 'assigned'
    can_mark_in_transit = delivery.status == 'picked_up'
    can_complete = delivery.status == 'in_transit'

    context = {
        'delivery': delivery,
        'status_updates': status_updates,
        'can_pickup': can_pickup,
        'can_mark_in_transit': can_mark_in_transit,
        'can_complete': can_complete,
    }

    return render(request, 'express_pwa/rider/delivery_detail.html', context)


@pwa_login_required(pwa_app='express')
def update_delivery_status_rider(request, delivery_id):
    """
    Update delivery status (pickup, in-transit, etc.)
    """
    delivery = get_object_or_404(DeliveryRequest, id=delivery_id, driver=request.user)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        # Special handling for delivery completion - redirect to signature capture
        if new_status == 'delivered' and delivery.status == 'in_transit':
            return redirect('express_pwa:rider_capture_signature', delivery_id=delivery.id)

        # Validate status transition
        valid_transitions = {
            'assigned': ['picked_up'],
            'picked_up': ['in_transit'],
            'in_transit': ['delivered'],  # Allow direct to delivered for other cases
        }

        if delivery.status not in valid_transitions or new_status not in valid_transitions[delivery.status]:
            messages.error(request, 'Invalid status transition.')
            return redirect('express_pwa:delivery_detail_rider', delivery_id=delivery.id)

        # Update delivery status
        delivery.status = new_status

        # Update timestamps
        if new_status == 'picked_up':
            delivery.pickup_time = timezone.now()
        elif new_status == 'delivered':
            delivery.delivery_time = timezone.now()

        delivery.save()

        # Create status update record
        DeliveryStatusUpdate.objects.create(
            delivery=delivery,
            status=new_status,
            notes=notes,
            updated_by=request.user
        )

        # Send SMS notification
        status_messages = {
            'picked_up': f'Your package {delivery.tracking_number} has been picked up by {request.user.get_full_name()}.',
            'in_transit': f'Your package {delivery.tracking_number} is now in transit to {delivery.delivery_address[:30]}...',
            'delivered': f'Your package {delivery.tracking_number} has been delivered!',
        }

        if new_status in status_messages:
            send_delivery_sms(
                phone=delivery.sender.phone_number if hasattr(delivery.sender, 'phone_number') else '',
                message=status_messages[new_status]
            )

        messages.success(request, f'Delivery status updated to {delivery.get_status_display()}')
        return redirect('express_pwa:delivery_detail_rider', delivery_id=delivery.id)

    return redirect('express_pwa:delivery_detail_rider', delivery_id=delivery.id)


@pwa_login_required(pwa_app='express')
def toggle_availability(request):
    """
    Toggle driver online/offline status
    """
    try:
        driver_profile = request.user.delivery_driver_profile

        if driver_profile.availability == 'ONLINE':
            driver_profile.availability = 'OFFLINE'
            messages.success(request, 'You are now offline.')
        elif driver_profile.availability == 'OFFLINE':
            # Check if driver has active deliveries
            has_active = DeliveryRequest.objects.filter(
                driver=request.user,
                status__in=['assigned', 'picked_up', 'in_transit']
            ).exists()

            if has_active:
                driver_profile.availability = 'ON_DELIVERY'
            else:
                driver_profile.availability = 'ONLINE'

            messages.success(request, 'You are now online and ready to accept deliveries!')
        elif driver_profile.availability == 'ON_DELIVERY':
            messages.warning(request, 'Complete your current delivery before going offline.')
            return redirect('express_pwa:rider_dashboard')

        driver_profile.save(update_fields=['availability'])

    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('express_pwa:become_driver')

    return redirect('express_pwa:rider_dashboard')


@pwa_login_required(pwa_app='express')
def rider_earnings(request):
    """
    Show rider earnings and payment history
    """
    try:
        driver_profile = request.user.delivery_driver_profile
    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('express_pwa:become_driver')

    today = timezone.now().date()
    week_ago = timezone.now() - timedelta(days=7)
    month_ago = timezone.now() - timedelta(days=30)

    # Calculate earnings from delivered deliveries
    # Driver gets 70% of the delivery fee
    DRIVER_COMMISSION_RATE = Decimal('0.70')
    
    def calculate_earnings(order_items):
        total_revenue = Decimal('0.00')
        total_commission = Decimal('0.00')
        count = 0
        
        for item in order_items:
            item_cost = item.estimated_cost or Decimal('0.00')
            driver_earning = item_cost * DRIVER_COMMISSION_RATE
            total_revenue += item_cost
            total_commission += driver_earning
            count += 1
            
        return {
            'total': total_commission,
            'count': count,
            'revenue': total_revenue
        }

    # Get delivered order items for different periods
    today_items = ExpressOrderItem.objects.filter(
        driver=request.user,
        status='delivered',
        delivery_time__date=today
    )
    
    week_items = ExpressOrderItem.objects.filter(
        driver=request.user,
        status='delivered',
        delivery_time__gte=week_ago
    )
    
    month_items = ExpressOrderItem.objects.filter(
        driver=request.user,
        status='delivered',
        delivery_time__gte=month_ago
    )
    
    all_items = ExpressOrderItem.objects.filter(
        driver=request.user,
        status='delivered'
    )

    # Calculate earnings stats
    earnings_stats = {
        'today': calculate_earnings(today_items),
        'week': calculate_earnings(week_items),
        'month': calculate_earnings(month_items),
        'total': calculate_earnings(all_items),
        'commission_rate': DRIVER_COMMISSION_RATE * 100,  # For display as percentage
    }

    # Get recent delivered order items for display
    recent_items = ExpressOrderItem.objects.filter(
        driver=request.user,
        status='delivered'
    ).order_by('-created_at')[:20]
    
    # Add commission calculation to each item
    for item in recent_items:
        item_cost = item.estimated_cost or Decimal('0.00')
        item.driver_commission = item_cost * DRIVER_COMMISSION_RATE

    # Calculate additional performance metrics
    total_completed = all_items.count()
    total_requests = ExpressOrderItem.objects.filter(driver=request.user).count()
    
    # Calculate success rate
    success_rate = (total_completed / total_requests * 100) if total_requests > 0 else 0
    
    # Get pending payouts (this would be from a payout model in production)
    pending_payout_amount = Decimal('0.00')  # Placeholder
    
    # Calculate average delivery time (placeholder for now)
    avg_delivery_time = 0  # Would calculate from pickup to delivery times
    
    # Get total distance (placeholder)
    total_distance = 0  # Would calculate from delivery routes

    context = {
        'driver_profile': driver_profile,
        'earnings_stats': earnings_stats,
        'recent_items': recent_items,
        'commission_rate': DRIVER_COMMISSION_RATE * 100,
        'success_rate': success_rate,
        'pending_payout_amount': pending_payout_amount,
        'avg_delivery_time': avg_delivery_time,
        'total_distance': total_distance,
        'total_completed_deliveries': total_completed,
    }

    return render(request, 'express_pwa/rider/earnings.html', context)


@pwa_login_required(pwa_app='express')
def request_payout(request):
    """
    Handle payout requests for delivery drivers
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('express_pwa:rider_earnings')
    
    try:
        driver_profile = request.user.delivery_driver_profile
    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('express_pwa:become_driver')
    
    # Validate payment method exists
    if not driver_profile.mobile_money_number:
        messages.error(request, 'Please add a mobile money number in your profile first.')
        return redirect('express_pwa:rider_profile')
    
    # Get payout amount
    try:
        payout_amount = Decimal(str(request.POST.get('amount', '0')))
    except (ValueError, TypeError):
        messages.error(request, 'Invalid payout amount.')
        return redirect('express_pwa:rider_earnings')
    
    # Validate minimum payout amount
    if payout_amount < Decimal('10.00'):
        messages.error(request, 'Minimum payout amount is GH₵10.00')
        return redirect('express_pwa:rider_earnings')
    
    # Calculate available earnings
    DRIVER_COMMISSION_RATE = Decimal('0.70')
    completed_deliveries = DeliveryRequest.objects.filter(
        driver=request.user,
        status='delivered'
    )
    
    total_earnings = Decimal('0.00')
    for delivery in completed_deliveries:
        delivery_cost = delivery.final_cost or delivery.estimated_cost or Decimal('0.00')
        driver_earning = delivery_cost * DRIVER_COMMISSION_RATE
        total_earnings += driver_earning
    
    # Check if requested amount is available
    if payout_amount > total_earnings:
        messages.error(request, f'Insufficient balance. Available: GH₵{total_earnings:.2f}')
        return redirect('express_pwa:rider_earnings')
    
    # Create payout request record (for tracking)
    try:
        from datetime import datetime
        
        # For now, we'll create a simple log entry
        # In production, you'd integrate with actual payment gateway
        payout_reference = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}{request.user.id}"
        
        # Here you would integrate with mobile money API
        # For demo purposes, we'll just show a success message
        
        messages.success(
            request, 
            f'Payout request of GH₵{payout_amount:.2f} has been submitted. '
            f'Reference: {payout_reference}. Funds will be sent within 24 hours.'
        )
        
        # Log the payout request
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Payout requested - User: {request.user.id}, Amount: {payout_amount}, Reference: {payout_reference}")
        
    except Exception as e:
        messages.error(request, 'Failed to process payout request. Please try again.')
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Payout error for user {request.user.id}: {str(e)}")
    
    return redirect('express_pwa:rider_earnings')


@pwa_login_required(pwa_app='express')
def rider_profile(request):
    """
    View and edit rider profile
    """
    try:
        driver_profile = request.user.delivery_driver_profile
    except DeliveryDriverProfile.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('express_pwa:become_driver')

    if request.method == 'POST':
        # Update profile fields
        driver_profile.mobile_money_number = request.POST.get('mobile_money_number', '')
        driver_profile.mobile_money_provider = request.POST.get('mobile_money_provider', '')
        driver_profile.bank_name = request.POST.get('bank_name', '')
        driver_profile.account_number = request.POST.get('account_number', '')
        driver_profile.account_holder_name = request.POST.get('account_holder_name', '')

        # Handle file uploads
        if 'profile_photo' in request.FILES:
            driver_profile.profile_photo = request.FILES['profile_photo']

        driver_profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('express_pwa:rider_profile')

    # Get rider's vehicles
    vehicles = driver_profile.vehicles.all()

    context = {
        'driver_profile': driver_profile,
        'vehicles': vehicles,
    }

    return render(request, 'express_pwa/rider/profile.html', context)


@pwa_login_required(pwa_app='express')
def rider_capture_signature(request, delivery_id):
    """
    Capture recipient signature before marking delivery as completed
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')

    try:
        delivery = DeliveryRequest.objects.get(
            id=delivery_id,
            driver=request.user,
            status='in_transit'
        )
    except DeliveryRequest.DoesNotExist:
        messages.error(request, 'Delivery not found or not in transit.')
        return redirect('express_pwa:rider_dashboard')

    if request.method == 'POST':
        signature_data = request.POST.get('signature_data')
        recipient_name = request.POST.get('recipient_name', '')
        notes = request.POST.get('notes', '')

        if not signature_data:
            messages.error(request, 'Signature is required to complete delivery.')
            return render(request, 'express_pwa/rider/signature_capture.html', {'delivery': delivery})

        # Save signature and complete delivery
        delivery.recipient_signature = signature_data
        delivery.signature_date = timezone.now()
        delivery.signature_ip_address = request.META.get('REMOTE_ADDR')
        if recipient_name:
            delivery.recipient_name = recipient_name
        delivery.status = 'delivered'
        delivery.delivery_time = timezone.now()
        delivery.save()

        # Create status update record
        DeliveryStatusUpdate.objects.create(
            delivery=delivery,
            status='delivered',
            notes=f"Signature captured. {notes}".strip(),
            updated_by=request.user
        )

        # Send SMS notification to sender
        try:
            send_custom_sms(
                delivery.sender.phone,
                f"Your delivery {delivery.tracking_number} has been completed and signed for by {recipient_name or 'recipient'}. Thank you for using Somako Express!"
            )
        except Exception as e:
            print(f"SMS notification failed: {e}")

        # Release driver for new assignments
        delivery.release_driver()

        messages.success(request, f'Delivery {delivery.tracking_number} completed successfully!')
        return redirect('express_pwa:rider_dashboard')

    context = {
        'delivery': delivery,
    }

    return render(request, 'express_pwa/rider/signature_capture.html', context)


@pwa_login_required(pwa_app='express')
def order_detail_rider(request, order_id):
    """
    Detail view for an ExpressOrder assigned to the rider
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'You need to be a delivery driver to access this page.')
        return redirect('express_pwa:become_driver')

    order = get_object_or_404(
        ExpressOrder.objects.prefetch_related('items__pickup_region', 'items__delivery_region'),
        id=order_id,
        driver=request.user
    )

    # Calculate driver commission (70%)
    driver_commission = (order.total_estimated_cost or Decimal('0.00')) * Decimal('0.70')

    context = {
        'order': order,
        'items': order.items.all().order_by('created_at'),
        'driver_commission': driver_commission,
    }

    return render(request, 'express_pwa/rider/order_detail.html', context)


@pwa_login_required(pwa_app='express')
def start_order(request, order_id):
    """
    Start processing an assigned order
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'You need to be a delivery driver to access this page.')
        return redirect('express_pwa:become_driver')

    order = get_object_or_404(ExpressOrder, id=order_id, driver=request.user)

    if order.status != 'assigned':
        messages.error(request, 'This order cannot be started.')
        return redirect('express_pwa:order_detail_rider', order_id=order.id)

    # Update order status
    order.status = 'in_progress'
    order.started_at = timezone.now()
    order.save()

    # Update all items to 'assigned' status if they aren't already
    order.items.filter(status='pending').update(
        status='assigned',
        driver=request.user
    )

    messages.success(request, f'Order {order.order_number} started successfully!')
    return redirect('express_pwa:order_detail_rider', order_id=order.id)


@pwa_login_required(pwa_app='express')  
def update_order_item_status(request, order_id, item_id):
    """
    Update the status of an individual item in an order
    """
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'You need to be a delivery driver to access this page.')
        return redirect('express_pwa:become_driver')

    order = get_object_or_404(ExpressOrder, id=order_id, driver=request.user)
    item = get_object_or_404(ExpressOrderItem, id=item_id, order=order, driver=request.user)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        valid_statuses = ['assigned', 'picked_up', 'in_transit', 'delivered', 'failed']
        if new_status not in valid_statuses:
            messages.error(request, 'Invalid status.')
            return redirect('express_pwa:order_detail_rider', order_id=order.id)

        # Update item status
        old_status = item.status
        item.status = new_status
        
        if new_status == 'picked_up' and old_status != 'picked_up':
            item.pickup_time = timezone.now()
        elif new_status == 'delivered' and old_status != 'delivered':
            item.delivery_time = timezone.now()
            
        item.save()

        # Check if all items are delivered to complete the order
        if new_status == 'delivered':
            all_items_delivered = not order.items.exclude(status='delivered').exists()
            if all_items_delivered:
                order.status = 'completed'
                order.completed_at = timezone.now()
                order.save()
                messages.success(request, f'Order {order.order_number} completed! All items delivered.')
            else:
                messages.success(request, f'Item {item.item_number} marked as delivered.')
        else:
            messages.success(request, f'Item {item.item_number} status updated to {item.get_status_display()}.')

        return redirect('express_pwa:order_detail_rider', order_id=order.id)

    context = {
        'order': order,
        'item': item,
    }

    return render(request, 'express_pwa/rider/update_item_status.html', context)
