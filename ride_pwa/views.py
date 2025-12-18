"""
Ride PWA Views - Progressive Web App specific views
Optimized for mobile-first experience with touch-friendly interfaces
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta
from decimal import Decimal
import json
import logging
from functools import wraps

from ride.models import Ride, Vehicle, Rating, VehicleCategory, DriverProfile

logger = logging.getLogger(__name__)


# ============================================
# DECORATORS
# ============================================

def driver_required(view_func):
    """Decorator to ensure only drivers can access certain views"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'driver_profile'):
            messages.error(request, 'You must be a registered driver to access this page.')
            return redirect('ride_pwa:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================
# RIDER VIEWS
# ============================================

@login_required
def pwa_dashboard(request):
    """PWA Ride Dashboard - Role-based (Rider/Driver)"""
    # Mark as PWA session
    request.session['is_pwa_user'] = True
    request.session['pwa_app'] = 'ride'

    user = request.user
    is_driver = hasattr(user, 'driver_profile')

    if is_driver:
        return redirect('ride_pwa:driver_dashboard')

    # Rider dashboard
    context = {
        'recent_rides': Ride.objects.filter(
            passenger=user
        ).order_by('-requested_at')[:5],
        'active_ride': Ride.objects.filter(
            passenger=user,
            status__in=['REQUESTED', 'ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS']
        ).first(),
        'vehicle_categories': VehicleCategory.objects.filter(is_active=True),
    }
    return render(request, 'ride/pwa/dashboard.html', context)


@csrf_exempt
@login_required
def update_location(request):
    """Update user location in session for GPS-based driver matching"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            
            # Validate coordinates
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                request.session['user_latitude'] = latitude
                request.session['user_longitude'] = longitude
                request.session['location_updated'] = timezone.now().isoformat()
                
                return JsonResponse({'success': True, 'message': 'Location updated'})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid coordinates'})
                
        except (ValueError, json.JSONDecodeError) as e:
            return JsonResponse({'success': False, 'error': 'Invalid data format'})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})


@login_required
def pwa_book_ride(request):
    """Book a new ride"""
    if request.method == 'POST':
        # Get form data
        pickup_address = request.POST.get('pickup_address')
        pickup_latitude = request.POST.get('pickup_latitude', '0.0')
        pickup_longitude = request.POST.get('pickup_longitude', '0.0')
        dropoff_address = request.POST.get('dropoff_address')
        dropoff_latitude = request.POST.get('dropoff_latitude', '0.0')
        dropoff_longitude = request.POST.get('dropoff_longitude', '0.0')
        driver_id = request.POST.get('driver_id')  # Get selected driver (required)
        passenger_count = int(request.POST.get('passenger_count', 1))
        special_requests = request.POST.get('special_requests', '')
        estimated_distance = Decimal(request.POST.get('estimated_distance', '5.0'))
        estimated_duration = int(request.POST.get('estimated_duration', '15'))

        # Validate driver selection
        if not driver_id:
            messages.error(request, 'Please select a driver to continue.')
            return redirect('ride_pwa:book_ride')
        
        # Get selected driver and their vehicle category
        try:
            driver = DriverProfile.objects.select_related('user').prefetch_related('vehicles__category').get(
                id=driver_id,
                status='APPROVED',
                availability='ONLINE'
            )
            # Get driver's primary vehicle (or first vehicle)
            primary_vehicle = driver.vehicles.filter(is_active=True).order_by('-is_primary').first()
            
            if not primary_vehicle:
                messages.error(request, 'Selected driver has no active vehicle. Please choose another driver.')
                return redirect('ride_pwa:book_ride')
            
            vehicle_category = primary_vehicle.category
            
        except DriverProfile.DoesNotExist:
            messages.error(request, 'Selected driver is no longer available. Please choose another driver.')
            return redirect('ride_pwa:book_ride')

        # Create ride instance (without saving yet)
        ride = Ride(
            passenger=request.user,
            driver=driver,  # Assign selected driver
            vehicle=primary_vehicle,  # Assign driver's vehicle
            pickup_address=pickup_address,
            pickup_latitude=Decimal(pickup_latitude),
            pickup_longitude=Decimal(pickup_longitude),
            dropoff_address=dropoff_address,
            dropoff_latitude=Decimal(dropoff_latitude),
            dropoff_longitude=Decimal(dropoff_longitude),
            vehicle_category=vehicle_category,
            passenger_count=passenger_count,
            special_requests=special_requests,
            estimated_distance_km=estimated_distance,
            estimated_duration_minutes=estimated_duration,
            status='REQUESTED'  # Driver must accept or reject
        )

        # Calculate fare BEFORE saving
        ride.calculate_fare()
        
        # Now save the ride with all fare fields populated
        ride.save()
        
        # Note: Driver availability stays ONLINE until they accept the ride
        # No accepted_at timestamp yet - set when driver accepts

        # Send SMS notifications
        try:
            # Send confirmation to passenger
            from utils.sms_utils import send_passenger_ride_confirmation, send_driver_ride_notification
            
            logger.info(f"Sending SMS notifications for ride {ride.ride_id}")
            logger.info(f"Passenger: {request.user.username}, Driver: {driver.user.username}")
            
            passenger_sms = send_passenger_ride_confirmation(request.user, ride)
            logger.info(f"Passenger SMS result: {passenger_sms}")
            
            # Send notification to selected driver
            driver_sms = send_driver_ride_notification(driver, ride)
            logger.info(f"Driver SMS result: {driver_sms}")
            
            if passenger_sms.get('success') and driver_sms.get('success'):
                messages.success(
                    request, 
                    f'Ride requested from {driver.user.get_full_name()}! Both you and the driver have been notified via SMS. Waiting for driver to accept. Ride ID: {ride.ride_id}'
                )
            elif passenger_sms.get('success'):
                messages.success(request, f'Ride requested! Confirmation sent to you via SMS. Waiting for driver to accept. Ride ID: {ride.ride_id}')
            elif driver_sms.get('success'):
                messages.success(request, f'Ride requested! Driver notified via SMS. Waiting for acceptance. Ride ID: {ride.ride_id}')
            else:
                messages.success(request, f'Ride requested from {driver.user.get_full_name()}! Waiting for driver to accept. Ride ID: {ride.ride_id}')
                logger.warning(f"Both SMS notifications failed for ride {ride.ride_id}")
                
        except Exception as e:
            logger.error(f"Failed to send notifications for ride {ride.ride_id}: {str(e)}", exc_info=True)
            messages.success(request, f'Ride requested from {driver.user.get_full_name()}! Waiting for driver to accept. Ride ID: {ride.ride_id}')
            messages.info(request, 'Notifications will be sent through the app.')

        return redirect('ride_pwa:track_ride', ride_id=ride.id)

    # GET request - show booking form with GPS-based driver filtering
    from django.db.models import Avg
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        """Calculate the great circle distance between two points on the earth"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    # Get user's location from session (set by GPS)
    user_lat = request.session.get('user_latitude', 5.6037)  # Default to Accra, Ghana
    user_lng = request.session.get('user_longitude', -0.1870)
    
    # Get all available drivers
    all_drivers = DriverProfile.objects.filter(
        status='APPROVED',
        availability='ONLINE',
        vehicles__is_active=True
    ).select_related('user').prefetch_related('vehicles__category').annotate(
        avg_rating=Avg('ratings_received__rating')
    ).distinct()

    # Categorize drivers based on location
    nearby_drivers = []
    random_drivers = []
    
    for driver in all_drivers:
        # Check if driver has location data
        if driver.current_latitude and driver.current_longitude:
            distance = haversine(
                float(user_lng), float(user_lat),
                float(driver.current_longitude), float(driver.current_latitude)
            )
            driver.distance_from_user = round(distance, 1)
            
            if distance <= 15:  # Within 15km radius
                nearby_drivers.append(driver)
            else:
                random_drivers.append(driver)
        else:
            # Driver without location - add to random list
            driver.distance_from_user = None
            random_drivers.append(driver)

    # Sort nearby drivers by distance, random drivers by rating
    nearby_drivers.sort(key=lambda x: x.distance_from_user)
    random_drivers.sort(key=lambda x: x.avg_rating or 0, reverse=True)
    
    # Determine driver selection mode
    has_gps = request.session.get('user_latitude') is not None
    driver_selection_mode = 'nearby' if nearby_drivers and has_gps else 'random'
    
    context = {
        'nearby_drivers': nearby_drivers[:6],  # Limit to 6 nearby drivers
        'random_drivers': random_drivers[:10],  # Limit to 10 random drivers
        'driver_selection_mode': driver_selection_mode,
        'has_gps': has_gps,
        'user_lat': user_lat,
        'user_lng': user_lng,
    }
    return render(request, 'ride/pwa/book_ride.html', context)


@login_required
def pwa_ride_list(request):
    """View ride history"""
    rides = Ride.objects.filter(passenger=request.user).order_by('-requested_at')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        rides = rides.filter(status=status_filter)

    context = {
        'rides': rides,
        'status_filter': status_filter,
    }
    return render(request, 'ride/pwa/ride_list.html', context)


@login_required
def pwa_ride_detail(request, ride_id):
    """View ride details"""
    ride = get_object_or_404(Ride, pk=ride_id, passenger=request.user)

    # Check if already rated
    has_rating = Rating.objects.filter(
        ride=ride,
        rating_type='PASSENGER_TO_DRIVER'
    ).exists()

    context = {
        'ride': ride,
        'can_cancel': ride.can_be_cancelled(),
        'can_rate': ride.status == 'COMPLETED' and not has_rating,
    }
    return render(request, 'ride/pwa/ride_detail.html', context)


@login_required
def pwa_track_ride(request, ride_id):
    """Track ride in real-time"""
    ride = get_object_or_404(Ride, pk=ride_id, passenger=request.user)

    # Ride progress stages
    stages = [
        {'status': 'REQUESTED', 'label': 'Finding Driver', 'icon': 'fa-search'},
        {'status': 'ACCEPTED', 'label': 'Driver Assigned', 'icon': 'fa-user-check'},
        {'status': 'DRIVER_ARRIVED', 'label': 'Driver Arrived', 'icon': 'fa-map-marker-alt'},
        {'status': 'IN_PROGRESS', 'label': 'On The Way', 'icon': 'fa-car'},
        {'status': 'COMPLETED', 'label': 'Arrived', 'icon': 'fa-flag-checkered'},
    ]

    context = {
        'ride': ride,
        'stages': stages,
    }
    return render(request, 'ride/pwa/track_ride.html', context)


@login_required
def pwa_cancel_ride(request, ride_id):
    """Cancel a ride"""
    ride = get_object_or_404(Ride, pk=ride_id, passenger=request.user)

    if request.method == 'POST':
        if ride.can_be_cancelled():
            ride.status = 'CANCELLED_BY_PASSENGER'
            ride.cancelled_at = timezone.now()
            ride.cancellation_reason = request.POST.get('reason', 'Cancelled by passenger')
            ride.save()
            messages.success(request, 'Ride cancelled successfully!')
        else:
            messages.error(request, 'This ride cannot be cancelled.')

        return redirect('ride_pwa:ride_detail', ride_id=ride_id)

    context = {'ride': ride}
    return render(request, 'ride/pwa/cancel_ride.html', context)


@login_required
def pwa_rate_ride(request, ride_id):
    """Rate a completed ride"""
    ride = get_object_or_404(Ride, pk=ride_id, passenger=request.user, status='COMPLETED')

    # Check if already rated
    if Rating.objects.filter(ride=ride, rating_type='PASSENGER_TO_DRIVER').exists():
        messages.info(request, 'You have already rated this ride.')
        return redirect('ride_pwa:ride_detail', ride_id=ride_id)

    if request.method == 'POST':
        rating_value = int(request.POST.get('rating', 5))
        review_text = request.POST.get('review', '')
        cleanliness = request.POST.get('cleanliness_rating')
        punctuality = request.POST.get('punctuality_rating')
        communication = request.POST.get('communication_rating')
        driving = request.POST.get('driving_rating')

        Rating.objects.create(
            ride=ride,
            rating_type='PASSENGER_TO_DRIVER',
            rater=request.user,
            rated_driver=ride.driver,
            rating=rating_value,
            review=review_text,
            cleanliness_rating=int(cleanliness) if cleanliness else None,
            punctuality_rating=int(punctuality) if punctuality else None,
            communication_rating=int(communication) if communication else None,
            driving_rating=int(driving) if driving else None,
        )

        messages.success(request, 'Thank you for your feedback!')
        return redirect('ride_pwa:ride_detail', ride_id=ride_id)

    context = {
        'ride': ride,
    }
    return render(request, 'ride/pwa/rate_ride.html', context)


@login_required
def pwa_complete_ride_passenger(request, ride_id):
    """Passenger confirms ride completion"""
    ride = get_object_or_404(Ride, pk=ride_id, passenger=request.user)
    
    # Only allow if driver has marked as completed
    if not ride.driver_completed:
        messages.error(request, 'Driver has not yet marked this ride as complete.')
        return redirect('ride_pwa:ride_detail', ride_id=ride_id)
    
    if request.method == 'POST':
        # Passenger confirms completion
        ride.passenger_completed = True
        ride.passenger_completed_at = timezone.now()
        
        # Both confirmed - complete the ride
        if ride.driver_completed:
            ride.status = 'COMPLETED'
            ride.completed_at = timezone.now()
            
            # Update driver availability and total rides
            if ride.driver:
                ride.driver.availability = 'ONLINE'
                ride.driver.total_rides += 1
                ride.driver.save()
            
            messages.success(request, 'Ride completed! Thank you for confirming.')
            
            # Send SMS notification to passenger
            try:
                from utils.sms_utils import send_passenger_ride_completed
                send_passenger_ride_completed(request.user, ride)
            except Exception as e:
                logger.error(f"Failed to send completion SMS to passenger for ride {ride.ride_id}: {str(e)}")
        else:
            messages.success(request, 'Thank you for confirming. Waiting for driver confirmation.')
        
        ride.save()
        return redirect('ride_pwa:rate_ride', ride_id=ride_id)
    
    context = {'ride': ride}
    return render(request, 'ride/pwa/complete_ride.html', context)


@login_required
def pwa_search(request):
    """Search rides"""
    query = request.GET.get('q', '')

    rides = []
    if query:
        rides = Ride.objects.filter(
            Q(pickup_address__icontains=query) |
            Q(dropoff_address__icontains=query),
            passenger=request.user
        ).order_by('-requested_at')[:20]

    context = {
        'query': query,
        'rides': rides,
    }
    return render(request, 'ride/pwa/search.html', context)


# ============================================
# DRIVER VIEWS
# ============================================

@driver_required
def pwa_driver_dashboard(request):
    """Driver dashboard"""
    driver = request.user.driver_profile
    today = date.today()

    # Stats
    total_rides = Ride.objects.filter(driver=driver, status='COMPLETED').count()
    today_rides = Ride.objects.filter(driver=driver, requested_at__date=today).count()
    today_earnings = Ride.objects.filter(
        driver=driver,
        requested_at__date=today,
        status='COMPLETED'
    ).aggregate(total=Sum('total_fare'))['total'] or Decimal('0.00')

    # Active and pending rides
    active_ride = Ride.objects.filter(
        driver=driver,
        status__in=['ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS']
    ).first()

    context = {
        'driver': driver,
        'total_rides': total_rides,
        'today_rides': today_rides,
        'today_earnings': today_earnings,
        'active_ride': active_ride,
        'availability': driver.availability,
        'rating': driver.average_rating or Decimal('0.00'),
    }
    return render(request, 'ride/pwa/driver/dashboard.html', context)


@driver_required
def pwa_available_rides(request):
    """View available rides for drivers"""
    driver = request.user.driver_profile

    # Get pending rides assigned to this driver OR general requests
    available_rides = Ride.objects.filter(
        Q(driver=driver, status='REQUESTED') | Q(driver__isnull=True, status='REQUESTED')
    ).order_by('-requested_at')[:20]

    context = {
        'rides': available_rides,
        'driver': driver,
        'is_online': driver.availability == 'ONLINE',
    }
    return render(request, 'ride/pwa/driver/available_rides.html', context)


@driver_required
def pwa_accept_ride(request, ride_id):
    """Accept a ride request"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('ride_pwa:available_rides')
        
    driver = request.user.driver_profile
    
    logger.info(f"Accept ride request: Driver={driver.user.username}, Ride ID={ride_id}, Availability={driver.availability}")
    
    # Check if driver is online
    if driver.availability != 'ONLINE':
        logger.warning(f"Driver {driver.user.username} tried to accept ride but is {driver.availability}")
        messages.error(request, 'You must be ONLINE to accept rides. Go to your dashboard to change your status.')
        return redirect('ride_pwa:available_rides')
    
    # Try to get the ride
    try:
        ride = Ride.objects.get(pk=ride_id, status='REQUESTED')
        logger.info(f"Found ride {ride_id}: passenger={ride.passenger.username}, assigned_driver={ride.driver.user.username if ride.driver else 'None'}")
    except Ride.DoesNotExist:
        logger.warning(f"Ride {ride_id} not found or not in REQUESTED status")
        messages.error(request, 'This ride is no longer available. It may have been accepted by another driver.')
        return redirect('ride_pwa:available_rides')

    # Get driver's primary vehicle (with sensible fallback)
    primary_vehicle = Vehicle.objects.filter(driver=driver, is_primary=True, is_active=True).first()
    if not primary_vehicle:
        # Fallback: pick any active vehicle (most recently created)
        fallback_vehicle = (
            Vehicle.objects.filter(driver=driver, is_active=True)
            .order_by('-is_primary', '-created_at')
            .first()
        )
        if fallback_vehicle:
            logger.warning(
                f"Driver {driver.user.username} has no active primary vehicle — using active vehicle {fallback_vehicle.license_plate}"
            )
            primary_vehicle = fallback_vehicle
        else:
            logger.error(f"Driver {driver.user.username} has no active vehicle available")
            messages.error(
                request,
                'No active vehicle found. Please add or activate a vehicle in your profile before accepting rides.'
            )
            return redirect('ride_pwa:available_rides')

    # Accept the ride
    # Accept the ride
    # Double-check ride is still available
    ride.refresh_from_db()
    if ride.status != 'REQUESTED':
        logger.warning(f"Driver {driver.user.username} tried to accept ride {ride_id} but status is {ride.status}")
        messages.error(request, 'This ride was just accepted by another driver.')
        return redirect('ride_pwa:available_rides')
        
    logger.info(f"Driver {driver.user.username} accepting ride {ride_id}")
    
    ride.driver = driver
    ride.vehicle = primary_vehicle
    ride.status = 'ACCEPTED'
    ride.accepted_at = timezone.now()
    ride.save()
    
    logger.info(f"Ride {ride_id} status changed to ACCEPTED")

    # Update driver availability to ON_RIDE (valid choice)
    driver.availability = 'ON_RIDE'
    driver.save()
    
    logger.info(f"Driver {driver.user.username} availability changed to ON_RIDE")
    
    # Send SMS notification to passenger
    try:
        from utils.sms_utils import send_passenger_driver_accepted
        logger.info(f"Attempting to send SMS to passenger {ride.passenger.username} for ride {ride.ride_id}")
        sms_result = send_passenger_driver_accepted(ride.passenger, ride)
        
        logger.info(f"SMS result for passenger: {sms_result}")
        
        if sms_result.get('success'):
            messages.success(request, f'Ride #{ride.ride_id} accepted! Passenger notified via SMS.')
        else:
            messages.success(request, f'Ride #{ride.ride_id} accepted! Passenger will be notified through the app.')
    except Exception as e:
        logger.error(f"Failed to send passenger notification for ride {ride.ride_id}: {str(e)}", exc_info=True)
        messages.success(request, f'Ride #{ride.ride_id} accepted!')

    return redirect('ride_pwa:driver_ride_detail', ride_id=ride_id)


@driver_required
def pwa_reject_ride(request, ride_id):
    """Reject a ride request"""
    driver = request.user.driver_profile
    
    # Try to get the ride assigned to this driver
    try:
        ride = Ride.objects.get(pk=ride_id, driver=driver, status='REQUESTED')
    except Ride.DoesNotExist:
        messages.error(request, 'This ride is not available for rejection.')
        return redirect('ride_pwa:available_rides')

    if request.method == 'POST':
        rejection_reason = request.POST.get('reason', 'Driver declined the ride')
        
        # Update ride status
        ride.status = 'CANCELLED_BY_DRIVER'
        ride.cancelled_at = timezone.now()
        ride.cancellation_reason = rejection_reason
        
        # Clear driver assignment since they rejected
        ride.driver = None
        ride.vehicle = None
        ride.save()
        
        messages.success(request, 'Ride request declined.')
        
        # Optionally notify passenger via SMS
        try:
            from utils.sms_utils import ArkeselSMS
            sms = ArkeselSMS()
            passenger_phone = ride.passenger.profile.phone_number if hasattr(ride.passenger, 'profile') and ride.passenger.profile.phone_number else None
            
            if passenger_phone:
                message = (
                    f"SOMA KO RIDE - Driver Unavailable. "
                    f"Your ride request #{ride.ride_id} was declined by the driver. "
                    f"Please book another ride in the app."
                )
                sms.send_sms(passenger_phone, message)
        except Exception as e:
            logger.error(f"Failed to notify passenger of ride rejection for ride {ride.ride_id}: {str(e)}")
        
        return redirect('ride_pwa:available_rides')
    
    # GET request - show confirmation
    context = {
        'ride': ride,
        'driver': driver,
    }
    return render(request, 'ride/pwa/driver/reject_ride_confirm.html', context)


@driver_required
def pwa_active_rides(request):
    """View active rides"""
    driver = request.user.driver_profile
    rides = Ride.objects.filter(
        driver=driver,
        status__in=['ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS']
    ).order_by('-requested_at')

    context = {
        'rides': rides,
        'driver': driver,
    }
    return render(request, 'ride/pwa/driver/active_rides.html', context)


@driver_required
def pwa_driver_ride_detail(request, ride_id):
    """View ride details (driver perspective)"""
    driver = request.user.driver_profile
    ride = get_object_or_404(Ride, pk=ride_id, driver=driver)

    context = {
        'ride': ride,
        'driver': driver,
        'can_update_status': ride.status in ['ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS'],
    }
    return render(request, 'ride/pwa/driver/ride_detail.html', context)


@driver_required
def pwa_update_ride_status(request, ride_id):
    """Update ride status"""
    driver = request.user.driver_profile
    ride = get_object_or_404(Ride, pk=ride_id, driver=driver)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = ['ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED_BY_DRIVER']

        if new_status in valid_statuses:
            # Update timestamps
            if new_status == 'DRIVER_ARRIVED':
                ride.driver_arrived_at = timezone.now()
                ride.status = new_status
            elif new_status == 'IN_PROGRESS':
                ride.started_at = timezone.now()
                ride.status = new_status
            elif new_status == 'COMPLETED':
                # Driver marks as completed (two-way confirmation)
                ride.driver_completed = True
                ride.driver_completed_at = timezone.now()
                
                # Check if passenger has also confirmed
                if ride.passenger_completed:
                    # Both confirmed - complete the ride
                    ride.status = 'COMPLETED'
                    ride.completed_at = timezone.now()
                    
                    # Set driver availability back to ONLINE
                    driver.availability = 'ONLINE'
                    driver.total_rides += 1
                    driver.save()
                    
                    # Send SMS notification to passenger
                    try:
                        from utils.sms_utils import send_passenger_ride_completed
                        send_passenger_ride_completed(ride.passenger, ride)
                    except Exception as e:
                        logger.error(f"Failed to send completion SMS to passenger for ride {ride.ride_id}: {str(e)}")
                    
                    messages.success(request, 'Ride completed! Both you and passenger have confirmed.')
                else:
                    # Only driver confirmed, waiting for passenger
                    ride.status = 'IN_PROGRESS'  # Keep as in progress
                    messages.success(request, 'You marked the ride as complete. Waiting for passenger confirmation.')
                    
            elif new_status == 'CANCELLED_BY_DRIVER':
                ride.status = new_status
                ride.cancelled_at = timezone.now()
                ride.cancellation_reason = request.POST.get('reason', 'Cancelled by driver')
                
                # Set driver availability back to ONLINE
                driver.availability = 'ONLINE'
                driver.save()
                
                messages.success(request, 'Ride cancelled.')
            else:
                ride.status = new_status

            ride.save()

        return redirect('ride_pwa:driver_ride_detail', ride_id=ride_id)

    return redirect('ride_pwa:driver_dashboard')


@driver_required
def pwa_driver_earnings(request):
    """View earnings"""
    driver = request.user.driver_profile

    # Calculate earnings
    total_earnings = Ride.objects.filter(
        driver=driver,
        status='COMPLETED'
    ).aggregate(total=Sum('total_fare'))['total'] or Decimal('0.00')

    today = date.today()
    today_earnings = Ride.objects.filter(
        driver=driver,
        requested_at__date=today,
        status='COMPLETED'
    ).aggregate(total=Sum('total_fare'))['total'] or Decimal('0.00')

    this_week = today - timedelta(days=today.weekday())
    week_earnings = Ride.objects.filter(
        driver=driver,
        requested_at__date__gte=this_week,
        status='COMPLETED'
    ).aggregate(total=Sum('total_fare'))['total'] or Decimal('0.00')

    context = {
        'driver': driver,
        'total_earnings': total_earnings,
        'today_earnings': today_earnings,
        'week_earnings': week_earnings,
    }
    return render(request, 'ride/pwa/driver/earnings.html', context)


@driver_required
def pwa_driver_profile(request):
    """Driver profile"""
    driver = request.user.driver_profile

    if request.method == 'POST':
        # Update driver banking info (example)
        driver.bank_name = request.POST.get('bank_name', driver.bank_name)
        driver.account_number = request.POST.get('account_number', driver.account_number)
        driver.account_holder_name = request.POST.get('account_holder_name', driver.account_holder_name)
        driver.save()

        messages.success(request, 'Profile updated!')
        return redirect('ride_pwa:driver_profile')

    context = {
        'driver': driver,
    }
    return render(request, 'ride/pwa/driver/profile.html', context)


@driver_required
def pwa_driver_analytics(request):
    """Driver analytics"""
    driver = request.user.driver_profile

    completed_rides = Ride.objects.filter(driver=driver, status='COMPLETED').count()
    total_earnings = Ride.objects.filter(
        driver=driver, status='COMPLETED'
    ).aggregate(total=Sum('total_fare'))['total'] or Decimal('0.00')

    context = {
        'driver': driver,
        'total_rides': driver.total_rides,
        'completed_rides': completed_rides,
        'total_earnings': total_earnings,
        'avg_rating': driver.average_rating or Decimal('0.00'),
    }
    return render(request, 'ride/pwa/driver/analytics.html', context)


@driver_required
def pwa_toggle_availability(request):
    """Toggle driver availability"""
    driver = request.user.driver_profile

    if request.method == 'POST':
        if driver.availability == 'ONLINE':
            driver.availability = 'OFFLINE'
            messages.success(request, 'You are now offline.')
        elif driver.availability == 'OFFLINE':
            # Check if driver is approved
            if driver.status == 'APPROVED':
                driver.availability = 'ONLINE'
                messages.success(request, 'You are now online and can accept rides!')
            else:
                messages.error(request, 'Your driver profile must be approved first.')
        else:
            messages.warning(request, 'You cannot change availability while on a ride.')

        driver.save()

    return redirect('ride_pwa:driver_dashboard')


@login_required
def pwa_notifications(request):
    """View notifications"""
    # Placeholder for notifications functionality
    context = {
        'notifications': [],
    }
    return render(request, 'ride/pwa/notifications.html', context)
