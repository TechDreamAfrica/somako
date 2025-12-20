from accounts.notification_service import send_notification


def notify_ride_requested(ride):
    """Notify driver when a new ride is requested via SMS with link to view ride"""
    if ride.driver:
        # Build the ride detail URL
        from django.urls import reverse
        from django.contrib.sites.models import Site

        try:
            current_site = Site.objects.get_current()
            domain = current_site.domain
        except:
            domain = 'localhost:8000'  # Fallback for development

        ride_url = f'https://{domain}{reverse("ride:ride_detail", args=[ride.ride_id])}'

        # SMS message with link
        sms_message = (
            f'New Ride Request!\n'
            f'From: {ride.passenger.get_full_name() or ride.passenger.username}\n'
            f'Pickup: {ride.pickup_address[:50]}...\n'
            f'Fare: GHS {ride.total_fare}\n'
            f'View & Accept: {ride_url}'
        )

        # Send via notification service
        send_notification(
            user=ride.driver.user,
            notification_type='ride_requested',
            title='New Ride Request',
            message=sms_message,
            channels=['in_app', 'sms'],
            reference_id=str(ride.ride_id),
            reference_type='Ride',
            data={
                'ride_id': str(ride.ride_id),
                'pickup': ride.pickup_address,
                'dropoff': ride.dropoff_address,
                'fare': str(ride.total_fare),
                'ride_url': ride_url
            }
        )

        # Also send via existing SMS utils for consistency
        try:
            from utils.sms_utils import send_driver_ride_notification
            send_driver_ride_notification(ride.driver, ride)
        except ImportError:
            pass  # SMS utils not available


def notify_ride_accepted(ride):
    """Notify passenger when driver accepts the ride"""
    # Get driver's primary vehicle
    primary_vehicle = ride.vehicle or ride.driver.vehicles.filter(is_active=True, is_primary=True).first()
    
    vehicle_info = f"{primary_vehicle.make} {primary_vehicle.model}" if primary_vehicle else "Vehicle"
    plate_info = primary_vehicle.license_plate if primary_vehicle else "N/A"
    
    message = (
        f"Your ride has been accepted!"
        f"\nDriver: {ride.driver.user.get_full_name() or ride.driver.user.username}"
        f"\nVehicle: {vehicle_info}"
        f"\nPlate: {plate_info}"
        f"\nPhone: {ride.driver.user.phone_number or 'N/A'}"
    )
    
    # Send via notification service
    send_notification(
        user=ride.passenger,
        notification_type='ride_accepted',
        title='Ride Accepted!',
        message=message,
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride',
        data={
            'ride_id': str(ride.ride_id),
            'driver_name': ride.driver.user.get_full_name() or ride.driver.user.username,
            'driver_phone': ride.driver.user.phone_number or '',
            'vehicle': vehicle_info,
            'plate': plate_info
        }
    )

    # Also send via existing SMS utils
    try:
        from utils.sms_utils import send_passenger_driver_accepted
        send_passenger_driver_accepted(ride.passenger, ride)
    except ImportError:
        pass  # SMS utils not available


def notify_driver_arrived(ride):
    """Notify passenger when driver arrives at pickup"""
    primary_vehicle = ride.vehicle or ride.driver.vehicles.filter(is_active=True, is_primary=True).first()
    vehicle_info = f"{primary_vehicle.make} {primary_vehicle.model} ({primary_vehicle.license_plate})" if primary_vehicle else "Your driver"
    
    message = (
        f"Your driver has arrived at the pickup location!"
        f"\nVehicle: {vehicle_info}"
        f"\nDriver: {ride.driver.user.get_full_name() or ride.driver.user.username}"
        f"\nPhone: {ride.driver.user.phone_number or 'N/A'}"
    )
    
    send_notification(
        user=ride.passenger,
        notification_type='ride_arrived',
        title='Driver Arrived',
        message=message,
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride'
    )


def notify_ride_started(ride):
    """Notify passenger when ride starts"""
    message = (
        f"Your ride has started!"
        f"\nDestination: {ride.dropoff_address[:50]}..."
        f"\nEstimated fare: GHS {ride.total_fare:.2f}"
        f"\nDriver: {ride.driver.user.get_full_name() or ride.driver.user.username}"
    )
    
    send_notification(
        user=ride.passenger,
        notification_type='ride_started',
        title='Ride Started',
        message=message,
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride'
    )


def notify_ride_completed(ride):
    """Notify both passenger and driver when ride is completed"""
    # Notify passenger
    passenger_message = (
        f"Your ride has been completed!"
        f"\nTotal fare: GHS {ride.total_fare:.2f}"
        f"\nThank you for riding with Soma Ko!"
        f"\nPlease rate your experience."
    )
    
    send_notification(
        user=ride.passenger,
        notification_type='ride_completed',
        title='Ride Completed',
        message=passenger_message,
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride',
        data={'fare': str(ride.total_fare)}
    )

    # Notify driver
    driver_message = (
        f"Ride completed successfully!"
        f"\nFare collected: GHS {ride.total_fare:.2f}"
        f"\nPassenger: {ride.passenger.get_full_name() or ride.passenger.username}"
        f"\nThank you for driving with Soma Ko!"
    )
    
    send_notification(
        user=ride.driver.user,
        notification_type='ride_completed',
        title='Ride Completed',
        message=driver_message,
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride',
        data={'fare': str(ride.total_fare)}
    )

    # Also send via existing SMS utils
    try:
        from utils.sms_utils import send_passenger_ride_completed
        send_passenger_ride_completed(ride.passenger, ride)
    except ImportError:
        pass  # SMS utils not available


def notify_ride_cancelled(ride, cancelled_by):
    """Notify when ride is cancelled"""
    # Determine who to notify
    if cancelled_by == ride.passenger:
        # Notify driver
        if ride.driver:
            message = (
                f"Ride has been cancelled by passenger."
                f"\nPickup: {ride.pickup_address[:50]}..."
                f"\nRide ID: {ride.ride_id}"
                f"\nYou are now available for new rides."
            )
            send_notification(
                user=ride.driver.user,
                notification_type='ride_cancelled',
                title='Ride Cancelled',
                message=message,
                channels=['in_app', 'sms'],
                reference_id=str(ride.ride_id),
                reference_type='Ride'
            )
    elif ride.driver and cancelled_by == ride.driver.user:
        # Notify passenger
        message = (
            f"Your ride has been cancelled by the driver."
            f"\nRide ID: {ride.ride_id}"
            f"\nPlease book a new ride."
            f"\nSorry for the inconvenience."
        )
        send_notification(
            user=ride.passenger,
            notification_type='ride_cancelled',
            title='Ride Cancelled',
            message=message,
            channels=['in_app', 'sms'],
            reference_id=str(ride.ride_id),
            reference_type='Ride'
        )
