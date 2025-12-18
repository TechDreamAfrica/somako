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


def notify_ride_accepted(ride):
    """Notify rider when driver accepts the ride"""
    send_notification(
        user=ride.rider,
        notification_type='ride_accepted',
        title='Ride Accepted!',
        message=f'Your ride has been accepted by {ride.driver.user.get_full_name() or ride.driver.user.username}. Vehicle: {ride.driver.vehicle_model}. Plate: {ride.driver.vehicle_plate}',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(ride.ride_id),
        reference_type='Ride',
        data={
            'ride_id': str(ride.ride_id),
            'driver_name': ride.driver.user.get_full_name() or ride.driver.user.username,
            'driver_phone': ride.driver.user.phone_number,
            'vehicle': f"{ride.driver.vehicle_model} - {ride.driver.vehicle_plate}"
        }
    )


def notify_driver_arrived(ride):
    """Notify rider when driver arrives at pickup"""
    send_notification(
        user=ride.rider,
        notification_type='ride_arrived',
        title='Driver Arrived',
        message=f'Your driver has arrived at the pickup location. Vehicle: {ride.driver.vehicle_model} ({ride.driver.vehicle_plate})',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(ride.ride_id),
        reference_type='Ride'
    )


def notify_ride_started(ride):
    """Notify rider when ride starts"""
    send_notification(
        user=ride.rider,
        notification_type='ride_started',
        title='Ride Started',
        message=f'Your ride has started. Destination: {ride.dropoff_address}. Estimated fare: GHS {ride.total_fare}',
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride'
    )


def notify_ride_completed(ride):
    """Notify both rider and driver when ride is completed"""
    # Notify rider
    send_notification(
        user=ride.rider,
        notification_type='ride_completed',
        title='Ride Completed',
        message=f'Your ride has been completed. Total fare: GHS {ride.total_fare}. Thank you for riding with Soma Ko!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(ride.ride_id),
        reference_type='Ride',
        data={'fare': str(ride.total_fare)}
    )

    # Notify driver
    send_notification(
        user=ride.driver.user,
        notification_type='ride_completed',
        title='Ride Completed',
        message=f'Ride completed successfully. Fare earned: GHS {ride.total_fare}',
        channels=['in_app', 'sms'],
        reference_id=str(ride.ride_id),
        reference_type='Ride',
        data={'fare': str(ride.total_fare)}
    )


def notify_ride_cancelled(ride, cancelled_by):
    """Notify when ride is cancelled"""
    # Determine who to notify
    if cancelled_by == ride.rider:
        # Notify driver
        if ride.driver:
            send_notification(
                user=ride.driver.user,
                notification_type='ride_cancelled',
                title='Ride Cancelled',
                message=f'The rider has cancelled the ride from {ride.pickup_address}.',
                channels=['in_app', 'sms', 'whatsapp'],
                reference_id=str(ride.ride_id),
                reference_type='Ride'
            )
    elif ride.driver and cancelled_by == ride.driver.user:
        # Notify rider
        send_notification(
            user=ride.rider,
            notification_type='ride_cancelled',
            title='Ride Cancelled',
            message=f'Your ride has been cancelled by the driver. Please request a new ride.',
            channels=['in_app', 'sms', 'whatsapp'],
            reference_id=str(ride.ride_id),
            reference_type='Ride'
        )
