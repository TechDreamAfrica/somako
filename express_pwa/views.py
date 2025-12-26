from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from decimal import Decimal, InvalidOperation, InvalidOperation

from core.pwa_decorators import pwa_login_required
from .models import DeliveryRequest, DeliveryStatusUpdate, DeliveryRating, DeliveryRegion, DeliveryArea
import requests
import logging
import traceback

logger = logging.getLogger(__name__)

# Try to import notification service, but make it optional
try:
    from accounts.notification_service import send_notification
except ImportError:
    send_notification = None


# ============================================
# SMS INTEGRATION - ARKESEL
# ============================================

def send_delivery_sms(phone, message):
    """
    Send SMS using Arkesel SMS API
    """
    # Skip if phone is not provided or SMS is disabled
    if not phone or not getattr(settings, 'ARKESEL_API_KEY', None):
        logger.warning(f"SMS not sent - phone: {phone}, API key configured: {bool(getattr(settings, 'ARKESEL_API_KEY', None))}")
        return False

    # Clean phone number - remove spaces and ensure proper format
    phone = phone.strip().replace(' ', '')

    # Add Ghana country code if not present
    if not phone.startswith('+'):
        if phone.startswith('0'):
            phone = '+233' + phone[1:]
        elif not phone.startswith('233'):
            phone = '+233' + phone
        else:
            phone = '+' + phone

    try:
        url = "https://sms.arkesel.com/api/v2/sms/send"
        headers = {
            'api-key': settings.ARKESEL_API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            'sender': getattr(settings, 'ARKESEL_SENDER_ID', 'Soma Ko'),
            'message': message,
            'recipients': [phone]
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"SMS sent successfully to {phone}: {result}")
            return True
        else:
            logger.error(f"SMS API error: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"SMS sending failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending SMS: {str(e)}")
        return False


@pwa_login_required(pwa_app='express')
def pwa_dashboard(request):
    """Express PWA Dashboard - Role-based (Sender/Driver)"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'express'

    user = request.user
    is_driver = user.has_role('delivery_driver')

    if is_driver:
        return redirect('express_pwa:rider_dashboard')

    # Sender dashboard
    # Import order models
    from .models import ExpressOrder, ExpressOrderItem
    
    # Get user's recent orders
    recent_orders = ExpressOrder.objects.filter(sender=user).order_by('-created_at')[:5]

    # Get active order (any order that's not completed or cancelled)
    active_order = ExpressOrder.objects.filter(
        sender=user,
        status__in=['draft', 'confirmed', 'assigned', 'in_progress']
    ).first()

    # Statistics - now using orders
    total_sent = ExpressOrder.objects.filter(sender=user).count()
    pending_count = ExpressOrder.objects.filter(
        sender=user,
        status__in=['draft', 'confirmed', 'assigned', 'in_progress']
    ).count()
    completed_count = ExpressOrder.objects.filter(
        sender=user,
        status='completed'
    ).count()

    stats = {
        'total_sent': total_sent,
        'pending_deliveries': pending_count,
        'completed': completed_count,
    }

    # Debug logging
    logger.info(f"Express Dashboard - User: {user.username}, Total Sent: {total_sent}, Pending: {pending_count}, Completed: {completed_count}")

    context = {
        'recent_orders': recent_orders,
        'stats': stats,
        'active_order': active_order,
        'is_driver': is_driver,
    }
    return render(request, 'express_pwa/dashboard.html', context)


@pwa_login_required(pwa_app='express')


def pwa_get_areas_by_region(request):
    """AJAX endpoint to get areas by region"""
    region_id = request.POST.get('region_id') if request.method == 'POST' else request.GET.get('region_id')
    if not region_id:
        return JsonResponse({'success': False, 'error': 'Region ID required'})
    
    try:
        region = DeliveryRegion.objects.get(id=region_id, is_active=True)
        areas = region.areas.filter(is_active=True).order_by('name')
        areas_data = [{'id': area.id, 'name': area.name} for area in areas]
        
        return JsonResponse({
            'success': True,
            'areas': areas_data
        })
    except DeliveryRegion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Region not found'})


@pwa_login_required(pwa_app='express')
def pwa_delivery_requests(request):
    """List user's delivery requests"""
    deliveries = DeliveryRequest.objects.filter(sender=request.user).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        deliveries = deliveries.filter(status=status_filter)
    
    paginator = Paginator(deliveries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': DeliveryRequest.STATUS_CHOICES,
    }
    return render(request, 'express_pwa/delivery_requests.html', context)


@pwa_login_required(pwa_app='express')
def pwa_delivery_detail(request, request_id):
    """Detailed view of a delivery request"""
    delivery = get_object_or_404(
        DeliveryRequest,
        id=request_id,
        sender=request.user
    )
    
    status_updates = delivery.status_updates.all()
    
    context = {
        'delivery': delivery,
        'status_updates': status_updates,
    }
    return render(request, 'express_pwa/delivery_detail.html', context)


@pwa_login_required(pwa_app='express')

@pwa_login_required(pwa_app='express')


@pwa_login_required(pwa_app='express')
def pwa_driver_dashboard(request):
    """Legacy driver dashboard - redirect to new rider dashboard"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'express'

    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')

    # Redirect to new rider dashboard
    messages.info(request, 'Redirected to updated driver dashboard.')
    return redirect('express_pwa:rider_dashboard')


@pwa_login_required(pwa_app='express')
def pwa_redirect_to_rider_available(request):
    """Redirect legacy available deliveries to rider system"""
    messages.info(request, 'Redirected to updated available deliveries page.')
    return redirect('express_pwa:rider_available_deliveries')


@pwa_login_required(pwa_app='express')
def pwa_redirect_to_rider_accept(request, request_id):
    """Redirect legacy accept delivery to rider system"""
    messages.info(request, 'Redirected to updated delivery system.')
    return redirect('express_pwa:rider_accept_delivery', request_id=request_id)


@pwa_login_required(pwa_app='express')
def pwa_redirect_to_rider_deliveries(request):
    """Redirect legacy my deliveries to rider system"""
    messages.info(request, 'Redirected to updated my deliveries page.')
    return redirect('express_pwa:rider_my_deliveries')


@pwa_login_required(pwa_app='express')
def pwa_redirect_to_rider_delivery(request, delivery_id):
    """Redirect legacy delivery detail to rider system"""
    messages.info(request, 'Redirected to updated delivery page.')
    return redirect('express_pwa:delivery_detail_rider', delivery_id=delivery_id)


@pwa_login_required(pwa_app='express')
def pwa_redirect_to_rider_signature(request, delivery_id):
    """Redirect legacy signature capture to rider system"""
    messages.info(request, 'Redirected to updated signature capture.')
    return redirect('express_pwa:rider_capture_signature', delivery_id=delivery_id)


@pwa_login_required(pwa_app='express')
def pwa_manual_assign_drivers(request):
    """Manually trigger driver assignment for unassigned deliveries"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin access required.')
        return redirect('express_pwa:dashboard')
    
    if request.method == 'POST':
        # Find unassigned confirmed deliveries
        unassigned_deliveries = DeliveryRequest.objects.filter(
            status='confirmed',
            driver__isnull=True
        ).order_by('created_at')
        
        assigned_count = 0
        failed_count = 0
        
        for delivery in unassigned_deliveries:
            if delivery.auto_assign_driver():
                assigned_count += 1
            else:
                failed_count += 1
        
        if assigned_count > 0:
            messages.success(request, f'Successfully assigned {assigned_count} deliveries to available drivers.')
        
        if failed_count > 0:
            messages.warning(request, f'{failed_count} deliveries could not be assigned - no available drivers.')
            
        if assigned_count == 0 and failed_count == 0:
            messages.info(request, 'No unassigned deliveries found.')
    
    return redirect('express_pwa:dashboard')


@pwa_login_required(pwa_app='express')
def pwa_available_deliveries(request):
    """Available deliveries for drivers"""
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')
    
    deliveries = DeliveryRequest.objects.filter(
        status='confirmed',
        driver__isnull=True
    ).order_by('-created_at')
    
    context = {'deliveries': deliveries}
    return render(request, 'express_pwa/available_deliveries.html', context)


@pwa_login_required(pwa_app='express')
def pwa_accept_delivery(request, request_id):
    """Accept a delivery request"""
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')
    
    delivery = get_object_or_404(DeliveryRequest, id=request_id, status='confirmed', driver__isnull=True)
    
    # Assign driver
    delivery.driver = request.user
    delivery.status = 'assigned'
    delivery.save()
    
    # Create status update
    DeliveryStatusUpdate.objects.create(
        delivery=delivery,
        status='assigned',
        notes=f'Assigned to driver {request.user.get_full_name()}',
        updated_by=request.user
    )
    
    # Notify sender
    if send_notification:
        send_notification(
            user=delivery.sender,
            notification_type='express_driver_assigned',
            title='Driver Assigned',
            message=f'A driver has been assigned to your delivery {delivery.tracking_number}.',
            channels=['in_app', 'sms']
        )
    
    messages.success(request, f'You have accepted delivery {delivery.tracking_number}')
    return redirect('express_pwa:driver_dashboard')


@pwa_login_required(pwa_app='express')
def pwa_my_deliveries(request):
    """Driver's assigned deliveries"""
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')
    
    deliveries = DeliveryRequest.objects.filter(driver=request.user).order_by('-created_at')
    
    context = {'deliveries': deliveries}
    return render(request, 'express_pwa/my_deliveries.html', context)


@pwa_login_required(pwa_app='express')
def pwa_update_delivery_status(request, delivery_id):
    """Update delivery status"""
    delivery = get_object_or_404(DeliveryRequest, id=delivery_id, driver=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in dict(DeliveryRequest.STATUS_CHOICES):
            delivery.status = new_status
            
            # Update pickup/delivery times
            if new_status == 'picked_up' and not delivery.pickup_time:
                delivery.pickup_time = timezone.now()
            elif new_status == 'delivered' and not delivery.delivery_time:
                delivery.delivery_time = timezone.now()
            
            delivery.save()
            
            # Create status update
            DeliveryStatusUpdate.objects.create(
                delivery=delivery,
                status=new_status,
                notes=notes,
                updated_by=request.user
            )
            
            # Notify sender via SMS
            status_messages = {
                'assigned': f'Driver {delivery.driver.get_full_name()} has been assigned to your delivery {delivery.tracking_number}.',
                'picked_up': f'Your package {delivery.tracking_number} has been picked up by the driver.',
                'in_transit': f'Your package {delivery.tracking_number} is now in transit to the destination.',
                'delivered': f'Your package {delivery.tracking_number} has been delivered successfully.',
            }

            if new_status in status_messages:
                # Send SMS to sender
                send_delivery_sms(
                    phone=delivery.sender.phone_number if hasattr(delivery.sender, 'phone_number') else None,
                    message=status_messages[new_status]
                )

                # Also send to recipient for important status changes
                if new_status in ['picked_up', 'in_transit']:
                    recipient_message = f'Your package (Tracking: {delivery.tracking_number}) from {delivery.sender.get_full_name()} is {new_status.replace("_", " ")}.'
                    send_delivery_sms(
                        phone=delivery.recipient_phone,
                        message=recipient_message
                    )

            messages.success(request, 'Delivery status updated successfully and notifications sent.')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('express_pwa:driver_dashboard')


@pwa_login_required(pwa_app='express')
def pwa_complete_delivery(request, delivery_id):
    """Redirect to signature capture page before completing delivery"""
    delivery = get_object_or_404(
        DeliveryRequest,
        id=delivery_id,
        driver=request.user,
        status='in_transit'
    )

    # Redirect to signature capture page
    messages.info(request, 'Please get recipient signature to complete delivery')
    return redirect('express_pwa:capture_signature', delivery_id=delivery.id)


@pwa_login_required(pwa_app='express')
def pwa_capture_signature(request, delivery_id):
    """Capture recipient signature for delivery confirmation"""
    try:
        delivery = get_object_or_404(
            DeliveryRequest,
            id=delivery_id,
            driver=request.user,
            status='in_transit'
        )
    except:
        # If delivery not found with the exact criteria, provide better error info
        try:
            delivery = get_object_or_404(DeliveryRequest, id=delivery_id)
            
            # Check various conditions and provide specific error messages
            if delivery.driver != request.user:
                messages.error(request, f'Access denied. This delivery is assigned to another driver.')
                return redirect('express_pwa:rider_dashboard')
            elif delivery.status != 'in_transit':
                if delivery.status == 'delivered':
                    messages.info(request, f'Delivery {delivery.tracking_number} has already been completed.')
                elif delivery.status == 'assigned':
                    messages.warning(request, f'Please mark delivery {delivery.tracking_number} as "picked up" and "in transit" before capturing signature.')
                elif delivery.status == 'picked_up':
                    messages.warning(request, f'Please mark delivery {delivery.tracking_number} as "in transit" before capturing signature.')
                else:
                    messages.error(request, f'Delivery {delivery.tracking_number} is not ready for signature capture. Current status: {delivery.get_status_display()}')
                return redirect('express_pwa:delivery_detail_rider', delivery_id=delivery.id)
        except:
            # Delivery doesn't exist at all
            messages.error(request, f'Delivery with ID {delivery_id} not found.')
            return redirect('express_pwa:rider_dashboard')

    if request.method == 'POST':
        signature_data = request.POST.get('signature')
        recipient_name = request.POST.get('recipient_name', '').strip()

        if not signature_data or signature_data == 'data:,':
            messages.error(request, 'Please provide a signature')
            return render(request, 'express_pwa/capture_signature.html', {'delivery': delivery})

        if not recipient_name:
            messages.error(request, 'Please provide recipient name')
            return render(request, 'express_pwa/capture_signature.html', {'delivery': delivery})

        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Update delivery with signature and mark as delivered
        delivery.recipient_signature = signature_data
        delivery.signed_by_name = recipient_name
        delivery.signature_date = timezone.now()
        delivery.signature_ip_address = ip_address
        delivery.status = 'delivered'
        delivery.delivery_time = timezone.now()
        delivery.final_cost = delivery.estimated_cost
        delivery.save()

        # Create status update
        DeliveryStatusUpdate.objects.create(
            delivery=delivery,
            status='delivered',
            notes=f'Package delivered and signed by {recipient_name}',
            updated_by=request.user
        )

        # Send SMS to sender
        send_delivery_sms(
            phone=delivery.sender.phone_number if hasattr(delivery.sender, 'phone_number') else None,
            message=f'Your package {delivery.tracking_number} has been delivered and signed by {recipient_name}. Thank you for using Soma Ko Express!'
        )

        # Send SMS to recipient
        send_delivery_sms(
            phone=delivery.recipient_phone,
            message=f'Package delivery confirmed. Tracking: {delivery.tracking_number}. Thank you for using Soma Ko Express!'
        )

        messages.success(request, f'Delivery completed successfully! Signed by: {recipient_name}')
        return redirect('express_pwa:driver_dashboard')

    context = {'delivery': delivery}
    return render(request, 'express_pwa/capture_signature.html', context)



@pwa_login_required(pwa_app='express')
def pwa_track_by_number(request, tracking_number):
    """Track delivery by tracking number"""
    try:
        delivery = DeliveryRequest.objects.get(tracking_number=tracking_number)
        # Allow tracking if user is sender, driver, or has the tracking number
        if delivery.sender == request.user or delivery.driver == request.user:
            return redirect('express_pwa:dashboard')
        else:
            # Public tracking with limited info
            context = {
                'delivery': delivery,
                'public_view': True,
            }
            return render(request, 'express_pwa/public_track.html', context)
    except DeliveryRequest.DoesNotExist:
        messages.error(request, 'Tracking number not found.')
        return redirect('express_pwa:dashboard')


def pwa_delivery_estimate(request):
    """Get delivery cost estimate (AJAX)"""
    if request.method == 'POST':
        try:
            weight = float(request.POST.get('weight', 0))
            urgency = request.POST.get('urgency', 'standard')
            pickup_region_id = request.POST.get('pickup_region')
            delivery_region_id = request.POST.get('delivery_region')
            
            # Determine base cost based on region
            base_cost = 20.0  # Same region default
            
            # Check if regions are different
            if pickup_region_id and delivery_region_id:
                if pickup_region_id != delivery_region_id:
                    base_cost = 40.0  # Different regions
            
            weight_cost = weight * 2.0
            urgency_multiplier = {'standard': 1.0, 'express': 1.5, 'urgent': 2.0}
            estimated_cost = (base_cost + weight_cost) * urgency_multiplier.get(urgency, 1.0)
            
            return JsonResponse({
                'success': True,
                'estimated_cost': round(estimated_cost, 2),
                'currency': 'GHS'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def pwa_pricing_info(request):
    """Pricing information page"""
    return render(request, 'express_pwa/pricing_info.html')


@pwa_login_required(pwa_app='express')
def pwa_delivery_history(request):
    """Delivery history"""
    deliveries = DeliveryRequest.objects.filter(
        Q(sender=request.user) | Q(driver=request.user),
        status__in=['delivered', 'cancelled']
    ).order_by('-delivery_time', '-created_at')
    
    context = {'deliveries': deliveries}
    return render(request, 'express_pwa/delivery_history.html', context)


@pwa_login_required(pwa_app='express')
def pwa_delivery_analytics(request):
    """Simple analytics for drivers"""
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Access denied. Driver role required.')
        return redirect('express_pwa:dashboard')
    
    # Monthly stats
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    
    stats = {
        'monthly_deliveries': DeliveryRequest.objects.filter(
            driver=request.user,
            delivery_time__gte=last_30_days,
            status='delivered'
        ).count(),
        'monthly_earnings': 0,  # Calculate based on delivery fees
        'avg_rating': DeliveryRating.objects.filter(
            delivery__driver=request.user
        ).aggregate(avg_rating=Avg('driver_rating'))['avg_rating'] or 0,
    }
    
    context = {'stats': stats}
    return render(request, 'express_pwa/analytics.html', context)


@pwa_login_required(pwa_app='express')
def pwa_notifications(request):
    """Express notifications"""
    # This would integrate with the main notification system
    context = {}
    return render(request, 'express_pwa/notifications.html', context)


@pwa_login_required(pwa_app='express')
def pwa_mark_notification_read(request, notification_id):
    """Mark notification as read"""
    # This would integrate with the main notification system
    return JsonResponse({'success': True})


# ============================================
# EXPRESS ORDER MANAGEMENT VIEWS
# ============================================

@pwa_login_required(pwa_app='express')
def pwa_create_order(request):
    """Create a new express order"""
    from .models import ExpressOrder
    
    if request.method == 'POST':
        try:
            # Create new order
            order = ExpressOrder.objects.create(
                sender=request.user,
                special_instructions=request.POST.get('special_instructions', '').strip()
            )
            
            messages.success(request, f'Order {order.order_number} created successfully!')
            return redirect('express_pwa:order_detail', order_number=order.order_number)
            
        except Exception as e:
            messages.error(request, f'Error creating order: {str(e)}')
            logger.error(f"Error creating express order: {str(e)}")
    
    context = {}
    return render(request, 'express_pwa/create_order.html', context)


@pwa_login_required(pwa_app='express')
def pwa_order_list(request):
    """List user's express orders"""
    from .models import ExpressOrder
    
    # Get orders for current user
    if request.user.has_role('delivery_driver'):
        # Driver sees assigned orders
        orders = ExpressOrder.objects.filter(
            driver=request.user
        ).select_related('sender').prefetch_related('items')
    else:
        # Customer sees their orders
        orders = ExpressOrder.objects.filter(
            sender=request.user
        ).prefetch_related('items')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'is_driver': request.user.has_role('delivery_driver'),
        'order_statuses': ExpressOrder.STATUS_CHOICES
    }
    return render(request, 'express_pwa/order_list.html', context)


@pwa_login_required(pwa_app='express')
def pwa_order_detail(request, order_number):
    """View order details and manage items"""
    from .models import ExpressOrder
    
    # Get order (driver can see assigned orders, sender can see their orders)
    if request.user.has_role('delivery_driver'):
        order = get_object_or_404(ExpressOrder, order_number=order_number, driver=request.user)
    else:
        order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    
    items = order.items.all().order_by('-created_at')
    
    context = {
        'order': order,
        'items': items,
        'can_add_items': order.status == 'draft' and order.sender == request.user,
        'can_assign_driver': order.can_assign_driver() and order.sender == request.user,
        'is_driver': request.user.has_role('delivery_driver')
    }
    return render(request, 'express_pwa/order_detail.html', context)


@pwa_login_required(pwa_app='express')
def pwa_add_item(request, order_number):
    """Add item to an order"""
    from .models import ExpressOrder, ExpressOrderItem
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    
    # Can only add items to draft orders
    if order.status != 'draft':
        messages.error(request, 'Cannot add items to this order.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        # Handle item creation for order
        try:
            # Validate required fields
            required_fields = ['recipient_name', 'recipient_phone', 'package_type', 'description',
                             'weight', 'urgency', 'pickup_address', 'delivery_address']

            for field in required_fields:
                if not request.POST.get(field):
                    messages.error(request, f'Please provide {field.replace("_", " ")}')
                    context = {
                        'order': order,
                        'package_types': DeliveryRequest.PACKAGE_TYPES,
                        'urgency_levels': DeliveryRequest.URGENCY_LEVELS,
                        'regions': DeliveryRegion.objects.filter(is_active=True).order_by('name'),
                    }
                    return render(request, 'express_pwa/add_item.html', context)

            # Get weight and value with validation
            try:
                weight = Decimal(request.POST.get('weight'))
                value = Decimal(request.POST.get('value', '0'))
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid weight or value format')
                context = {
                    'order': order,
                    'package_types': DeliveryRequest.PACKAGE_TYPES,
                    'urgency_levels': [
                        ('standard', 'Standard (24-48 hours)'),
                        ('express', 'Same Day (+GHS 5)'),
                        ('urgent', 'Urgent (2-4 hours) (+GHS 10)'),
                    ],
                    'regions': DeliveryRegion.objects.filter(is_active=True).order_by('name'),
                }
                return render(request, 'express_pwa/add_item.html', context)

            # Calculate estimated cost with new pricing structure
            pickup_region_id = request.POST.get('pickup_region')
            delivery_region_id = request.POST.get('delivery_region')
            urgency = request.POST.get('urgency', 'standard')
            
            # Base pricing logic
            if pickup_region_id and delivery_region_id:
                # Cross-region delivery
                if pickup_region_id != delivery_region_id:
                    base_cost = Decimal('40.0')  # GHS 40 for cross region
                else:
                    base_cost = Decimal('20.0')  # GHS 20 for local delivery
            else:
                # Default to local delivery if regions not specified
                base_cost = Decimal('20.0')
            
            # Weight-based pricing
            weight_cost = Decimal('0.0')
            if weight <= Decimal('1.0'):
                # Included in base rate for 1kg
                weight_cost = Decimal('0.0')
            elif weight <= Decimal('3.0'):
                # Additional weight beyond 1kg at 20 GHS per kg for local, 40 for cross-region
                if pickup_region_id and delivery_region_id and pickup_region_id != delivery_region_id:
                    weight_cost = (weight - Decimal('1.0')) * Decimal('40.0')
                else:
                    weight_cost = (weight - Decimal('1.0')) * Decimal('20.0')
            elif weight <= Decimal('5.0'):
                # 3KG to 5KG: GHS 5 additional
                if pickup_region_id and delivery_region_id and pickup_region_id != delivery_region_id:
                    weight_cost = Decimal('2.0') * Decimal('40.0')  # First 2kg beyond 1kg
                else:
                    weight_cost = Decimal('2.0') * Decimal('20.0')  # First 2kg beyond 1kg
                weight_cost += Decimal('5.0')  # Additional GHS 5 for 3-5kg range
            elif weight <= Decimal('10.0'):
                # 5KG to 10KG: GHS 10 additional
                if pickup_region_id and delivery_region_id and pickup_region_id != delivery_region_id:
                    weight_cost = Decimal('2.0') * Decimal('40.0')  # First 2kg beyond 1kg
                else:
                    weight_cost = Decimal('2.0') * Decimal('20.0')  # First 2kg beyond 1kg
                weight_cost += Decimal('5.0')  # 3-5kg range
                weight_cost += Decimal('10.0')  # Additional GHS 10 for 5-10kg range
            else:
                # Beyond 10kg: calculate proportionally
                if pickup_region_id and delivery_region_id and pickup_region_id != delivery_region_id:
                    weight_cost = Decimal('2.0') * Decimal('40.0')  # First 2kg beyond 1kg
                else:
                    weight_cost = Decimal('2.0') * Decimal('20.0')  # First 2kg beyond 1kg
                weight_cost += Decimal('5.0')  # 3-5kg range
                weight_cost += Decimal('10.0')  # 5-10kg range
                # Additional weight beyond 10kg
                extra_weight = weight - Decimal('10.0')
                if pickup_region_id and delivery_region_id and pickup_region_id != delivery_region_id:
                    weight_cost += extra_weight * Decimal('40.0')
                else:
                    weight_cost += extra_weight * Decimal('20.0')
            
            # Urgency-based additional charges
            urgency_additional = Decimal('0.0')
            if urgency == 'express':
                urgency_additional = Decimal('5.0')  # Additional GHS 5 for same day
            elif urgency == 'urgent':  # 2-4 hours
                urgency_additional = Decimal('10.0')  # Additional GHS 10 for 2-4 hours
            
            estimated_cost = base_cost + weight_cost + urgency_additional

            # Add item to order
            item = ExpressOrderItem.objects.create(
                order=order,
                recipient_name=request.POST.get('recipient_name').strip(),
                recipient_phone=request.POST.get('recipient_phone').strip(),
                package_type=request.POST.get('package_type'),
                description=request.POST.get('description').strip(),
                weight=weight,
                value=value,
                urgency=request.POST.get('urgency'),
                pickup_address=request.POST.get('pickup_address').strip(),
                pickup_landmark=request.POST.get('pickup_landmark', '').strip(),
                pickup_instructions=request.POST.get('pickup_instructions', '').strip(),
                pickup_region_id=pickup_region_id if pickup_region_id else None,
                pickup_area_id=request.POST.get('pickup_area') if request.POST.get('pickup_area') else None,
                delivery_address=request.POST.get('delivery_address').strip(),
                delivery_landmark=request.POST.get('delivery_landmark', '').strip(),
                delivery_instructions=request.POST.get('delivery_instructions', '').strip(),
                delivery_region_id=delivery_region_id if delivery_region_id else None,
                delivery_area_id=request.POST.get('delivery_area') if request.POST.get('delivery_area') else None,
                estimated_cost=estimated_cost,
                status='pending'
            )
            
            # Recalculate order total cost
            order.calculate_total_cost()
            
            messages.success(request, f'Item {item.item_number} added to order {order.order_number}!')
            return redirect('express_pwa:order_detail', order_number=order.order_number)

        except Exception as e:
            messages.error(request, f'Error adding item to order: {str(e)}')

    # Render add item form
    context = {
        'order': order,
        'package_types': DeliveryRequest.PACKAGE_TYPES,
        'urgency_levels': [
            ('standard', 'Standard (24-48 hours)'),
            ('express', 'Same Day (+GHS 5)'),
            ('urgent', 'Urgent (2-4 hours) (+GHS 10)'),
        ],
        'regions': DeliveryRegion.objects.filter(is_active=True).order_by('name'),
    }
    return render(request, 'express_pwa/add_item.html', context)


@pwa_login_required(pwa_app='express')
def pwa_edit_order(request, order_number):
    """Edit order details when in draft status"""
    from .models import ExpressOrder
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    
    # Can only edit draft orders
    if order.status != 'draft':
        messages.error(request, 'Cannot edit this order as it is no longer in draft status.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        # Update order details
        order.special_instructions = request.POST.get('special_instructions', '').strip()
        order.save()
        
        messages.success(request, 'Order updated successfully!')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    context = {
        'order': order,
    }
    return render(request, 'express_pwa/edit_order.html', context)


@pwa_login_required(pwa_app='express')
def pwa_edit_item(request, order_number, item_id):
    """Edit order item when order is in draft status"""
    from .models import ExpressOrder, ExpressOrderItem
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    item = get_object_or_404(ExpressOrderItem, id=item_id, order=order)
    
    # Can only edit items in draft orders
    if order.status != 'draft':
        messages.error(request, 'Cannot edit items as this order is no longer in draft status.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = ['recipient_name', 'recipient_phone', 'package_type', 'description',
                             'weight', 'urgency', 'pickup_address', 'delivery_address']

            for field in required_fields:
                if not request.POST.get(field):
                    messages.error(request, f'Please provide {field.replace("_", " ")}')
                    context = {
                        'order': order,
                        'item': item,
                        'package_types': ExpressOrderItem.PACKAGE_TYPES,
                        'urgency_levels': ExpressOrderItem.URGENCY_LEVELS,
                        'regions': DeliveryRegion.objects.filter(is_active=True).order_by('name'),
                    }
                    return render(request, 'express_pwa/edit_item.html', context)

            # Get weight and value with validation
            try:
                weight = Decimal(request.POST.get('weight'))
                value = Decimal(request.POST.get('value', '0'))
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid weight or value format')
                context = {
                    'order': order,
                    'item': item,
                    'package_types': ExpressOrderItem.PACKAGE_TYPES,
                    'urgency_levels': ExpressOrderItem.URGENCY_LEVELS,
                    'regions': DeliveryRegion.objects.filter(is_active=True).order_by('name'),
                }
                return render(request, 'express_pwa/edit_item.html', context)

            # Update item fields
            item.recipient_name = request.POST.get('recipient_name').strip()
            item.recipient_phone = request.POST.get('recipient_phone').strip()
            item.package_type = request.POST.get('package_type')
            item.description = request.POST.get('description').strip()
            item.weight = weight
            item.value = value
            item.urgency = request.POST.get('urgency')
            item.pickup_address = request.POST.get('pickup_address').strip()
            item.pickup_landmark = request.POST.get('pickup_landmark', '').strip()
            item.pickup_instructions = request.POST.get('pickup_instructions', '').strip()
            item.delivery_address = request.POST.get('delivery_address').strip()
            item.delivery_landmark = request.POST.get('delivery_landmark', '').strip()
            item.delivery_instructions = request.POST.get('delivery_instructions', '').strip()

            # Recalculate estimated cost
            base_cost = Decimal('20.0')  # Same region default
            pickup_region_id = request.POST.get('pickup_region')
            delivery_region_id = request.POST.get('delivery_region')
            if pickup_region_id and delivery_region_id and pickup_region_id != delivery_region_id:
                base_cost = Decimal('40.0')  # Different regions
                
            weight_cost = weight * Decimal('2.0')
            urgency_multiplier = {
                'standard': Decimal('1.0'),
                'express': Decimal('1.5'),
                'urgent': Decimal('2.0')
            }
            item.estimated_cost = (base_cost + weight_cost) * urgency_multiplier.get(
                request.POST.get('urgency', 'standard'), Decimal('1.0')
            )

            # Handle region selection
            pickup_region_id = request.POST.get('pickup_region')
            delivery_region_id = request.POST.get('delivery_region')
            pickup_area_id = request.POST.get('pickup_area')
            delivery_area_id = request.POST.get('delivery_area')

            if pickup_region_id:
                item.pickup_region_id = pickup_region_id
            if delivery_region_id:
                item.delivery_region_id = delivery_region_id
            if pickup_area_id:
                item.pickup_area_id = pickup_area_id
            if delivery_area_id:
                item.delivery_area_id = delivery_area_id

            item.save()
            
            # Update order total cost
            order.calculate_total_cost()
            
            messages.success(request, f'Item {item.item_number} updated successfully!')
            return redirect('express_pwa:order_detail', order_number=order_number)
            
        except Exception as e:
            messages.error(request, f'Error updating item: {str(e)}')
    
    # Calculate current estimated cost for display
    current_base_cost = Decimal('20.0')  # Same region default
    if item.pickup_region and item.delivery_region and item.pickup_region != item.delivery_region:
        current_base_cost = Decimal('40.0')  # Different regions
    
    current_weight_cost = (item.weight or Decimal('1.0')) * Decimal('2.0')
    urgency_multiplier = {
        'standard': Decimal('1.0'),
        'express': Decimal('1.5'),
        'urgent': Decimal('2.0')
    }
    calculated_cost = (current_base_cost + current_weight_cost) * urgency_multiplier.get(
        item.urgency or 'standard', Decimal('1.0')
    )

    context = {
        'order': order,
        'item': item,
        'package_types': ExpressOrderItem.PACKAGE_TYPES,
        'urgency_levels': ExpressOrderItem.URGENCY_LEVELS,
        'regions': DeliveryRegion.objects.filter(is_active=True).order_by('name'),
        'calculated_cost': calculated_cost,
        'current_estimated_cost': item.estimated_cost or calculated_cost,
    }
    return render(request, 'express_pwa/edit_item.html', context)


@pwa_login_required(pwa_app='express')
def pwa_delete_item(request, order_number, item_id):
    """Delete order item when order is in draft status"""
    from .models import ExpressOrder, ExpressOrderItem
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    item = get_object_or_404(ExpressOrderItem, id=item_id, order=order)
    
    # Can only delete items from draft orders
    if order.status != 'draft':
        messages.error(request, 'Cannot delete items as this order is no longer in draft status.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        item_number = item.item_number
        item.delete()
        
        # Update order total cost
        order.calculate_total_cost()
        
        messages.success(request, f'Item {item_number} deleted successfully!')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    context = {
        'order': order,
        'item': item,
    }
    return render(request, 'express_pwa/confirm_delete_item.html', context)


@pwa_login_required(pwa_app='express')
def pwa_submit_order(request, order_number):
    """Submit order for processing and send SMS notifications"""
    from .models import ExpressOrder
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    
    # Can only submit draft orders with items
    if order.status != 'draft':
        messages.error(request, 'This order has already been submitted.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if not order.items.exists():
        messages.error(request, 'Cannot submit an order without items.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    try:
        # Update order status
        order.status = 'pending'
        order.save()
        
        # Get recipients info before sending SMS
        recipients = order.get_recipients()
        total_recipients = len(recipients)
        
        logger.info(f"Order {order.order_number} submitted. Attempting to send SMS to {total_recipients} recipients: {recipients}")
        
        # Send SMS notifications to recipients
        sms_results = order.send_creation_sms()
        
        # Send SMS notification to sender
        from utils.sms_utils import send_express_sender_notification
        sender_result = send_express_sender_notification(order, 'submitted')
        
        logger.info(f"SMS sending completed. Recipient results: {sms_results}")
        logger.info(f"Sender notification result: {sender_result}")
        
        success_count = len([r for r in sms_results if r.get('success', False)]) if sms_results else 0
        sender_success = sender_result.get('success', False) if sender_result else False
        
        if success_count > 0 or sender_success:
            notification_parts = []
            if success_count > 0:
                notification_parts.append(f'{success_count} of {total_recipients} recipients')
            if sender_success:
                notification_parts.append('sender (you)')
            
            notifications_text = ' and '.join(notification_parts) if notification_parts else 'recipients'
            
            messages.success(
                request, 
                f'Order {order.order_number} submitted successfully! '
                f'SMS notifications sent to {notifications_text}.'
            )
        else:
            if total_recipients > 0:
                # Show the specific SMS error if available
                error_details = []
                if sms_results:
                    for result in sms_results:
                        if not result.get('success', False):
                            error_details.append(f"{result.get('recipient', 'Unknown')}: {result.get('message', 'Unknown error')}")
                
                error_msg = f'Order {order.order_number} submitted successfully! However, SMS notifications failed.'
                if error_details:
                    error_msg += f' Errors: {"; ".join(error_details)}'
                
                messages.warning(request, error_msg)
                logger.warning(f"SMS sending failed for order {order_number}: {error_details}")
            else:
                messages.success(
                    request, 
                    f'Order {order.order_number} submitted successfully! (No recipient phone numbers to notify)'
                )
        
    except Exception as e:
        messages.error(request, f'Error submitting order: {str(e)}')
        logger.error(f"Error submitting order {order_number}: {str(e)}")
        logger.error(f"Full traceback: ", exc_info=True)
    
    return redirect('express_pwa:order_detail', order_number=order_number)


@pwa_login_required(pwa_app='express')
def pwa_assign_driver(request, order_number):
    """Assign driver to an order"""
    from .models import ExpressOrder, DeliveryDriverProfile
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    
    if not order.can_assign_driver():
        messages.error(request, 'This order cannot be assigned to a driver.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            driver = get_object_or_404(User, id=driver_id, delivery_driver_profile__status='APPROVED')
            
            if order.assign_to_driver(driver):
                # The assign_to_driver method will trigger SMS sending to both recipients and driver
                messages.success(request, f'Order assigned to {driver.get_full_name() or driver.username} successfully! SMS notifications sent to recipients and driver.')
                logger.info(f"Order {order.order_number} assigned to driver {driver.username}")
            else:
                messages.error(request, 'Failed to assign driver to order.')
                
        except Exception as e:
            messages.error(request, f'Error assigning driver: {str(e)}')
            logger.error(f"Error assigning driver to order {order_number}: {str(e)}")
        
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    # Get available drivers
    available_drivers = DeliveryDriverProfile.objects.filter(
        status='APPROVED',
        availability='ONLINE'
    ).exclude(
        user__assigned_express_orders__status__in=['assigned', 'in_progress']
    ).select_related('user')[:10]
    
    context = {
        'order': order,
        'available_drivers': available_drivers
    }
    return render(request, 'express_pwa/assign_driver.html', context)


@pwa_login_required(pwa_app='express')
def pwa_update_order_status(request, order_number):
    """Update order status (driver only)"""
    from .models import ExpressOrder
    
    # Only drivers can update order status
    if not request.user.has_role('delivery_driver'):
        messages.error(request, 'Only delivery drivers can update order status.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, driver=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in ['in_progress', 'completed']:
            try:
                old_status = order.status
                order.status = new_status
                
                if new_status == 'in_progress' and not order.started_at:
                    order.started_at = timezone.now()
                elif new_status == 'completed' and not order.completed_at:
                    order.completed_at = timezone.now()
                    # Mark all items as delivered
                    order.items.update(status='delivered', delivery_time=timezone.now())
                
                order.save()  # This will trigger SMS notifications
                
                messages.success(request, f'Order status updated to {new_status}!')
                
            except Exception as e:
                messages.error(request, f'Error updating status: {str(e)}')
                logger.error(f"Error updating order {order_number} status: {str(e)}")
        else:
            messages.error(request, 'Invalid status update.')
    
    return redirect('express_pwa:order_detail', order_number=order_number)


@pwa_login_required(pwa_app='express')
def pwa_delete_order(request, order_number):
    """Delete a draft order"""
    from .models import ExpressOrder
    
    order = get_object_or_404(ExpressOrder, order_number=order_number, sender=request.user)
    
    # Only allow deletion of draft orders
    if order.status != 'draft':
        messages.error(request, 'Only draft orders can be deleted.')
        return redirect('express_pwa:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        try:
            order_items_count = order.items.count()
            order.delete()
            
            messages.success(request, f'Draft order {order_number} and its {order_items_count} item(s) have been deleted successfully.')
            logger.info(f"Draft order {order_number} deleted by user {request.user.username}")
            
            return redirect('express_pwa:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error deleting order: {str(e)}')
            logger.error(f"Error deleting order {order_number}: {str(e)}")
            return redirect('express_pwa:order_detail', order_number=order_number)
    
    context = {
        'order': order,
    }
    return render(request, 'express_pwa/confirm_delete_order.html', context)


@pwa_login_required(pwa_app='express')
def pwa_order_tracking(request):
    """Order tracking for senders - shows all their order items"""
    from .models import ExpressOrderItem
    
    # Get all order items for the current user
    items = ExpressOrderItem.objects.filter(
        order__sender=request.user
    ).select_related('order').order_by('-created_at')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        items = items.filter(status=status_filter)
    
    # Search by order number or item number
    search_query = request.GET.get('search')
    if search_query:
        items = items.filter(
            Q(order__order_number__icontains=search_query) |
            Q(item_number__icontains=search_query) |
            Q(recipient_name__icontains=search_query)
        )
    
    context = {
        'items': items,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': [
            ('all', 'All Items'),
            ('pending', 'Pending'),
            ('assigned', 'Assigned'),
            ('picked_up', 'Picked Up'),
            ('in_transit', 'In Transit'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
        ]
    }
    return render(request, 'express_pwa/order_tracking.html', context)


@pwa_login_required(pwa_app='express')
def get_areas_by_region(request):
    """AJAX endpoint to get delivery areas for a specific region"""
    region_id = request.GET.get('region_id')
    
    if not region_id:
        return JsonResponse({'success': False, 'message': 'Region ID is required'})
    
    try:
        region = DeliveryRegion.objects.get(id=region_id, is_active=True)
        areas = list(region.areas.filter(is_active=True).values('id', 'name'))
        
        return JsonResponse({
            'success': True,
            'areas': areas
        })
    
    except DeliveryRegion.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Region not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
