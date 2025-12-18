from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Avg
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from ride.models import (
    DriverProfile,
    Ride,
    Vehicle,
    VehicleCategory,
    Rating,
    Payment
)


# Ride Home View
@login_required
def ride_home(request):
    """
    Home page for ride service showing available vehicle categories
    and recent rides for the user
    """
    # Get active vehicle categories
    vehicle_categories = VehicleCategory.objects.filter(
        is_active=True
    ).order_by('vehicle_type', 'base_fare')

    # Get user's recent rides (last 5)
    recent_rides = Ride.objects.filter(
        passenger=request.user
    ).select_related(
        'driver',
        'driver__user',
        'vehicle',
        'vehicle_category'
    ).order_by('-requested_at')[:5]

    # Check if user is a driver
    is_driver = hasattr(request.user, 'driver_profile')
    driver_profile = None
    if is_driver:
        driver_profile = request.user.driver_profile

    # Get available drivers count
    available_drivers_count = DriverProfile.objects.filter(
        status='APPROVED',
        availability='ONLINE'
    ).count()

    context = {
        'vehicle_categories': vehicle_categories,
        'recent_rides': recent_rides,
        'is_driver': is_driver,
        'driver_profile': driver_profile,
        'available_drivers_count': available_drivers_count,
    }

    return render(request, 'ride/ride_home.html', context)


# Book Ride View
@login_required
@require_http_methods(["GET", "POST"])
def book_ride(request):
    """
    Book a new ride with fare calculation
    """
    if request.method == 'POST':
        # Get form data
        pickup_address = request.POST.get('pickup_address')
        pickup_latitude = request.POST.get('pickup_latitude')
        pickup_longitude = request.POST.get('pickup_longitude')

        dropoff_address = request.POST.get('dropoff_address')
        dropoff_latitude = request.POST.get('dropoff_latitude')
        dropoff_longitude = request.POST.get('dropoff_longitude')

        driver_id = request.POST.get('driver_id')
        vehicle_category_id = request.POST.get('vehicle_category')
        passenger_count = request.POST.get('passenger_count', 1)
        special_requests = request.POST.get('special_requests', '')

        estimated_distance_km = request.POST.get('estimated_distance_km')
        estimated_duration_minutes = request.POST.get('estimated_duration_minutes')
        payment_method = request.POST.get('payment_method', 'CASH')

        # Validation
        if not all([pickup_address, pickup_latitude, pickup_longitude,
                   dropoff_address, dropoff_latitude, dropoff_longitude,
                   driver_id, vehicle_category_id, estimated_distance_km, estimated_duration_minutes]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('ride:book_ride')

        try:
            # Get driver and vehicle category
            driver_profile = get_object_or_404(DriverProfile, id=driver_id, status='APPROVED')
            vehicle_category = get_object_or_404(VehicleCategory, id=vehicle_category_id, is_active=True)

            # Get driver's primary vehicle
            primary_vehicle = driver_profile.vehicles.filter(
                is_active=True,
                is_primary=True,
                category=vehicle_category
            ).first()

            if not primary_vehicle:
                messages.error(request, 'Selected driver does not have a matching vehicle available.')
                return redirect('ride:book_ride')

            # Convert to Decimal
            estimated_distance_km = Decimal(str(estimated_distance_km))
            estimated_duration_minutes = int(estimated_duration_minutes)
            passenger_count = int(passenger_count)

            # Check passenger count
            if passenger_count > vehicle_category.max_passengers:
                messages.error(
                    request,
                    f'This vehicle category can only accommodate {vehicle_category.max_passengers} passengers.'
                )
                return redirect('ride:book_ride')

            # Create ride instance with driver and vehicle assigned
            ride = Ride(
                passenger=request.user,
                driver=driver_profile,
                vehicle=primary_vehicle,
                pickup_address=pickup_address,
                pickup_latitude=Decimal(str(pickup_latitude)),
                pickup_longitude=Decimal(str(pickup_longitude)),
                dropoff_address=dropoff_address,
                dropoff_latitude=Decimal(str(dropoff_latitude)),
                dropoff_longitude=Decimal(str(dropoff_longitude)),
                vehicle_category=vehicle_category,
                passenger_count=passenger_count,
                special_requests=special_requests,
                estimated_distance_km=estimated_distance_km,
                estimated_duration_minutes=estimated_duration_minutes,
                payment_method=payment_method,
                status='REQUESTED',
                requested_at=timezone.now()
            )

            # Calculate fare
            ride.calculate_fare()

            # Save ride
            ride.save()

            # Send SMS notification to driver with ride link
            from ride.notifications import notify_ride_requested
            notify_ride_requested(ride)

            # Send SMS booking confirmation to user
            from accounts.notification_service import send_notification
            from django.urls import reverse
            from django.contrib.sites.models import Site

            try:
                current_site = Site.objects.get_current()
                domain = current_site.domain
            except:
                domain = 'localhost:8000'  # Fallback for development

            ride_url = f'https://{domain}{reverse("ride:ride_detail", args=[ride.ride_id])}'

            # SMS confirmation for user
            user_sms_message = (
                f'Ride Booked Successfully!\n'
                f'Ride ID: {ride.ride_id}\n'
                f'Driver: {driver_profile.user.get_full_name() or driver_profile.user.username}\n'
                f'Vehicle: {primary_vehicle.category.name}\n'
                f'Total Fare: GHS {ride.total_fare:.2f}\n'
                f'Track your ride: {ride_url}'
            )

            send_notification(
                user=request.user,
                notification_type='ride_booked',
                title='Ride Booking Confirmation',
                message=user_sms_message,
                channels=['in_app', 'sms'],
                reference_id=str(ride.ride_id),
                reference_type='Ride',
                data={
                    'ride_id': str(ride.ride_id),
                    'driver': driver_profile.user.get_full_name() or driver_profile.user.username,
                    'vehicle': primary_vehicle.category.name,
                    'fare': str(ride.total_fare),
                    'ride_url': ride_url
                }
            )

            messages.success(
                request,
                f'Ride booked successfully! Your ride ID is {ride.ride_id}. Total fare: GHS {ride.total_fare:.2f}. SMS confirmation sent!'
            )
            return redirect('ride:ride_detail', ride_id=ride.ride_id)

        except Exception as e:
            messages.error(request, f'Error booking ride: {str(e)}')
            return redirect('ride:book_ride')

    # GET request - show booking form
    vehicle_categories = VehicleCategory.objects.filter(
        is_active=True
    ).order_by('vehicle_type', 'base_fare')

    # Get available online drivers with their primary vehicles
    # Filter by location (drivers in same location as user) and limit to first 3
    from django.db.models import Prefetch
    from math import radians, cos, sin, asin, sqrt

    # Try to get user's location from session or use default (Accra, Ghana)
    user_lat = request.session.get('user_latitude', 5.6037)
    user_lng = request.session.get('user_longitude', -0.1870)

    # Get all available drivers
    all_drivers = DriverProfile.objects.filter(
        status='APPROVED',
        availability='ONLINE'
    ).select_related('user').prefetch_related(
        Prefetch('vehicles',
                queryset=Vehicle.objects.filter(is_active=True, is_primary=True).select_related('category'),
                to_attr='primary_vehicles')
    ).annotate(
        avg_rating=Avg('ratings_received__rating')
    ).filter(vehicles__is_active=True, vehicles__is_primary=True).distinct()

    # Calculate distance for each driver and filter by proximity (within 20km)
    def haversine(lon1, lat1, lon2, lat2):
        """Calculate the great circle distance between two points on the earth"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    # Filter drivers within 20km and sort by distance
    nearby_drivers = []
    drivers_without_location = []

    for driver in all_drivers:
        # Check if driver has location data
        if driver.current_latitude and driver.current_longitude:
            distance = haversine(
                float(user_lng), float(user_lat),
                float(driver.current_longitude), float(driver.current_latitude)
            )
            if distance <= 20:  # Within 20km radius
                driver.distance_from_user = distance
                nearby_drivers.append(driver)
        else:
            # Driver without location - add to end of list with max distance
            driver.distance_from_user = 9999  # Very high distance to sort to end
            drivers_without_location.append(driver)

    # Sort by distance and combine lists
    nearby_drivers.sort(key=lambda x: x.distance_from_user)
    all_sorted_drivers = nearby_drivers + drivers_without_location

    # Limit to first 3 for main display
    available_drivers = all_sorted_drivers[:3]

    # Get related/other drivers for the slider (remaining drivers)
    related_drivers = all_sorted_drivers[3:9] if len(all_sorted_drivers) > 3 else []

    context = {
        'vehicle_categories': vehicle_categories,
        'available_drivers': available_drivers,
        'related_drivers': related_drivers,
    }

    return render(request, 'ride/book_ride.html', context)


# Ride Detail View
@login_required
def ride_detail(request, ride_id):
    """
    View details of a specific ride
    """
    ride = get_object_or_404(
        Ride.objects.select_related(
            'passenger',
            'driver',
            'driver__user',
            'vehicle',
            'vehicle__category',
            'vehicle_category'
        ),
        ride_id=ride_id
    )

    # Check if user is authorized to view this ride
    is_passenger = ride.passenger == request.user
    is_driver = hasattr(request.user, 'driver_profile') and ride.driver == request.user.driver_profile

    if not (is_passenger or is_driver):
        messages.error(request, 'You are not authorized to view this ride.')
        return redirect('ride:ride_home')

    # Get tracking points if ride is active
    tracking_points = []
    if ride.is_active():
        tracking_points = ride.tracking_points.order_by('-recorded_at')[:50]

    # Get ratings for this ride
    ratings = ride.ratings.all()

    # Check if user can rate
    can_rate = False
    has_rated = False
    if is_passenger and ride.status == 'COMPLETED':
        has_rated = Rating.objects.filter(
            ride=ride,
            rating_type='PASSENGER_TO_DRIVER'
        ).exists()
        can_rate = not has_rated

    context = {
        'ride': ride,
        'is_passenger': is_passenger,
        'is_driver': is_driver,
        'tracking_points': tracking_points,
        'ratings': ratings,
        'can_rate': can_rate,
        'has_rated': has_rated,
    }

    return render(request, 'ride/ride_detail.html', context)


# Track Ride View
@login_required
def track_ride(request, ride_id):
    """
    Real-time tracking page for active rides
    """
    ride = get_object_or_404(
        Ride.objects.select_related(
            'passenger',
            'driver',
            'driver__user',
            'vehicle'
        ),
        ride_id=ride_id
    )

    # Check authorization
    is_passenger = ride.passenger == request.user
    is_driver = hasattr(request.user, 'driver_profile') and ride.driver == request.user.driver_profile

    if not (is_passenger or is_driver):
        messages.error(request, 'You are not authorized to track this ride.')
        return redirect('ride:ride_home')

    # Check if ride is trackable
    if not ride.is_active():
        messages.info(request, 'This ride is not currently active.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Get latest tracking point
    latest_tracking = ride.tracking_points.order_by('-recorded_at').first()

    # Get driver's current location if available
    driver_location = None
    if ride.driver and ride.driver.current_latitude and ride.driver.current_longitude:
        driver_location = {
            'latitude': float(ride.driver.current_latitude),
            'longitude': float(ride.driver.current_longitude),
            'last_update': ride.driver.last_location_update
        }

    context = {
        'ride': ride,
        'is_passenger': is_passenger,
        'is_driver': is_driver,
        'latest_tracking': latest_tracking,
        'driver_location': driver_location,
    }

    return render(request, 'ride/track_ride.html', context)


# Ride History View
@login_required
def ride_history(request):
    """
    View all rides for the current user with pagination and filters
    """
    # Base query
    rides = Ride.objects.filter(
        passenger=request.user
    ).select_related(
        'driver',
        'driver__user',
        'vehicle',
        'vehicle_category'
    ).order_by('-requested_at')

    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        rides = rides.filter(status=status_filter)

    date_from = request.GET.get('date_from')
    if date_from:
        rides = rides.filter(requested_at__date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        rides = rides.filter(requested_at__date__lte=date_to)

    # Search by ride ID or addresses
    search_query = request.GET.get('search')
    if search_query:
        rides = rides.filter(
            Q(ride_id__icontains=search_query) |
            Q(pickup_address__icontains=search_query) |
            Q(dropoff_address__icontains=search_query)
        )

    # Calculate statistics
    total_rides = rides.count()
    completed_rides = rides.filter(status='COMPLETED').count()
    total_spent = sum(
        ride.total_fare for ride in rides.filter(status='COMPLETED', payment_status='PAID')
    )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(rides, 10)  # 10 rides per page

    try:
        rides_page = paginator.page(page)
    except PageNotAnInteger:
        rides_page = paginator.page(1)
    except EmptyPage:
        rides_page = paginator.page(paginator.num_pages)

    context = {
        'rides': rides_page,
        'total_rides': total_rides,
        'completed_rides': completed_rides,
        'total_spent': total_spent,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'status_choices': Ride.STATUS_CHOICES,
    }

    return render(request, 'ride/ride_history.html', context)


# Driver Dashboard View
@login_required
def driver_dashboard(request):
    """
    Dashboard for drivers showing statistics and active rides
    """
    # Check if user is a driver
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'You need a driver profile to access this page.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile

    # Check if driver is approved
    if driver_profile.status != 'APPROVED':
        messages.warning(
            request,
            f'Your driver profile is currently {driver_profile.get_status_display()}. '
            'Please wait for approval to start accepting rides.'
        )

    # Get driver's vehicles
    vehicles = driver_profile.vehicles.filter(is_active=True).select_related('category')
    primary_vehicle = vehicles.filter(is_primary=True).first()

    # Get active ride for this driver
    active_ride = Ride.objects.filter(
        driver=driver_profile,
        status__in=['ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS']
    ).select_related('passenger', 'vehicle', 'vehicle_category').first()

    # Calculate statistics
    total_rides = driver_profile.total_rides or 0
    average_rating = driver_profile.average_rating or Decimal('0.00')

    # Today's statistics
    today = timezone.now().date()
    today_rides = Ride.objects.filter(
        driver=driver_profile,
        requested_at__date=today
    )
    today_completed = today_rides.filter(status='COMPLETED').count()

    # Calculate today's earnings
    today_payments = Payment.objects.filter(
        ride__driver=driver_profile,
        ride__completed_at__date=today,
        status='COMPLETED'
    )
    today_earnings = Decimal('0.00')
    for payment in today_payments:
        if payment.driver_payout:
            today_earnings += payment.driver_payout

    # This week's statistics
    week_start = timezone.now() - timezone.timedelta(days=7)
    week_rides = Ride.objects.filter(
        driver=driver_profile,
        requested_at__gte=week_start,
        status='COMPLETED'
    ).count()

    # Recent completed rides
    recent_rides = Ride.objects.filter(
        driver=driver_profile,
        status='COMPLETED'
    ).select_related('passenger', 'vehicle', 'vehicle_category').order_by('-completed_at')[:5]

    # Pending ride requests for this driver
    # Include both: rides directly assigned to this driver, and open requests matching vehicle category
    if primary_vehicle:
        pending_requests = Ride.objects.filter(
            Q(driver=driver_profile, status='REQUESTED') |  # Direct bookings
            Q(driver__isnull=True, status='REQUESTED', vehicle_category=primary_vehicle.category)  # Open requests
        ).select_related('passenger', 'vehicle', 'vehicle_category').order_by('-requested_at')[:10]
    else:
        # Only show direct bookings if no primary vehicle set
        pending_requests = Ride.objects.filter(
            driver=driver_profile,
            status='REQUESTED'
        ).select_related('passenger', 'vehicle', 'vehicle_category').order_by('-requested_at')[:10]

    # All rides for table (recent 20)
    all_rides = Ride.objects.filter(
        driver=driver_profile
    ).select_related('passenger', 'vehicle', 'vehicle_category').order_by('-requested_at')[:20]

    context = {
        'driver_profile': driver_profile,
        'vehicles': vehicles,
        'primary_vehicle': primary_vehicle,
        'active_ride': active_ride,
        'total_rides': total_rides,
        'average_rating': average_rating,
        'today_completed': today_completed,
        'today_earnings': today_earnings,
        'week_rides': week_rides,
        'recent_rides': recent_rides,
        'pending_requests': pending_requests,
        'all_rides': all_rides,
    }

    return render(request, 'ride/driver_dashboard.html', context)


# Driver Rides View
@login_required
def driver_rides(request):
    """
    View all rides for the driver with filters and pagination
    """
    # Check if user is a driver
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'You need a driver profile to access this page.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile

    # Base query
    rides = Ride.objects.filter(
        driver=driver_profile
    ).select_related(
        'passenger',
        'vehicle',
        'vehicle_category'
    ).order_by('-requested_at')

    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        rides = rides.filter(status=status_filter)

    date_from = request.GET.get('date_from')
    if date_from:
        rides = rides.filter(requested_at__date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        rides = rides.filter(requested_at__date__lte=date_to)

    # Search
    search_query = request.GET.get('search')
    if search_query:
        rides = rides.filter(
            Q(ride_id__icontains=search_query) |
            Q(passenger__username__icontains=search_query) |
            Q(passenger__first_name__icontains=search_query) |
            Q(passenger__last_name__icontains=search_query) |
            Q(pickup_address__icontains=search_query) |
            Q(dropoff_address__icontains=search_query)
        )

    # Calculate statistics
    total_rides_count = rides.count()
    completed_rides_count = rides.filter(status='COMPLETED').count()
    total_earnings = sum(
        payment.driver_payout for payment in Payment.objects.filter(
            ride__driver=driver_profile,
            ride__in=rides.filter(status='COMPLETED'),
            status='COMPLETED'
        )
    )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(rides, 15)  # 15 rides per page

    try:
        rides_page = paginator.page(page)
    except PageNotAnInteger:
        rides_page = paginator.page(1)
    except EmptyPage:
        rides_page = paginator.page(paginator.num_pages)

    context = {
        'rides': rides_page,
        'driver_profile': driver_profile,
        'total_rides_count': total_rides_count,
        'completed_rides_count': completed_rides_count,
        'total_earnings': total_earnings,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'status_choices': Ride.STATUS_CHOICES,
    }

    return render(request, 'ride/driver_rides.html', context)


# Accept Ride View
@login_required
@require_http_methods(["POST"])
def accept_ride(request, ride_id):
    """
    Driver accepts a ride request
    """
    # Check if user is a driver
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'Only drivers can accept rides.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile

    # Check if driver is approved and available
    if driver_profile.status != 'APPROVED':
        messages.error(request, 'Your driver profile must be approved to accept rides.')
        return redirect('ride:driver_dashboard')

    if driver_profile.availability != 'ONLINE':
        messages.error(request, 'You must be online to accept rides.')
        return redirect('ride:driver_dashboard')

    # Check if driver has an active ride
    has_active_ride = Ride.objects.filter(
        driver=driver_profile,
        status__in=['ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS']
    ).exists()

    if has_active_ride:
        messages.error(request, 'You already have an active ride. Complete it before accepting another.')
        return redirect('ride:driver_dashboard')

    # Get the ride
    ride = get_object_or_404(Ride, ride_id=ride_id)

    # Check if ride is still available
    if ride.status != 'REQUESTED':
        messages.error(request, 'This ride is no longer available.')
        return redirect('ride:driver_dashboard')

    # Get driver's primary vehicle
    primary_vehicle = driver_profile.vehicles.filter(
        is_active=True,
        is_primary=True
    ).first()

    if not primary_vehicle:
        messages.error(request, 'You need to set a primary vehicle before accepting rides.')
        return redirect('ride:driver_dashboard')

    # Check if vehicle category matches
    if primary_vehicle.category != ride.vehicle_category:
        messages.error(
            request,
            f'Your vehicle category ({primary_vehicle.category}) does not match the requested category ({ride.vehicle_category}).'
        )
        return redirect('ride:driver_dashboard')

    # Accept the ride
    ride.driver = driver_profile
    ride.vehicle = primary_vehicle
    ride.status = 'ACCEPTED'
    ride.accepted_at = timezone.now()
    ride.save()

    # Update driver availability
    driver_profile.availability = 'ON_RIDE'
    driver_profile.save()

    messages.success(request, f'Ride {ride.ride_id} accepted successfully!')
    return redirect('ride:ride_detail', ride_id=ride.ride_id)


# Complete Ride View
@login_required
@require_http_methods(["POST"])
def complete_ride(request, ride_id):
    """
    Driver completes a ride
    """
    # Check if user is a driver
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'Only drivers can complete rides.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile

    # Get the ride
    ride = get_object_or_404(Ride, ride_id=ride_id)

    # Check if this driver owns the ride
    if ride.driver != driver_profile:
        messages.error(request, 'You can only complete your own rides.')
        return redirect('ride:driver_dashboard')

    # Check if ride is in progress
    if ride.status != 'IN_PROGRESS':
        messages.error(request, 'Only rides in progress can be completed.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Get actual distance and duration from POST data
    actual_distance_km = request.POST.get('actual_distance_km')
    actual_duration_minutes = request.POST.get('actual_duration_minutes')

    # Update ride
    ride.status = 'COMPLETED'
    ride.completed_at = timezone.now()

    if actual_distance_km:
        ride.actual_distance_km = Decimal(str(actual_distance_km))
    else:
        ride.actual_distance_km = ride.estimated_distance_km

    if actual_duration_minutes:
        ride.actual_duration_minutes = int(actual_duration_minutes)
    else:
        # Calculate duration from started_at to now
        if ride.started_at:
            duration = (timezone.now() - ride.started_at).total_seconds() / 60
            ride.actual_duration_minutes = int(duration)
        else:
            ride.actual_duration_minutes = ride.estimated_duration_minutes

    # Mark payment as paid if cash
    if ride.payment_method == 'CASH':
        ride.payment_status = 'PAID'

    ride.save()

    # Update driver stats
    driver_profile.total_rides += 1
    driver_profile.availability = 'ONLINE'
    driver_profile.save()

    # Create payment record
    payment = Payment.objects.create(
        ride=ride,
        payer=ride.passenger,
        recipient=driver_profile,
        transaction_type='RIDE_PAYMENT',
        amount=ride.total_fare,
        payment_method=ride.payment_method,
        status='COMPLETED' if ride.payment_method == 'CASH' else 'PENDING'
    )
    payment.calculate_driver_payout()
    payment.save()

    messages.success(
        request,
        f'Ride completed successfully! Fare: GHS {ride.total_fare:.2f}, Your payout: GHS {payment.driver_payout:.2f}'
    )
    return redirect('ride:ride_detail', ride_id=ride.ride_id)


# Cancel Ride View
@login_required
@require_http_methods(["POST"])
def cancel_ride(request, ride_id):
    """
    Cancel a ride (by passenger or driver)
    """
    ride = get_object_or_404(Ride, ride_id=ride_id)

    # Check authorization
    is_passenger = ride.passenger == request.user
    is_driver = hasattr(request.user, 'driver_profile') and ride.driver == request.user.driver_profile

    if not (is_passenger or is_driver):
        messages.error(request, 'You are not authorized to cancel this ride.')
        return redirect('ride:ride_home')

    # Check if ride can be cancelled
    if not ride.can_be_cancelled():
        messages.error(request, f'Rides with status "{ride.get_status_display()}" cannot be cancelled.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Get cancellation reason
    cancellation_reason = request.POST.get('cancellation_reason', 'No reason provided')

    # Update ride status
    if is_passenger:
        ride.status = 'CANCELLED_BY_PASSENGER'
    else:
        ride.status = 'CANCELLED_BY_DRIVER'
        # Make driver available again
        if ride.driver:
            ride.driver.availability = 'ONLINE'
            ride.driver.save()

    ride.cancelled_at = timezone.now()
    ride.cancellation_reason = cancellation_reason
    ride.save()

    messages.info(request, 'Ride cancelled successfully.')
    return redirect('ride:ride_detail', ride_id=ride.ride_id)


# Start Ride View (Driver marks ride as started)
@login_required
@require_http_methods(["POST"])
def start_ride(request, ride_id):
    """
    Driver starts the ride (marks as in progress)
    """
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'Only drivers can start rides.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile
    ride = get_object_or_404(Ride, ride_id=ride_id)

    # Check if this driver owns the ride
    if ride.driver != driver_profile:
        messages.error(request, 'You can only start your own rides.')
        return redirect('ride:driver_dashboard')

    # Check if ride status is appropriate
    if ride.status not in ['ACCEPTED', 'DRIVER_ARRIVED']:
        messages.error(request, 'This ride cannot be started.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Start the ride
    ride.status = 'IN_PROGRESS'
    ride.started_at = timezone.now()
    ride.save()

    messages.success(request, 'Ride started! Drive safely.')
    return redirect('ride:track_ride', ride_id=ride.ride_id)


# Mark Driver Arrived View
@login_required
@require_http_methods(["POST"])
def driver_arrived(request, ride_id):
    """
    Driver marks arrival at pickup location
    """
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'Only drivers can mark arrival.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile
    ride = get_object_or_404(Ride, ride_id=ride_id)

    # Check if this driver owns the ride
    if ride.driver != driver_profile:
        messages.error(request, 'You can only update your own rides.')
        return redirect('ride:driver_dashboard')

    # Check if ride status is appropriate
    if ride.status != 'ACCEPTED':
        messages.error(request, 'Invalid ride status.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Mark arrived
    ride.status = 'DRIVER_ARRIVED'
    ride.driver_arrived_at = timezone.now()
    ride.save()

    messages.success(request, 'Arrival confirmed. Waiting for passenger.')
    return redirect('ride:ride_detail', ride_id=ride.ride_id)


# Available Rides View (for drivers)
@login_required
def available_rides(request):
    """
    Show available ride requests for drivers
    """
    # Check if user is a driver
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'You need a driver profile to access this page.')
        return redirect('ride:ride_home')

    driver_profile = request.user.driver_profile

    # Check if driver is approved and online
    if driver_profile.status != 'APPROVED':
        messages.warning(request, 'Your driver profile must be approved to view available rides.')
        return redirect('ride:driver_dashboard')

    # Get driver's primary vehicle category
    primary_vehicle = driver_profile.vehicles.filter(
        is_active=True,
        is_primary=True
    ).select_related('category').first()

    if not primary_vehicle:
        messages.warning(request, 'Please set a primary vehicle to view available rides.')
        return redirect('ride:driver_dashboard')

    # Get available rides matching driver's vehicle category
    available_rides_list = Ride.objects.filter(
        status='REQUESTED',
        vehicle_category=primary_vehicle.category
    ).select_related(
        'passenger',
        'vehicle_category'
    ).order_by('-requested_at')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(available_rides_list, 10)

    try:
        rides_page = paginator.page(page)
    except PageNotAnInteger:
        rides_page = paginator.page(1)
    except EmptyPage:
        rides_page = paginator.page(paginator.num_pages)

    context = {
        'rides': rides_page,
        'driver_profile': driver_profile,
        'primary_vehicle': primary_vehicle,
    }

    return render(request, 'ride/available_rides.html', context)


# Rate Ride View
@login_required
@require_http_methods(["POST"])
def rate_ride(request, ride_id):
    """
    Passenger rates driver after completed ride
    """
    ride = get_object_or_404(Ride, ride_id=ride_id)

    # Check if user is the passenger
    if ride.passenger != request.user:
        messages.error(request, 'Only passengers can rate rides.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Check if ride is completed
    if ride.status != 'COMPLETED':
        messages.error(request, 'You can only rate completed rides.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Check if already rated
    existing_rating = Rating.objects.filter(
        ride=ride,
        rating_type='PASSENGER_TO_DRIVER'
    ).first()

    if existing_rating:
        messages.warning(request, 'You have already rated this ride.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    # Get rating data
    rating_value = request.POST.get('rating')
    review = request.POST.get('review', '')
    cleanliness_rating = request.POST.get('cleanliness_rating')
    punctuality_rating = request.POST.get('punctuality_rating')
    communication_rating = request.POST.get('communication_rating')
    driving_rating = request.POST.get('driving_rating')

    if not rating_value:
        messages.error(request, 'Please provide a rating.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    try:
        # Create rating
        rating = Rating.objects.create(
            ride=ride,
            rating_type='PASSENGER_TO_DRIVER',
            rater=request.user,
            rating=int(rating_value),
            review=review
        )

        # Add optional detailed ratings
        if cleanliness_rating:
            rating.cleanliness_rating = int(cleanliness_rating)
        if punctuality_rating:
            rating.punctuality_rating = int(punctuality_rating)
        if communication_rating:
            rating.communication_rating = int(communication_rating)
        if driving_rating:
            rating.driving_rating = int(driving_rating)

        rating.save()

        messages.success(request, 'Thank you for rating your ride!')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    except Exception as e:
        messages.error(request, f'Error submitting rating: {str(e)}')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)


@login_required
@require_http_methods(["POST"])
def confirm_cash_payment(request, ride_id):
    """
    Confirm cash payment for a ride
    """
    ride = get_object_or_404(Ride, ride_id=ride_id, passenger=request.user)

    # Verify payment is pending
    if ride.payment_status == 'PAID':
        messages.info(request, 'Payment has already been confirmed for this ride.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    if ride.payment_method != 'CASH':
        messages.error(request, 'This ride was not set for cash payment.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    try:
        # Update payment status
        ride.payment_status = 'PAID'

        # Update ride status to COMPLETED if not already
        if ride.status != 'COMPLETED':
            ride.status = 'COMPLETED'
            if not ride.completed_at:
                ride.completed_at = timezone.now()

        ride.save()

        # Create or update payment record
        payment, created = Payment.objects.get_or_create(
            ride=ride,
            payer=request.user,
            defaults={
                'recipient': ride.driver,
                'amount': ride.total_fare,
                'driver_payout': ride.total_fare,  # No commission for now
                'payment_method': 'CASH',
                'status': 'COMPLETED',
                'transaction_reference': f'CASH-{ride.ride_id}',
                'completed_at': timezone.now()
            }
        )

        if not created:
            payment.status = 'COMPLETED'
            payment.completed_at = timezone.now()
            payment.save()

        messages.success(request, 'Cash payment confirmed successfully! Ride completed.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    except Exception as e:
        messages.error(request, f'Error confirming payment: {str(e)}')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)


@login_required
@require_http_methods(["POST"])
def initiate_payment(request, ride_id):
    """
    Initiate mobile money payment via Paystack
    """
    import requests
    from django.conf import settings

    ride = get_object_or_404(Ride, ride_id=ride_id, passenger=request.user)

    if ride.payment_status == 'PAID':
        messages.info(request, 'Payment has already been completed for this ride.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    if ride.payment_method == 'CASH':
        messages.error(request, 'This ride is set for cash payment. Please use the cash confirmation button.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    try:
        # Get Paystack secret key from settings
        paystack_secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)

        if not paystack_secret_key:
            messages.error(request, 'Payment system is not configured. Please contact support.')
            return redirect('ride:ride_detail', ride_id=ride.ride_id)

        # Get driver's phone number (recipient)
        if not ride.driver or not hasattr(ride.driver, 'phone_number'):
            messages.error(request, 'Driver phone number not available for payment.')
            return redirect('ride:ride_detail', ride_id=ride.ride_id)

        driver_phone = ride.driver.phone_number
        # Format phone number for Ghana (remove + and spaces)
        driver_phone = driver_phone.replace('+', '').replace(' ', '').replace('-', '')

        # Prepare Paystack payment data
        amount_in_pesewas = int(float(ride.total_fare) * 100)  # Paystack uses pesewas

        payment_data = {
            'email': request.user.email,
            'amount': amount_in_pesewas,
            'currency': 'GHS',
            'reference': f'RIDE-{ride.ride_id}',
            'callback_url': request.build_absolute_uri(f'/ride/payment/verify/{ride.ride_id}/'),
            'metadata': {
                'ride_id': str(ride.ride_id),
                'passenger_name': request.user.get_full_name(),
                'driver_phone': driver_phone,
                'payment_type': 'ride_payment'
            },
            'channels': ['mobile_money'],
            'mobile_money': {
                'phone': driver_phone,
                'provider': 'mtn'  # Default to MTN, can be changed
            }
        }

        # Make request to Paystack
        headers = {
            'Authorization': f'Bearer {paystack_secret_key}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json=payment_data,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            if data['status']:
                # Create pending payment record
                Payment.objects.create(
                    ride=ride,
                    payer=request.user,
                    recipient=ride.driver,
                    amount=ride.total_fare,
                    driver_payout=ride.total_fare,  # No commission for now
                    payment_method='MOBILE_MONEY',
                    status='PENDING',
                    transaction_reference=data['data']['reference'],
                    external_transaction_id=data['data']['reference']
                )

                # Redirect to Paystack payment page
                return redirect(data['data']['authorization_url'])
            else:
                messages.error(request, f"Payment initialization failed: {data.get('message', 'Unknown error')}")
                return redirect('ride:ride_detail', ride_id=ride.ride_id)
        else:
            messages.error(request, 'Failed to connect to payment system. Please try again.')
            return redirect('ride:ride_detail', ride_id=ride.ride_id)

    except Exception as e:
        messages.error(request, f'Error initiating payment: {str(e)}')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)


@login_required
def verify_payment(request, ride_id):
    """
    Verify payment from Paystack callback
    """
    import requests
    from django.conf import settings

    ride = get_object_or_404(Ride, ride_id=ride_id, passenger=request.user)
    reference = request.GET.get('reference')

    if not reference:
        messages.error(request, 'Invalid payment reference.')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)

    try:
        paystack_secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)

        if not paystack_secret_key:
            messages.error(request, 'Payment system is not configured.')
            return redirect('ride:ride_detail', ride_id=ride.ride_id)

        # Verify transaction with Paystack
        headers = {
            'Authorization': f'Bearer {paystack_secret_key}'
        }

        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()

            if data['status'] and data['data']['status'] == 'success':
                # Update payment record
                payment = Payment.objects.filter(
                    ride=ride,
                    external_transaction_id=reference
                ).first()

                if payment:
                    payment.status = 'COMPLETED'
                    payment.completed_at = timezone.now()
                    payment.save()

                # Update ride payment status
                ride.payment_status = 'PAID'
                ride.save()

                messages.success(request, 'Payment successful! Thank you.')
                return redirect('ride:ride_detail', ride_id=ride.ride_id)
            else:
                messages.error(request, 'Payment verification failed. Please contact support if amount was deducted.')
                return redirect('ride:ride_detail', ride_id=ride.ride_id)
        else:
            messages.error(request, 'Could not verify payment. Please contact support.')
            return redirect('ride:ride_detail', ride_id=ride.ride_id)

    except Exception as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
        return redirect('ride:ride_detail', ride_id=ride.ride_id)